import sys
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import ABSA_FULL_PARSED_FILE, SKU_ABSA_FEATURES_FILE, ensure_dirs


def main():
    ensure_dirs()

    print(f"1) 读取 {ABSA_FULL_PARSED_FILE} ...")
    df = pd.read_csv(ABSA_FULL_PARSED_FILE)

    print("2) 按 sku 聚合 ...")
    sku_feat = df.groupby("sku_id").agg(
        absa_comment_count=("sku_id", "size"),
        aspect_sentiment_mean=("sentiment_score", "mean"),
        aspect_sentiment_abs_mean=("sentiment_abs", "mean"),
        aspect_positive_ratio=("is_positive", "mean"),
        aspect_negative_ratio=("is_negative", "mean"),
        aspect_neutral_ratio=("is_neutral", "mean"),
        aspect_known_ratio=("is_known_label", "mean"),
        absa_confidence_mean=("confidence_value", "mean")
    ).reset_index()

    sku_feat.to_csv(SKU_ABSA_FEATURES_FILE, index=False, encoding="utf-8-sig")

    print(f"3) 已导出 {SKU_ABSA_FEATURES_FILE}")
    print("\n前5行预览：")
    print(sku_feat.head())


if __name__ == "__main__":
    main()