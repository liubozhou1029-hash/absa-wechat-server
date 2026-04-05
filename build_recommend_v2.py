import pandas as pd

def main():
    print("1) 读取旧版 sku_metrics.csv ...")
    old_df = pd.read_csv("sku_metrics.csv")

    print("2) 读取 ABSA 特征 sku_absa_features.csv ...")
    absa_df = pd.read_csv("sku_absa_features.csv")

    print("3) 按 sku_id 合并 ...")
    df = old_df.merge(absa_df, on="sku_id", how="left")

    # 缺失值兜底
    df["aspect_sentiment_mean"] = df["aspect_sentiment_mean"].fillna(0.5)
    df["aspect_positive_ratio"] = df["aspect_positive_ratio"].fillna(0.5)
    df["aspect_negative_ratio"] = df["aspect_negative_ratio"].fillna(0.0)
    df["aspect_neutral_ratio"] = df["aspect_neutral_ratio"].fillna(0.0)
    df["absa_confidence_mean"] = df["absa_confidence_mean"].fillna(0.5)
    df["absa_comment_count"] = df["absa_comment_count"].fillna(0)

    print("4) 计算 recommend_index_v2 ...")
    df["recommend_index_v2"] = (
        0.20 * df["avg_sentiment"].clip(0, 1)
        + 0.15 * df["avg_rating_norm"].clip(0, 1)
        + 0.20 * df["effective_ratio"].clip(0, 1)
        + 0.10 * df["topic_top1_ratio"].clip(0, 1)
        + 0.10 * df["volume_factor"].clip(0, 1)
        + 0.15 * df["aspect_sentiment_mean"].clip(0, 1)
        + 0.10 * df["aspect_positive_ratio"].clip(0, 1)
    ) * 100

    df["recommend_index_v2"] = df["recommend_index_v2"].round(2)

    print("5) 排序并导出 ...")
    df = df.sort_values("recommend_index_v2", ascending=False)

    out_file = "sku_recommend_index_v2.csv"
    df.to_csv(out_file, index=False, encoding="utf-8-sig")

    print(f"6) 已导出 {out_file}")
    print("\nTop 10 预览：")
    print(df[[
        "sku_id",
        "generated_name",
        "recommend_index_v2",
        "avg_sentiment",
        "aspect_sentiment_mean",
        "aspect_positive_ratio",
        "effective_ratio",
        "topic_top1_ratio",
        "volume_factor"
    ]].head(10))


if __name__ == "__main__":
    main()