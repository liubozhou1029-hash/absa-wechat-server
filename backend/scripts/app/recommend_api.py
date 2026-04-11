"""
recommend_api.py - Flask本地后端
接收小程序传来的评论文本，调用ABSA推理，返回推荐结果
运行：python recommend_api.py
访问：http://localhost:5000
"""

import os
import sys
import json
import math
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# ─── 路径配置 ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from config import SKU_ABSA_FEATURES_FILE, HF_CACHE_DIR

os.environ["HF_HOME"]      = str(HF_CACHE_DIR)
os.environ["HF_HUB_CACHE"] = str(HF_CACHE_DIR / "hub")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

ASPECT_FEAT_FILE = SKU_ABSA_FEATURES_FILE.parent / "sku_aspect_features.csv"

import pandas as pd

app = Flask(__name__)
CORS(app)  # 允许小程序跨域

# ─── 全局变量（模型只加载一次）──────────────────────────────────────
classifier = None

def get_classifier():
    global classifier
    if classifier is None:
        print("正在加载ABSA模型...")
        from pyabsa import AspectPolarityClassification as APC
        classifier = APC.SentimentClassifier("multilingual", cal_perplexity=False)
        print("模型加载完成")
    return classifier

# ─── 方面词表 ────────────────────────────────────────────────────────
COMMON_ASPECTS = {"价格", "性价比", "物流", "快递", "包装", "客服", "服务", "质量"}

CATEGORY_ASPECTS = {
    "书籍":  {"内容", "文笔", "作者", "装帧", "印刷", "排版", "翻译", "故事"},
    "平板":  {"性能", "续航", "屏幕", "做工", "系统", "拍照", "充电", "发热"},
    "手机":  {"性能", "续航", "屏幕", "拍照", "信号", "系统", "做工", "充电", "发热"},
    "水果":  {"新鲜", "口感", "甜度", "大小", "外观", "产地", "重量"},
    "洗发水": {"效果", "气味", "成分", "泡沫", "滋润", "去屑", "香味"},
    "热水器": {"加热", "保温", "安装", "噪音", "安全", "容量", "外观"},
    "蒙牛":  {"口感", "新鲜", "营养", "甜度", "浓度", "气味"},
    "衣服":  {"版型", "面料", "尺码", "颜色", "做工", "舒适", "洗涤"},
    "计算机": {"性能", "续航", "屏幕", "散热", "键盘", "做工", "系统", "运行"},
    "酒店":  {"位置", "房间", "卫生", "早餐", "服务", "环境", "设施", "噪音"},
}

ALL_ASPECTS = COMMON_ASPECTS.copy()
for aspects in CATEGORY_ASPECTS.values():
    ALL_ASPECTS |= aspects

WEIGHTS = {
    "overall_sentiment": 0.40,
    "aspect_match":      0.35,
    "confidence":        0.10,
    "volume":            0.15,
}

MIN_COMMENTS = 3


def volume_factor(n, max_n):
    if max_n <= 0:
        return 0.0
    return math.log1p(n) / math.log1p(max_n)


def extract_user_preference(reviews):
    clf = get_classifier()
    aspect_scores = {}
    aspect_counts = {}

    for review in reviews:
        if len(review.strip()) < 5:
            continue
        matched = [a for a in ALL_ASPECTS if a in review]
        if not matched:
            matched = ["整体"]

        batch = [f"[B-ASP]{a}[E-ASP] {review}" for a in matched]
        try:
            results = clf.predict(batch, print_result=False,
                                  save_result=False, ignore_error=True)
            if results and len(results) == len(matched):
                for aspect, r in zip(matched, results):
                    label = str(r.get("sentiment", "")).lower()
                    conf_raw = r.get("confidence", 0)
                    try:
                        conf = float(str(conf_raw).strip("[]").split(",")[0])
                    except Exception:
                        conf = 0.5
                    score = conf if "positive" in label else (-conf if "negative" in label else 0.0)
                    aspect_scores[aspect] = aspect_scores.get(aspect, 0.0) + score
                    aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1
        except Exception:
            pass

    return {a: aspect_scores[a] / aspect_counts[a] for a in aspect_scores}


def detect_user_category(reviews):
    cat_hits = {}
    for cat, aspects in CATEGORY_ASPECTS.items():
        count = sum(1 for r in reviews for a in aspects if a in r)
        if count > 0:
            cat_hits[cat] = count
    return max(cat_hits, key=cat_hits.get) if cat_hits else None


def compute_aspect_match(user_pref, item_aspects_df, item_cat):
    if not user_pref or item_aspects_df.empty:
        return 0.5
    item_dict = dict(zip(item_aspects_df["aspect"], item_aspects_df["aspect_sentiment_mean"]))
    cat_aspects = CATEGORY_ASPECTS.get(item_cat, set())
    scores, w_sum = [], 0.0
    for aspect, u_score in user_pref.items():
        is_common    = aspect in COMMON_ASPECTS
        is_cat_match = aspect in cat_aspects
        if not is_common and not is_cat_match:
            continue
        if aspect in item_dict:
            match = 1.0 - abs(u_score - item_dict[aspect]) / 2.0
            w = 2.0 if is_common else 1.0
            scores.append(match * w)
            w_sum += w
    return sum(scores) / w_sum if (scores and w_sum > 0) else 0.5


def generate_block_reason(user_pref, rec_list, cat, is_same_cat):
    if not rec_list:
        return ""
    sorted_pref = sorted(user_pref.items(), key=lambda x: abs(x[1]), reverse=True) if user_pref else []
    top_aspects = [(a, s) for a, s in sorted_pref[:3] if abs(s) > 0.3]
    pos_aspects = [a for a, s in top_aspects if s > 0]
    neg_aspects = [a for a, s in top_aspects if s < 0]
    focus_str = "、".join(pos_aspects[:2])
    avoid_str = "、".join(neg_aspects[:2])

    avg_pos_rate = sum(r["positive_ratio"] for r in rec_list) / len(rec_list) * 100
    total_comments = sum(r["comment_count"] for r in rec_list)
    top_item = rec_list[0]["name"]

    if focus_str and avoid_str:
        pref_str = f"根据您的评论，判断出您对【{focus_str}】较为重视，同时对【{avoid_str}】有一定负面感受"
    elif focus_str:
        pref_str = f"根据您的评论，判断出您对【{focus_str}】更为重视，整体倾向于正向体验"
    else:
        pref_str = "根据您的评论整体情感分析"

    if is_same_cat:
        detail = (f"为您筛选出同品类【{cat}】中综合评分最优的商品，"
                  f"推荐列表平均好评率达{avg_pos_rate:.0f}%，"
                  f"基于共{total_comments}条真实用户评论。"
                  f"其中「{top_item}」综合推荐分最高，在您关注的方面上用户反馈最为积极")
    else:
        cats = list(set(r["cat"] for r in rec_list))[:4]
        cat_str = "、".join(cats)
        detail = (f"通过方面情感迁移，在全品类中为您匹配最符合偏好的商品，"
                  f"推荐结果涵盖【{cat_str}】等品类，"
                  f"平均好评率{avg_pos_rate:.0f}%，"
                  f"基于共{total_comments}条评论综合评估。"
                  f"推荐榜首「{top_item}」在您关注的通用方面表现尤为突出")

    return f"{pref_str}，{detail}。"


def build_recommendation(user_pref, top_k=10):
    sku_feat    = pd.read_csv(SKU_ABSA_FEATURES_FILE, encoding="utf-8-sig")
    aspect_feat = pd.read_csv(ASPECT_FEAT_FILE, encoding="utf-8-sig")

    sku_feat = sku_feat[sku_feat["absa_comment_count"] >= MIN_COMMENTS].copy()
    max_n = int(sku_feat["absa_comment_count"].max())

    results = []
    for _, row in sku_feat.iterrows():
        sku_id = row["sku_id"]
        cat    = row["cat"]
        n      = int(row["absa_comment_count"])

        comp_overall    = float(row.get("aspect_positive_ratio", 0.5))
        item_asp        = aspect_feat[aspect_feat["sku_id"] == sku_id]
        comp_aspect     = compute_aspect_match(user_pref, item_asp, cat)
        comp_confidence = float(row.get("absa_confidence_mean", 0.5))
        comp_volume     = volume_factor(n, max_n)

        score = (
            WEIGHTS["overall_sentiment"] * comp_overall
            + WEIGHTS["aspect_match"]    * comp_aspect
            + WEIGHTS["confidence"]      * comp_confidence
            + WEIGHTS["volume"]          * comp_volume
        )

        results.append({
            "name":           str(sku_id),
            "cat":            str(cat),
            "score":          round(score * 100, 1),
            "positive_ratio": round(comp_overall, 4),
            "aspect_match":   round(comp_aspect, 4),
            "comment_count":  n,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k], results


# ─── API路由 ─────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "推荐服务运行中"})


@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        data    = request.get_json()
        reviews = data.get("reviews", [])
        top_k   = int(data.get("top_k", 10))

        if not reviews or len(reviews) == 0:
            return jsonify({"code": 400, "message": "请至少输入一条评论"}), 400

        # 提取用户偏好
        user_pref = extract_user_preference(reviews)
        user_cat  = detect_user_category(reviews)

        # 生成推荐
        cross_rec, all_rec = build_recommendation(user_pref, top_k=top_k)

        # 同品类推荐
        same_cat_rec = [r for r in all_rec if r["cat"] == user_cat][:top_k] if user_cat else []

        # 生成推荐理由
        cross_reason    = generate_block_reason(user_pref, cross_rec, user_cat or "", is_same_cat=False)
        same_cat_reason = generate_block_reason(user_pref, same_cat_rec, user_cat or "", is_same_cat=True) if same_cat_rec else ""

        # 整理用户偏好展示数据
        pref_display = [
            {"aspect": a, "score": round(s, 3), "positive": s > 0}
            for a, s in sorted(user_pref.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
        ]

        return jsonify({
            "code": 200,
            "user_category": user_cat or "",
            "preferences":   pref_display,
            "same_category": {
                "cat":    user_cat or "",
                "reason": same_cat_reason,
                "list":   same_cat_rec,
            },
            "cross_category": {
                "reason": cross_reason,
                "list":   cross_rec,
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"code": 500, "message": str(e)}), 500


if __name__ == "__main__":
    print("启动推荐API服务...")
    print("地址：http://localhost:5000")
    print("健康检查：http://localhost:5000/health")
    # 预加载模型
    get_classifier()
    app.run(host="0.0.0.0", port=5000, debug=False)
