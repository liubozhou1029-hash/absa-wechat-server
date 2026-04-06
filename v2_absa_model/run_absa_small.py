import os

# 一定要放在 import pyabsa 之前
os.environ["HF_HOME"] = r"F:\hf_cache"
os.environ["HF_HUB_CACHE"] = r"F:\hf_cache\hub"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import pandas as pd
import re
import html
from pyabsa import AspectPolarityClassification as APC

INVALID_PATTERNS = [
    "此用户未填写评价内容",
    "NO_MESSAGE",
]

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    for p in INVALID_PATTERNS:
        text = text.replace(p, " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def main():
    print("HF_HOME =", os.environ.get("HF_HOME"))
    print("HF_HUB_CACHE =", os.environ.get("HF_HUB_CACHE"))

    print("1) 开始读取数据...")
    df = pd.read_csv("京东评论数据.csv")
    df = df[["sku_id", "item_name", "content", "score"]].copy()

    print("2) 开始清洗文本...")
    df["clean_content"] = df["content"].apply(clean_text)
    df = df[df["clean_content"].str.len() > 5].copy()

    df = df.head(20).copy()
    print(f"3) 当前测试样本数: {len(df)}")

    print("4) 开始加载分类器...")
    classifier = APC.SentimentClassifier("multilingual")
    print("5) 分类器加载完成")

    rows = []

    print("6) 开始逐条预测...")
    for i, (_, row) in enumerate(df.iterrows(), 1):
        text = row["clean_content"]

        try:
            result = classifier.predict(
                [text],
                print_result=False,
                save_result=False
            )

            r = result[0]

            rows.append({
                "sku_id": row["sku_id"],
                "item_name": row["item_name"],
                "score": row["score"],
                "text": text,
                "aspect": str(r.get("aspect", "")),
                "sentiment": str(r.get("sentiment", "")),
                "confidence": str(r.get("confidence", "")),
                "raw_result": str(r)
            })

        except Exception as e:
            rows.append({
                "sku_id": row["sku_id"],
                "item_name": row["item_name"],
                "score": row["score"],
                "text": text,
                "aspect": "",
                "sentiment": f"ERROR: {repr(e)}",
                "confidence": "",
                "raw_result": ""
            })

        print(f"   已完成 {i}/{len(df)}")

    out_df = pd.DataFrame(rows)
    out_df.to_csv("absa_small_results.csv", index=False, encoding="utf-8-sig")
    print("7) 已导出 absa_small_results.csv")

if __name__ == "__main__":
    main()