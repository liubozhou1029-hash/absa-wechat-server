import pandas as pd

def main():
    print("1) 读取 absa_full_parsed.csv ...")
    df = pd.read_csv("absa_full_parsed.csv")

    print("2) 按 sku 聚合 ...")
    sku_feat = df.groupby("sku_id").agg(
        absa_comment_count=("sku_id", "size"),
        aspect_sentiment_mean=("sentiment_score", "mean"),
        aspect_positive_ratio=("is_positive", "mean"),
        aspect_negative_ratio=("is_negative", "mean"),
        aspect_neutral_ratio=("is_neutral", "mean"),
        absa_confidence_mean=("confidence_value", "mean")
    ).reset_index()

    out_file = "sku_absa_features.csv"
    sku_feat.to_csv(out_file, index=False, encoding="utf-8-sig")

    print(f"3) 已导出 {out_file}")
    print(sku_feat.head())

if __name__ == "__main__":
    main()