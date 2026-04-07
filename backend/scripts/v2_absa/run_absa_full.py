import os
import sys
import warnings
import pandas as pd
import re
import html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import (
    RAW_COMMENTS_FILE,
    ABSA_FULL_RESULTS_FILE,
    ABSA_FULL_RESULTS_PARTIAL_FILE,
    ensure_dirs,
    HF_CACHE_DIR,
)

os.environ["HF_HOME"] = str(HF_CACHE_DIR)
os.environ["HF_HUB_CACHE"] = str(HF_CACHE_DIR / "hub")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

warnings.filterwarnings("ignore")

from pyabsa import AspectPolarityClassification as APC

INVALID_PATTERNS = [
    "此用户未填写评价内容",
    "NO_MESSAGE",
]

ASPECT_KEYWORDS = [
    "续航", "电池", "耗电", "掉电", "发热", "发烫", "散热",
    "屏幕", "显示", "亮度", "拍照", "相机", "成像",
    "性能", "运行", "速度", "卡顿", "死机", "闪退",
    "系统", "外观", "手感", "做工", "质感",
    "物流", "快递", "包装", "价格", "性价比",
    "客服", "服务", "音质", "声音", "信号", "网络",
    "充电", "待机"
]


def extract_aspects(text):
    found = []
    for kw in ASPECT_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw)

    if not found:
        found = ["整体"]

    return found


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
    ensure_dirs()

    print("HF_HOME =", os.environ.get("HF_HOME"))
    print("HF_HUB_CACHE =", os.environ.get("HF_HUB_CACHE"))

    print("1) 开始读取数据...")
    df = pd.read_csv(RAW_COMMENTS_FILE)
    df = df[["sku_id", "item_name", "content", "score"]].copy()

    print("2) 开始清洗文本...")
    df["clean_content"] = df["content"].apply(clean_text)
    df = df[df["clean_content"].str.len() > 5].copy()
    print(f"3) 清洗后样本数: {len(df)}")

    print("4) 开始加载分类器...")
    classifier = APC.SentimentClassifier("multilingual", cal_perplexity=False)
    print("5) 分类器加载完成")

    rows = []
    total = len(df)

    print("6) 开始逐条预测 aspect-level 情感...")

    for i, (_, row) in enumerate(df.iterrows(), 1):
        text = row["clean_content"]
        aspects = extract_aspects(text)

        for aspect in aspects:
            try:
                absa_text = f"[B-ASP]{aspect}[E-ASP] {text}"

                result = classifier.predict(
                    [absa_text],
                    print_result=False,
                    save_result=False,
                    ignore_error=True
                )

                if result and len(result) > 0:
                    r = result[0]
                    rows.append({
                        "sku_id": row["sku_id"],
                        "item_name": row["item_name"],
                        "score": row["score"],
                        "text": text,
                        "aspect_input": aspect,
                        "absa_text": absa_text,
                        "aspect": str(r.get("aspect", "")),
                        "sentiment": str(r.get("sentiment", "")),
                        "confidence": str(r.get("confidence", "")),
                        "raw_result": str(r)
                    })
                else:
                    rows.append({
                        "sku_id": row["sku_id"],
                        "item_name": row["item_name"],
                        "score": row["score"],
                        "text": text,
                        "aspect_input": aspect,
                        "absa_text": absa_text,
                        "aspect": "",
                        "sentiment": "ERROR: empty_result",
                        "confidence": "",
                        "raw_result": ""
                    })

            except Exception as e:
                rows.append({
                    "sku_id": row["sku_id"],
                    "item_name": row["item_name"],
                    "score": row["score"],
                    "text": text,
                    "aspect_input": aspect,
                    "absa_text": f"[B-ASP]{aspect}[E-ASP] {text}",
                    "aspect": "",
                    "sentiment": f"ERROR: {repr(e)}",
                    "confidence": "",
                    "raw_result": ""
                })

        if i % 50 == 0 or i == total:
            print(f"   已完成 {i}/{total}，当前评论aspects={aspects}")

        if i % 100 == 0 or i == total:
            pd.DataFrame(rows).to_csv(
                ABSA_FULL_RESULTS_PARTIAL_FILE,
                index=False,
                encoding="utf-8-sig"
            )

    out_df = pd.DataFrame(rows)
    out_df.to_csv(ABSA_FULL_RESULTS_FILE, index=False, encoding="utf-8-sig")
    print(f"7) 已导出 {ABSA_FULL_RESULTS_FILE}")


if __name__ == "__main__":
    main()