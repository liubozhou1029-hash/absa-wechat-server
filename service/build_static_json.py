"""
build_static_json.py
把新ABSA数据转换为小程序可用的JS文件
输出：
  miniapp/utils/data/phones_new.js   → 商品列表（phones页面用）
  miniapp/utils/data/details_new.js  → 商品详情（detail页面用）

运行：python build_static_json.py
"""

import sys
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# 直接硬编码路径，不依赖config
SKU_ABSA_FEATURES_FILE = BASE_DIR / "backend" / "data" / "results" / "sku_absa_features.csv"
ASPECT_FEAT_FILE       = BASE_DIR / "backend" / "data" / "results" / "sku_aspect_features.csv"
RECOMMEND_FILE         = BASE_DIR / "backend" / "data" / "results" / "sku_recommend_index_v2.csv"

MINIAPP_DATA_DIR = BASE_DIR / "miniapp" / "utils" / "data"
MINIAPP_DATA_DIR.mkdir(parents=True, exist_ok=True)

OUT_PHONES  = MINIAPP_DATA_DIR / "phones_new.js"
OUT_DETAILS = MINIAPP_DATA_DIR / "details_new.js"


def safe_float(v, digits=4, default=0.0):
    try:
        return round(float(v), digits)
    except Exception:
        return default


def safe_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def main():
    # 读取数据
    sku_feat = pd.read_csv(SKU_ABSA_FEATURES_FILE, encoding="utf-8-sig")
    aspect_feat = pd.read_csv(ASPECT_FEAT_FILE, encoding="utf-8-sig")

    # 尝试读取推荐索引（有recommend_score字段）
    try:
        rec = pd.read_csv(RECOMMEND_FILE, encoding="utf-8-sig")
        sku_feat = sku_feat.merge(
            rec[["sku_id", "recommend_score"]].drop_duplicates("sku_id"),
            on="sku_id", how="left"
        )
    except Exception:
        sku_feat["recommend_score"] = sku_feat["aspect_sentiment_mean"].apply(
            lambda x: round((safe_float(x) + 1) / 2 * 100, 2)
        )

    # 过滤评论数不足的商品
    sku_feat = sku_feat[sku_feat["absa_comment_count"] >= 3].copy()
    sku_feat = sku_feat.sort_values("recommend_score", ascending=False).reset_index(drop=True)

    print(f"总商品数：{len(sku_feat)}")
    print(f"品类分布：\n{sku_feat['cat'].value_counts().to_string()}")

    # ── 构建 phones_new.js（列表页数据）──────────────────────────────
    phones_list = []
    for idx, row in sku_feat.iterrows():
        sku_id = str(row["sku_id"])
        cat    = str(row["cat"])
        n      = safe_int(row["absa_comment_count"])
        pos_r  = safe_float(row.get("aspect_positive_ratio", 0))
        neg_r  = safe_float(row.get("aspect_negative_ratio", 0))
        sent   = safe_float(row.get("aspect_sentiment_mean", 0))
        conf   = safe_float(row.get("absa_confidence_mean", 0.5))
        score  = safe_float(row.get("recommend_score", 0), 2)

        phones_list.append({
            "sku_id":                  sku_id,
            "display_id":              str(idx + 1).zfill(3),
            "cat":                     cat,
            "recommend_score":         score,
            "absa_comment_count":      n,
            "aspect_sentiment_mean":   sent,
            "aspect_positive_ratio":   pos_r,
            "aspect_negative_ratio":   neg_r,
            "aspect_neutral_ratio":    safe_float(row.get("aspect_neutral_ratio", 0)),
            "absa_confidence_mean":    conf,
            "aspect_known_ratio":      safe_float(row.get("aspect_known_ratio", 1)),
        })

    phones_js = "module.exports = " + json.dumps(phones_list, ensure_ascii=False, indent=2)
    OUT_PHONES.write_text(phones_js, encoding="utf-8")
    print(f"\n✅ phones_new.js 已生成：{OUT_PHONES}（{len(phones_list)} 条）")

    # ── 构建 details_new.js（详情页数据）─────────────────────────────
    details_dict = {}
    for idx, row in sku_feat.iterrows():
        sku_id = str(row["sku_id"])
        cat    = str(row["cat"])
        n      = safe_int(row["absa_comment_count"])
        pos_r  = safe_float(row.get("aspect_positive_ratio", 0))
        neg_r  = safe_float(row.get("aspect_negative_ratio", 0))
        neu_r  = safe_float(row.get("aspect_neutral_ratio", 0))
        sent   = safe_float(row.get("aspect_sentiment_mean", 0))
        conf   = safe_float(row.get("absa_confidence_mean", 0.5))
        score  = safe_float(row.get("recommend_score", 0), 2)
        abs_m  = safe_float(row.get("aspect_sentiment_abs_mean", 0))
        known  = safe_float(row.get("aspect_known_ratio", 1))

        # 该商品的各方面情感数据
        item_aspects = aspect_feat[aspect_feat["sku_id"] == sku_id]
        aspects_list = []
        for _, ar in item_aspects.sort_values("aspect_sentiment_mean", ascending=False).iterrows():
            aspects_list.append({
                "aspect":                ar["aspect"],
                "aspect_count":          safe_int(ar.get("aspect_count", 0)),
                "aspect_sentiment_mean": safe_float(ar.get("aspect_sentiment_mean", 0)),
                "aspect_positive_ratio": safe_float(ar.get("aspect_positive_ratio", 0)),
                "aspect_negative_ratio": safe_float(ar.get("aspect_negative_ratio", 0)),
                "aspect_confidence_mean": safe_float(ar.get("aspect_confidence_mean", 0.5)),
            })

        details_dict[sku_id] = {
            "detail": {
                "sku_id":                         sku_id,
                "cat":                            cat,
                "recommend_score":                score,
                "absa_comment_count":             n,
                "aspect_sentiment_mean":          sent,
                "aspect_sentiment_abs_mean":      abs_m,
                "aspect_positive_ratio":          pos_r,
                "aspect_negative_ratio":          neg_r,
                "aspect_neutral_ratio":           neu_r,
                "aspect_known_ratio":             known,
                "absa_confidence_mean":           conf,
            },
            "aspects": aspects_list
        }

    details_js = "module.exports = " + json.dumps(details_dict, ensure_ascii=False, indent=2)
    OUT_DETAILS.write_text(details_js, encoding="utf-8")
    print(f"✅ details_new.js 已生成：{OUT_DETAILS}（{len(details_dict)} 个商品）")


if __name__ == "__main__":
    main()
