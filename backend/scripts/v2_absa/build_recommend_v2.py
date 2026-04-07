import sys
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import (
    SKU_RECOMMEND_INDEX_FILE,
    SKU_ABSA_FEATURES_FILE,
    SKU_RECOMMEND_INDEX_V2_FILE,
    ensure_dirs,
)


def main():
    ensure_dirs()

    print(f"1) 读取原推荐结果: {SKU_RECOMMEND_INDEX_FILE} ...")
    rec = pd.read_csv(SKU_RECOMMEND_INDEX_FILE)

    print(f"2) 读取 ABSA 聚合特征: {SKU_ABSA_FEATURES_FILE} ...")
    absa = pd.read_csv(SKU_ABSA_FEATURES_FILE)

    print("3) 合并推荐结果与 ABSA 特征 ...")
    df = rec.merge(absa, on="sku_id", how="left")

    # 缺失值兜底
    fill_values = {
        "absa_comment_count": 0,
        "aspect_sentiment_mean": 0.0,
        "aspect_sentiment_abs_mean": 0.0 if "aspect_sentiment_abs_mean" in df.columns else None,
        "aspect_positive_ratio": 0.0,
        "aspect_negative_ratio": 0.0,
        "aspect_neutral_ratio": 0.0,
        "aspect_known_ratio": 0.0 if "aspect_known_ratio" in df.columns else None,
        "absa_confidence_mean": 0.0,
    }
    for col, val in fill_values.items():
        if col in df.columns and val is not None:
            df[col] = df[col].fillna(val)

    if "recommend_index" not in df.columns:
        raise ValueError("原推荐结果中缺少 recommend_index 列")

    print("4) 构建 recommend_index_v2 ...")

    # 缺失值兜底
    fill_values = {
        "absa_comment_count": 0,
        "aspect_sentiment_mean": 0.0,
        "aspect_positive_ratio": 0.0,
        "aspect_negative_ratio": 0.0,
        "aspect_neutral_ratio": 0.0,
        "absa_confidence_mean": 0.0,
    }
    for col, val in fill_values.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    # 基于排序分融合，而不是直接线性加法
    df["rank_base"] = df["recommend_index"].rank(ascending=False, method="min")
    df["rank_sent"] = df["aspect_sentiment_mean"].rank(ascending=False, method="min")
    df["rank_neg"] = df["aspect_negative_ratio"].rank(ascending=True, method="min")
    df["rank_conf"] = df["absa_confidence_mean"].rank(ascending=False, method="min")

    df["rank_score_v2"] = (
            0.55 * df["rank_base"]
            + 0.20 * df["rank_sent"]
            + 0.20 * df["rank_neg"]
            + 0.05 * df["rank_conf"]
    )

    df = df.sort_values("rank_score_v2", ascending=True).reset_index(drop=True)

    # 为了兼容 compare_v1_v2.py，保留 recommend_index_v2 字段
    df["recommend_index_v2"] = -df["rank_score_v2"]

    print("5) 排序并导出新版推荐结果 ...")
    df = df.sort_values("recommend_index_v2", ascending=False).reset_index(drop=True)
    df.to_csv(SKU_RECOMMEND_INDEX_V2_FILE, index=False, encoding="utf-8-sig")

    print(f"6) 已导出 {SKU_RECOMMEND_INDEX_V2_FILE}")
    print("\n前10行预览：")
    preview_cols = [
        "sku_id",
        "generated_name" if "generated_name" in df.columns else None,
        "recommend_index",
        "recommend_index_v2",
        "aspect_sentiment_mean",
        "aspect_positive_ratio",
        "aspect_negative_ratio",
        "absa_confidence_mean",
    ]
    preview_cols = [c for c in preview_cols if c is not None and c in df.columns]
    print(df[preview_cols].head(10))


if __name__ == "__main__":
    main()