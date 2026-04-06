import sys
import ast
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import ABSA_SMALL_RESULTS_FILE, ABSA_SMALL_PARSED_FILE, ensure_dirs


def normalize_label(x):
    if x is None:
        return "Unknown"

    s = str(x).strip()
    s_low = s.lower()

    if "positive" in s_low:
        return "Positive"
    if "negative" in s_low:
        return "Negative"
    if "neutral" in s_low:
        return "Neutral"

    try:
        obj = ast.literal_eval(s)

        if isinstance(obj, (list, tuple)) and len(obj) > 0:
            joined = " ".join(str(v) for v in obj).lower()
            if "positive" in joined:
                return "Positive"
            if "negative" in joined:
                return "Negative"
            if "neutral" in joined:
                return "Neutral"

        obj_s = str(obj).lower()
        if "positive" in obj_s:
            return "Positive"
        if "negative" in obj_s:
            return "Negative"
        if "neutral" in obj_s:
            return "Neutral"

    except Exception:
        pass

    return "Unknown"


def extract_confidence(x):
    s = str(x).strip()

    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, list) and len(obj) > 0:
            return float(obj[0])
        return float(obj)
    except Exception:
        return None


def clip_confidence(confidence, default=0.5):
    if confidence is None or pd.isna(confidence):
        return default
    try:
        confidence = float(confidence)
    except Exception:
        return default
    return max(0.0, min(1.0, confidence))


def label_to_score(label, confidence):
    confidence = clip_confidence(confidence, default=0.5)

    if label == "Positive":
        return confidence
    elif label == "Negative":
        return -confidence
    elif label == "Neutral":
        return 0.0
    else:
        return 0.0


def main():
    ensure_dirs()

    print(f"1) 读取 {ABSA_SMALL_RESULTS_FILE} ...")
    df = pd.read_csv(ABSA_SMALL_RESULTS_FILE)

    print("2) 解析 sentiment / confidence ...")
    df["sentiment_label"] = df["sentiment"].apply(normalize_label)
    df["confidence_value"] = df["confidence"].apply(extract_confidence)
    df["confidence_value"] = df["confidence_value"].apply(clip_confidence)

    print("3) 生成数值情感分数 ...")
    df["sentiment_score"] = df.apply(
        lambda row: label_to_score(row["sentiment_label"], row["confidence_value"]),
        axis=1
    )
    df["sentiment_score"] = df["sentiment_score"].fillna(0.0)

    print("4) 生成辅助标记列 ...")
    df["is_positive"] = (df["sentiment_label"] == "Positive").astype(int)
    df["is_negative"] = (df["sentiment_label"] == "Negative").astype(int)
    df["is_neutral"] = (df["sentiment_label"] == "Neutral").astype(int)
    df["is_known_label"] = df["sentiment_label"].isin(
        ["Positive", "Negative", "Neutral"]
    ).astype(int)

    print("5) 生成额外分析列 ...")
    df["sentiment_abs"] = df["sentiment_score"].abs()
    df["sentiment_direction"] = df["sentiment_score"].apply(
        lambda x: "Positive" if pd.notna(x) and x > 0
        else ("Negative" if pd.notna(x) and x < 0
              else ("Neutral" if pd.notna(x) and x == 0 else "Unknown"))
    )

    df.to_csv(ABSA_FULL_PARSED_FILE, index=False, encoding="utf-8-sig")

    print(f"6) 已导出 {ABSA_FULL_PARSED_FILE}")
    print("\n前5行预览：")
    print(df[[
        "sku_id", "item_name", "text",
        "sentiment", "confidence",
        "sentiment_label", "confidence_value", "sentiment_score"
    ]].head())

    print("\n情感标签分布：")
    print(df["sentiment_label"].value_counts(dropna=False))

    print("\n情感分数统计：")
    print(df["sentiment_score"].describe())


if __name__ == "__main__":
    main()