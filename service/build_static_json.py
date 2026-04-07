import pandas as pd
import os
import math
import json

# =========================
# 1. 路径配置
# =========================
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parent
MINIAPP_DATA_DIR = REPO_ROOT / "miniapp" / "utils" / "data"

RECOMMEND_CSV = SERVICE_DIR / "sku_recommend_index.csv"
TOPICS_CSV = SERVICE_DIR / "sku_top3_topics.csv"
METRICS_CSV = SERVICE_DIR / "sku_metrics.csv"

PHONES_JS = MINIAPP_DATA_DIR / "phones.js"
DETAILS_JS = MINIAPP_DATA_DIR / "details.js"

os.makedirs(MINIAPP_DATA_DIR, exist_ok=True)


# =========================
# 2. 工具函数
# =========================
def safe_value(x):
    if pd.isna(x):
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def round_or_none(x, n=4):
    if x is None or pd.isna(x):
        return None
    return round(float(x), n)


def to_pretty_js_module(obj):
    json_str = json.dumps(obj, ensure_ascii=False, indent=2)
    return "module.exports = " + json_str + ";\n"


def build_display_id(idx: int) -> str:
    """生成数据编号，例如 001 / 002 / 003"""
    return f"{idx:03d}"


# =========================
# 3. 读取 CSV
# =========================
recommend_df = pd.read_csv(RECOMMEND_CSV)
top3_df = pd.read_csv(TOPICS_CSV)
metrics_df = pd.read_csv(METRICS_CSV)

recommend_df = recommend_df.sort_values("recommend_index", ascending=False).reset_index(drop=True)

# 首版建议控制数量，避免体积过大
recommend_df = recommend_df.head(50).copy()


# =========================
# 4. 生成 phones.js
# =========================
phones_list = []

for idx, (_, row) in enumerate(recommend_df.iterrows(), start=1):
    sku_id = str(safe_value(row.get("sku_id")))
    original_name = safe_value(row.get("generated_name")) or "未知数据"
    display_id = build_display_id(idx)

    item = {
        "sku_id": sku_id,
        "display_id": display_id,
        "display_name": f"数据编号 {display_id}",
        "original_name": original_name,   # 前端默认不展示
        "sentiment_index": round_or_none(row.get("recommend_index"), 2),
        "avg_sentiment": round_or_none(row.get("avg_sentiment"), 4),
        "effective_ratio": round_or_none(row.get("effective_ratio"), 4),
        "effective_comments": int(row.get("effective_comments", 0)) if pd.notna(row.get("effective_comments")) else 0
    }
    phones_list.append(item)

with open(PHONES_JS, "w", encoding="utf-8") as f:
    f.write(to_pretty_js_module(phones_list))


# =========================
# 5. 生成 details.js
# =========================
details_dict = {}

for idx, (_, row) in enumerate(recommend_df.iterrows(), start=1):
    sku_id = str(safe_value(row.get("sku_id")))
    original_name = safe_value(row.get("generated_name")) or "未知数据"
    display_id = build_display_id(idx)

    detail = {
        "sku_id": sku_id,
        "display_id": display_id,
        "display_name": f"数据编号 {display_id}",
        "original_name": original_name,   # 前端默认不展示
        "sentiment_index": round_or_none(row.get("recommend_index"), 2),
        "avg_sentiment": round_or_none(row.get("avg_sentiment"), 4),
        "effective_ratio": round_or_none(row.get("effective_ratio"), 4),
        "effective_comments": int(row.get("effective_comments", 0)) if pd.notna(row.get("effective_comments")) else 0
    }

    met_row = metrics_df[metrics_df["sku_id"].astype(str) == sku_id]
    if not met_row.empty:
        met = met_row.iloc[0]
        detail.update({
            "pos_ratio": round_or_none(met.get("pos_ratio"), 4),
            "neg_ratio": round_or_none(met.get("neg_ratio"), 4),
            "topic_top1_ratio": round_or_none(met.get("topic_top1_ratio"), 4),
            "avg_rating_norm": round_or_none(met.get("avg_rating_norm"), 4),
            "volume_factor": round_or_none(met.get("volume_factor"), 4)
        })
    else:
        detail.update({
            "pos_ratio": None,
            "neg_ratio": None,
            "topic_top1_ratio": None,
            "avg_rating_norm": None,
            "volume_factor": None
        })

    topic_rows = top3_df[top3_df["sku_id"].astype(str) == sku_id].copy()
    topic_rows = topic_rows.sort_values("ratio", ascending=False)

    topics = []
    for _, t in topic_rows.iterrows():
        topics.append({
            "topic_id": safe_value(t.get("topic_id")),
            "ratio": round_or_none(t.get("ratio"), 4),
            "keywords": safe_value(t.get("topic_keywords")) or ""
        })

    details_dict[sku_id] = {
        "detail": detail,
        "topics": topics
    }

with open(DETAILS_JS, "w", encoding="utf-8") as f:
    f.write(to_pretty_js_module(details_dict))

print("已生成：")
print(PHONES_JS)
print(DETAILS_JS)
print(f"共生成 {len(phones_list)} 条数据")