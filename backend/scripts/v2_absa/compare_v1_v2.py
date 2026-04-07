import sys
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import (
    SKU_RECOMMEND_INDEX_FILE,
    SKU_RECOMMEND_INDEX_V2_FILE,
    COMPARE_V1_V2_FULL_FILE,
    COMPARE_V1_V2_TOP_RISE_FILE,
    COMPARE_V1_V2_TOP_DROP_FILE,
    ensure_dirs,
)


def main():
    ensure_dirs()

    print("1) 读取旧版和新版推荐结果...")
    v1 = pd.read_csv(SKU_RECOMMEND_INDEX_FILE)
    v2 = pd.read_csv(SKU_RECOMMEND_INDEX_V2_FILE)

    v1 = v1.copy().reset_index(drop=True)
    v2 = v2.copy().reset_index(drop=True)

    v1["rank_v1"] = v1.index + 1
    v2["rank_v2"] = v2.index + 1

    if "recommend_index" not in v1.columns:
        raise ValueError("旧版文件中未找到 recommend_index 列")
    if "recommend_index_v2" not in v2.columns:
        raise ValueError("新版文件中未找到 recommend_index_v2 列")

    print("2) 合并排名与分数...")
    cols_v1 = ["sku_id", "generated_name", "recommend_index", "rank_v1"]
    cols_v2 = [
        "sku_id", "recommend_index_v2", "rank_v2",
        "aspect_sentiment_mean", "aspect_positive_ratio",
        "aspect_negative_ratio", "absa_confidence_mean"
    ]
    cols_v2 = [c for c in cols_v2 if c in v2.columns]

    df = v1[cols_v1].merge(v2[cols_v2], on="sku_id", how="outer")
    df["generated_name"] = df["generated_name"].fillna("")

    for col in ["rank_v1", "rank_v2", "recommend_index", "recommend_index_v2"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["rank_change"] = df["rank_v1"] - df["rank_v2"]
    # 对于排序融合，v1/v2分数尺度不同，score_change不再直接可比
    df["score_change"] = pd.NA

    # 更适合展示的指标：排名变化方向
    df["rank_change"] = df["rank_v1"] - df["rank_v2"]

    print("3) 导出完整对比表...")
    df.to_csv(COMPARE_V1_V2_FULL_FILE, index=False, encoding="utf-8-sig")

    print("4) 导出上升最多和下降最多样本...")
    up = df[df["rank_change"] > 0].sort_values(
        ["rank_change", "score_change"],
        ascending=[False, False]
    )

    # 这里强制要求分数也下降，避免出现“名次降了但分数涨了”的样本
    down = df[df["rank_change"] < 0].sort_values(
        ["rank_change"],
        ascending=[True]
    )

    up.head(20).to_csv(COMPARE_V1_V2_TOP_RISE_FILE, index=False, encoding="utf-8-sig")
    down.head(20).to_csv(COMPARE_V1_V2_TOP_DROP_FILE, index=False, encoding="utf-8-sig")

    print("\n=== 排名上升最多 Top10 ===")
    print(up[[
        "sku_id", "generated_name",
        "rank_v1", "rank_v2", "rank_change",
        "aspect_sentiment_mean", "aspect_positive_ratio",
        "aspect_negative_ratio"
    ]].head(10))

    print("\n=== 排名下降最多 Top10 ===")
    print(down[[
        "sku_id", "generated_name",
        "rank_v1", "rank_v2", "rank_change",
        "aspect_sentiment_mean", "aspect_positive_ratio",
        "aspect_negative_ratio"
    ]].head(10))

    print("\n=== 新版 Top10 ===")
    preview_cols = [
        "sku_id", "generated_name", "recommend_index_v2",
        "aspect_sentiment_mean", "aspect_positive_ratio",
        "aspect_negative_ratio"
    ]
    preview_cols = [c for c in preview_cols if c in v2.columns]
    print(v2[preview_cols].head(10))

    print("\n5) 已导出：")
    print(f"   {COMPARE_V1_V2_FULL_FILE}")
    print(f"   {COMPARE_V1_V2_TOP_RISE_FILE}")
    print(f"   {COMPARE_V1_V2_TOP_DROP_FILE}")


if __name__ == "__main__":
    main()