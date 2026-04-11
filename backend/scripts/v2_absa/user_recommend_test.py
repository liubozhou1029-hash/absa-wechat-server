"""
user_recommend_test.py - 本地测试：用户输入评论 → ABSA分析 → 跨品类推荐
运行方式：python user_recommend_test.py
依赖：pyabsa, pandas（已安装）
"""

import os
import sys
import re
import html
import math
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# ─── 路径配置 ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from config import (
    SKU_ABSA_FEATURES_FILE,
    HF_CACHE_DIR,
)
ASPECT_FEAT_FILE = SKU_ABSA_FEATURES_FILE.parent / "sku_aspect_features.csv"

os.environ["HF_HOME"]               = str(HF_CACHE_DIR)
os.environ["HF_HUB_CACHE"]          = str(HF_CACHE_DIR / "hub")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

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

MIN_COMMENTS = 3  # 商品最少评论数阈值


# ─── 工具函数 ────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def volume_factor(n: int, max_n: int) -> float:
    if max_n <= 0:
        return 0.0
    return math.log1p(n) / math.log1p(max_n)


def extract_user_preference(classifier, reviews: list[str]) -> dict:
    """
    对用户输入的评论做ABSA，提取方面偏好向量
    返回：{aspect: avg_sentiment_score}
    """
    aspect_scores = {}
    aspect_counts = {}

    for review in reviews:
        review = clean_text(review)
        if len(review) < 5:
            continue

        # 对所有方面词中出现在评论里的进行预测
        matched = [a for a in ALL_ASPECTS if a in review]
        if not matched:
            matched = ["整体"]

        batch = [f"[B-ASP]{a}[E-ASP] {review}" for a in matched]

        try:
            results = classifier.predict(
                batch,
                print_result=False,
                save_result=False,
                ignore_error=True,
            )
            if results and len(results) == len(matched):
                for aspect, r in zip(matched, results):
                    label = str(r.get("sentiment", "")).lower()
                    conf_raw = r.get("confidence", 0)
                    try:
                        conf = float(str(conf_raw).strip("[]").split(",")[0])
                    except Exception:
                        conf = 0.5

                    if "positive" in label:
                        score = conf
                    elif "negative" in label:
                        score = -conf
                    else:
                        score = 0.0

                    aspect_scores[aspect] = aspect_scores.get(aspect, 0.0) + score
                    aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1
        except Exception:
            pass

    # 取均值
    user_pref = {}
    for aspect in aspect_scores:
        user_pref[aspect] = aspect_scores[aspect] / aspect_counts[aspect]

    return user_pref


def compute_aspect_match(user_pref: dict, item_aspects: pd.DataFrame, item_cat: str) -> float:
    if not user_pref or item_aspects.empty:
        return 0.5

    item_dict = dict(zip(item_aspects["aspect"], item_aspects["aspect_sentiment_mean"]))
    cat_aspects = CATEGORY_ASPECTS.get(item_cat, set())

    scores, w_sum = [], 0.0
    for aspect, u_score in user_pref.items():
        is_common   = aspect in COMMON_ASPECTS
        is_cat_match = aspect in cat_aspects
        if not is_common and not is_cat_match:
            continue
        if aspect in item_dict:
            match = 1.0 - abs(u_score - item_dict[aspect]) / 2.0
            w = 2.0 if is_common else 1.0
            scores.append(match * w)
            w_sum += w

    return sum(scores) / w_sum if (scores and w_sum > 0) else 0.5


def detect_user_category(reviews: list[str]) -> str:
    """
    根据用户评论中出现的专属方面词，推断用户最可能评论的品类
    返回品类名，若无法判断返回None
    """
    cat_hits = {}
    for cat, aspects in CATEGORY_ASPECTS.items():
        count = 0
        for review in reviews:
            for asp in aspects:
                if asp in review:
                    count += 1
        if count > 0:
            cat_hits[cat] = count

    if not cat_hits:
        return None
    return max(cat_hits, key=cat_hits.get)


def generate_block_reason(user_pref: dict, rec_df: pd.DataFrame,
                           cat: str, is_same_cat: bool) -> str:
    """
    为整个推荐区块生成一段整体推荐理由
    格式：判断出您对XX更重视，倾向于YY，因此推荐的商品在ZZ方面表现突出
    """
    if rec_df.empty:
        return ""

    # ① 找出用户最重视的方面（取绝对值最大的前2个）
    if user_pref:
        sorted_pref = sorted(user_pref.items(), key=lambda x: abs(x[1]), reverse=True)
        top_aspects = [(a, s) for a, s in sorted_pref[:3] if abs(s) > 0.3]
    else:
        top_aspects = []

    # ② 分析用户倾向
    if top_aspects:
        pos_aspects = [a for a, s in top_aspects if s > 0]
        neg_aspects = [a for a, s in top_aspects if s < 0]
        focus_str = "、".join(pos_aspects[:2]) if pos_aspects else ""
        avoid_str = "、".join(neg_aspects[:2]) if neg_aspects else ""
    else:
        focus_str = ""
        avoid_str = ""

    # ③ 统计推荐商品的整体质量数据
    avg_score    = rec_df["推荐分"].mean()
    avg_pos_rate = rec_df["正向率"].str.rstrip("%").astype(float).mean()
    total_comments = rec_df["评论数"].sum()
    top_item     = rec_df.iloc[0]["商品名称"]

    # ④ 组装理由
    parts = []

    # 用户偏好描述
    if focus_str and avoid_str:
        parts.append(
            f"根据您的评论，判断出您对【{focus_str}】较为重视，"
            f"同时对【{avoid_str}】有一定负面感受"
        )
    elif focus_str:
        parts.append(
            f"根据您的评论，判断出您对【{focus_str}】更为重视，"
            f"整体倾向于正向体验"
        )
    else:
        parts.append("根据您的评论整体情感分析")

    # 推荐依据
    if is_same_cat:
        parts.append(
            f"为您筛选出同品类【{cat}】中综合评分最优的商品，"
            f"推荐列表平均好评率达 {avg_pos_rate:.0f}%，"
            f"基于共 {total_comments} 条真实用户评论。"
            f"其中「{top_item}」综合推荐分最高（{rec_df.iloc[0]['推荐分']}分），"
            f"在您关注的方面上用户反馈最为积极"
        )
    else:
        # 统计推荐商品涵盖的品类
        cats = rec_df["品类"].unique().tolist()
        cat_str = "、".join(cats[:4])
        parts.append(
            f"通过方面情感迁移，在全品类中为您匹配最符合您偏好的商品，"
            f"推荐结果涵盖【{cat_str}】等品类，"
            f"平均好评率 {avg_pos_rate:.0f}%，"
            f"基于共 {total_comments} 条评论综合评估。"
            f"推荐榜首「{top_item}」在您关注的通用方面（如价格、服务等）表现尤为突出"
        )

    return "，".join(parts) + "。"


def build_recommendation(user_pref: dict, top_k: int = 10) -> tuple:
    """
    根据用户偏好生成推荐列表
    返回：(跨品类推荐df, 全量df)
    """
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
            "商品名称": sku_id,
            "品类":     cat,
            "推荐分":   round(score * 100, 1),
            "正向率":   f"{comp_overall*100:.0f}%",
            "方面匹配": f"{comp_aspect:.3f}",
            "评论数":   n,
        })

    df = pd.DataFrame(results).sort_values("推荐分", ascending=False).reset_index(drop=True)
    return df.head(top_k), df


# ─── GUI 界面 ────────────────────────────────────────────────────────
class RecommendApp:
    def __init__(self, root):
        self.root = root
        self.root.title("商品推荐测试工具")
        self.root.geometry("700x650")
        self.root.resizable(True, True)
        self.classifier = None
        self._build_ui()

    def _build_ui(self):
        # 标题
        tk.Label(self.root, text="基于评论的跨品类商品推荐",
                 font=("SimHei", 14, "bold")).pack(pady=10)

        # 说明
        tk.Label(self.root,
                 text="请在下方输入您的评论（每行一条，建议3~10条，可以是任何商品的评论）",
                 font=("SimSun", 10), fg="gray").pack()

        # 评论输入框
        self.text_input = scrolledtext.ScrolledText(
            self.root, height=12, font=("SimSun", 11), wrap=tk.WORD
        )
        self.text_input.pack(fill=tk.BOTH, expand=False, padx=20, pady=8)

        # 示例按钮
        tk.Button(self.root, text="填入示例评论", command=self._fill_example,
                  bg="#e8e8e8").pack(pady=2)

        # 推荐数量
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Label(frame, text="推荐数量 Top-K：").pack(side=tk.LEFT)
        self.topk_var = tk.IntVar(value=10)
        tk.Spinbox(frame, from_=5, to=30, textvariable=self.topk_var, width=5).pack(side=tk.LEFT)

        # 分析按钮
        self.btn = tk.Button(self.root, text="▶  开始分析并推荐",
                             command=self._run, font=("SimHei", 11, "bold"),
                             bg="#4a9eff", fg="white", pady=6)
        self.btn.pack(pady=8, ipadx=20)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(self.root, textvariable=self.status_var,
                 fg="blue", font=("SimSun", 10)).pack()

        # 结果展示
        tk.Label(self.root, text="推荐结果：",
                 font=("SimHei", 11, "bold")).pack(anchor="w", padx=20)
        self.result_box = scrolledtext.ScrolledText(
            self.root, height=12, font=("Courier New", 10),
            state=tk.DISABLED, bg="#f8f8f8"
        )
        self.result_box.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

    def _fill_example(self):
        example = (
            "这本书内容非常充实，作者文笔流畅，读完收获很多，价格也很实惠\n"
            "物流很快，包装完好，客服态度很好，总体满意\n"
            "书的印刷质量不错，内容深入浅出，适合入门，性价比很高\n"
            "快递速度一般，但商品本身质量没问题，服务态度还可以\n"
            "内容有点干涩，读起来费劲，不太适合普通读者，价格偏贵\n"
        )
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", example)

    def _run(self):
        raw = self.text_input.get("1.0", tk.END).strip()
        reviews = [r.strip() for r in raw.split("\n") if r.strip()]

        if len(reviews) < 1:
            messagebox.showwarning("提示", "请至少输入1条评论！")
            return

        self.btn.config(state=tk.DISABLED)
        self.status_var.set("正在加载ABSA模型（首次约30秒）...")
        self.root.update()

        try:
            if self.classifier is None:
                from pyabsa import AspectPolarityClassification as APC
                self.classifier = APC.SentimentClassifier(
                    "multilingual", cal_perplexity=False
                )

            self.status_var.set(f"正在分析 {len(reviews)} 条评论...")
            self.root.update()

            user_pref = extract_user_preference(self.classifier, reviews)

            # 推断用户品类
            user_cat = detect_user_category(reviews)

            if not user_pref:
                self.status_var.set("未能识别有效方面偏好，使用整体质量排序")
                user_pref = {}
            else:
                cat_hint = f"，推断品类：{user_cat}" if user_cat else ""
                self.status_var.set(
                    f"识别到 {len(user_pref)} 个方面偏好{cat_hint}，正在匹配商品..."
                )
                self.root.update()

            top_k = self.topk_var.get()
            cross_rec, all_rec = build_recommendation(user_pref, top_k=top_k)

            # 同品类推荐
            if user_cat:
                same_cat_rec = all_rec[all_rec["品类"] == user_cat].head(top_k)
            else:
                same_cat_rec = pd.DataFrame()

            self._show_result(user_pref, cross_rec, same_cat_rec, user_cat)
            self.status_var.set("✅ 分析完成！")

        except Exception as e:
            messagebox.showerror("错误", f"运行出错：{e}")
            self.status_var.set("❌ 出现错误")
        finally:
            self.btn.config(state=tk.NORMAL)

    def _show_result(self, user_pref: dict, cross_rec: pd.DataFrame,
                     same_cat_rec: pd.DataFrame, user_cat: str):
        self.result_box.config(state=tk.NORMAL)
        self.result_box.delete("1.0", tk.END)

        # 用户偏好向量
        self.result_box.insert(tk.END, "【识别到的用户方面偏好】\n")
        if user_pref:
            sorted_pref = sorted(user_pref.items(), key=lambda x: abs(x[1]), reverse=True)
            for asp, score in sorted_pref[:8]:
                bar = "█" * int(abs(score) * 10)
                direction = "正向" if score > 0 else "负向"
                self.result_box.insert(
                    tk.END, f"  {asp:6s}  {direction}  {bar}  ({score:+.3f})\n"
                )
        else:
            self.result_box.insert(tk.END, "  （未识别到具体方面，使用商品整体质量排序）\n")

        if user_cat:
            self.result_box.insert(tk.END, f"\n  推断您评论的品类：【{user_cat}】\n")

        # ── 同品类推荐（先展示）──────────────────────────────────────
        self.result_box.insert(tk.END, f"\n{'═'*62}\n")
        if not same_cat_rec.empty and user_cat:
            reason = generate_block_reason(user_pref, same_cat_rec, user_cat, is_same_cat=True)
            self.result_box.insert(
                tk.END, f"【同品类推荐（{user_cat}）】\n{'─'*62}\n"
            )
            # 整体推荐理由
            self.result_box.insert(tk.END, f"📋 推荐说明：\n")
            # 自动换行展示（每60字换行）
            for i in range(0, len(reason), 55):
                self.result_box.insert(tk.END, f"   {reason[i:i+55]}\n")
            self.result_box.insert(tk.END, f"{'─'*62}\n")

            for rank, (_, row) in enumerate(same_cat_rec.iterrows(), 1):
                self.result_box.insert(
                    tk.END,
                    f"  No.{rank}  {str(row['商品名称'])}\n"
                    f"       推荐分 {row['推荐分']}  |  好评率 {row['正向率']}"
                    f"  |  {row['评论数']} 条评论\n\n"
                )
        elif user_cat:
            self.result_box.insert(
                tk.END,
                f"【同品类推荐（{user_cat}）】\n"
                f"  暂无足够数据的{user_cat}类商品\n"
            )

        # ── 跨品类推荐（后展示）──────────────────────────────────────
        self.result_box.insert(tk.END, f"\n{'═'*62}\n")
        cross_reason = generate_block_reason(user_pref, cross_rec, user_cat or "", is_same_cat=False)
        self.result_box.insert(tk.END, f"【跨品类推荐】\n{'─'*62}\n")
        self.result_box.insert(tk.END, f"📋 推荐说明：\n")
        for i in range(0, len(cross_reason), 55):
            self.result_box.insert(tk.END, f"   {cross_reason[i:i+55]}\n")
        self.result_box.insert(tk.END, f"{'─'*62}\n")

        for rank, (_, row) in enumerate(cross_rec.iterrows(), 1):
            self.result_box.insert(
                tk.END,
                f"  No.{rank}  {str(row['商品名称'])}（{row['品类']}）\n"
                f"       推荐分 {row['推荐分']}  |  好评率 {row['正向率']}"
                f"  |  {row['评论数']} 条评论\n\n"
            )

        self.result_box.config(state=tk.DISABLED)


# ─── 入口 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = RecommendApp(root)
    root.mainloop()
