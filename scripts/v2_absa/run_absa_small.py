import os
import sys
import pandas as pd
import re
import html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import RAW_COMMENTS_FILE, ABSA_SMALL_RESULTS_FILE, ensure_dirs

# 一定要放在 import pyabsa 之前
os.environ["HF_HOME"] = r"F:\hf_cache"
os.environ["HF_HUB_CACHE"] = r"F:\hf_cache\hub"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from pyabsa import AspectPolarityClassification as APC

INVALID_PATTERNS = [
    "此用户未填写评价内容",
    "NO_MESSAGE",
]

# 先用规则法做候选方面词抽取
ASPECT_KEYWORDS = [
    "续航", "电池", "发热", "散热", "屏幕", "显示", "拍照", "相机",
    "性能", "运行", "速度", "系统", "外观", "手感", "做工", "质感",
    "物流", "快递", "包装", "价格", "性价比", "客服", "服务",
    "音质", "声音", "信号", "网络", "充电", "待机"
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


def extract_aspects(text):
    """
    从评论中抽取候选 aspect
    先用简单关键词匹配，保证稳定可控
    """
    found = []
    for kw in ASPECT_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw)

    # 如果一个都没抽到，可以给一个兜底项
    if not found:
        found = ["整体"]

    return found


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

    df = df.head(20).copy()
    print(f"3) 当前测试样本数: {len(df)}")

    print("4) 开始加载分类器...")
    classifier = APC.SentimentClassifier("multilingual")
    print("5) 分类器加载完成")

    rows = []

    print("6) 开始逐条预测 aspect-level 情感...")
    for i, (_, row) in enumerate(df.iterrows(), 1):
        text = row["clean_content"]
        aspects = extract_aspects(text)

        for aspect in aspects:
            try:
                # 关键：这里不再只传 text，而是传 [text, aspect]
                absa_text = f"[B-ASP]{aspect}[E-ASP] {text}"

                result = classifier.predict(
                    [absa_text],
                    print_result=False,
                    save_result=False
                )

                r = result[0]

                rows.append({
                    "sku_id": row["sku_id"],
                    "item_name": row["item_name"],
                    "score": row["score"],
                    "text": text,
                    "aspect_input": aspect,              # 你手工抽出的 aspect
                    "aspect": str(r.get("aspect", "")),  # 模型返回的 aspect
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
                    "aspect_input": aspect,
                    "aspect": "",
                    "sentiment": f"ERROR: {repr(e)}",
                    "confidence": "",
                    "raw_result": ""
                })

        print(f"   已完成 {i}/{len(df)}，aspects={aspects}")

    out_df = pd.DataFrame(rows)
    out_df.to_csv(ABSA_SMALL_RESULTS_FILE, index=False, encoding="utf-8-sig")
    print(f"7) 已导出 {ABSA_SMALL_RESULTS_FILE}")
    print(f"8) 总输出行数: {len(out_df)}")


if __name__ == "__main__":
    main()