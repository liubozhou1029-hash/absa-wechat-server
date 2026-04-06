import pandas as pd
import ast

def normalize_label(x):
    s = str(x).strip()
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, list) and len(obj) > 0:
            s = str(obj[0]).strip()
    except Exception:
        pass

    s_low = s.lower()

    if "positive" in s_low:
        return "Positive"
    elif "negative" in s_low:
        return "Negative"
    elif "neutral" in s_low:
        return "Neutral"
    else:
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

def label_to_score(label, confidence):
    if confidence is None:
        confidence = 0.5

    if label == "Positive":
        return float(confidence)
    elif label == "Negative":
        return float(1 - confidence)
    elif label == "Neutral":
        return 0.5
    else:
        return None

def main():
    print("1) 读取 absa_full_results.csv ...")
    df = pd.read_csv("absa_full_results.csv")

    print("2) 解析 sentiment / confidence ...")
    df["sentiment_label"] = df["sentiment"].apply(normalize_label)
    df["confidence_value"] = df["confidence"].apply(extract_confidence)

    print("3) 生成数值情感分数 ...")
    df["sentiment_score"] = df.apply(
        lambda row: label_to_score(row["sentiment_label"], row["confidence_value"]),
        axis=1
    )

    print("4) 生成辅助标记列 ...")
    df["is_positive"] = (df["sentiment_label"] == "Positive").astype(int)
    df["is_negative"] = (df["sentiment_label"] == "Negative").astype(int)
    df["is_neutral"] = (df["sentiment_label"] == "Neutral").astype(int)

    out_file = "absa_full_parsed.csv"
    df.to_csv(out_file, index=False, encoding="utf-8-sig")

    print(f"5) 已导出 {out_file}")
    print(df[[
        "sku_id", "item_name", "text",
        "sentiment_label", "confidence_value", "sentiment_score"
    ]].head())

if __name__ == "__main__":
    main()