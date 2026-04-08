import pandas as pd
import os
import math
import json
from pathlib import Path

# =========================
# 1. 路径配置
# =========================
SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parent
MINIAPP_DATA_DIR = REPO_ROOT / "miniapp" / "utils" / "data"

RECOMMEND_CSV    = SERVICE_DIR / "sku_recommend_index.csv"
RECOMMEND_V2_CSV = SERVICE_DIR / "sku_recommend_index_v2.csv"   # 可选，含 ABSA 字段
TOPICS_CSV       = SERVICE_DIR / "sku_top3_topics.csv"
METRICS_CSV      = SERVICE_DIR / "sku_metrics.csv"

PHONES_JS  = MINIAPP_DATA_DIR / "phones.js"
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


def safe_float(x, default=0.0):
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def round_or_none(x, n=4):
    if x is None or pd.isna(x):
        return None
    try:
        return round(float(x), n)
    except Exception:
        return None


def int_or_zero(x):
    if x is None or pd.isna(x):
        return 0
    try:
        return int(float(x))
    except Exception:
        return 0


def to_pretty_js_module(obj):
    json_str = json.dumps(obj, ensure_ascii=False, indent=2)
    return "module.exports = " + json_str + ";\n"


def build_display_id(idx: int) -> str:
    return f"{idx:03d}"


def build_real_name(row):
    val = safe_value(row.get("generated_name"))
    if val is not None and str(val).strip() != "":
        return str(val)
    return "未知数据"


def compute_recommend_score(v1_row, v2_row=None) -> float:
    """
    百分制推荐分（0~100）。

    有 ABSA 数据时（v2_row 不为 None）：
      融合 V1 基础分量 + ABSA 方面级特征，权重合计 = 1.0
        0.30 × avg_sentiment          整体情感
        0.10 × avg_rating_norm        星级评分
        0.15 × effective_ratio        有效评论率
        0.10 × topic_top1_ratio       话题一致性
        0.05 × volume_factor          评论量因子
        0.20 × aspect_positive_ratio  ABSA 正向占比
        0.10 × (1 − aspect_negative_ratio)  ABSA 负向逆
      合计 × 100 → 自然落在 0~100

    无 ABSA 数据时：
      直接使用 V1 recommend_index（原公式，已是 0~100）
    """
    if v2_row is not None:
        avg_sent  = safe_float(v2_row.get("avg_sentiment"),          0.0)
        avg_rat   = safe_float(v2_row.get("avg_rating_norm"),        0.0)
        eff_ratio = safe_float(v2_row.get("effective_ratio"),        0.0)
        consist   = safe_float(v2_row.get("topic_top1_ratio"),       0.0)
        volume    = safe_float(v2_row.get("volume_factor"),          0.0)
        asp_pos   = safe_float(v2_row.get("aspect_positive_ratio"),  0.0)
        asp_neg   = safe_float(v2_row.get("aspect_negative_ratio"),  0.0)

        score = (
            0.30 * avg_sent
            + 0.10 * avg_rat
            + 0.15 * eff_ratio
            + 0.10 * consist
            + 0.05 * volume
            + 0.20 * asp_pos
            + 0.10 * (1.0 - asp_neg)
        ) * 100
    else:
        score = safe_float(v1_row.get("recommend_index"), 0.0)

    return round(max(0.0, min(100.0, score)), 2)


# =========================
# 3. 读取 CSV
# =========================
recommend_df = pd.read_csv(RECOMMEND_CSV)
top3_df      = pd.read_csv(TOPICS_CSV)
metrics_df   = pd.read_csv(METRICS_CSV)

if RECOMMEND_V2_CSV.exists():
    recommend_v2_df = pd.read_csv(RECOMMEND_V2_CSV)
else:
    recommend_v2_df = pd.DataFrame()

# 构建 v2 快速索引（sku_id → row）
v2_map = {}
if not recommend_v2_df.empty and "sku_id" in recommend_v2_df.columns:
    for _, r in recommend_v2_df.iterrows():
        v2_map[str(r["sku_id"])] = r

# 先对所有 V1 记录计算 recommend_score，再按分数降序取前 50
recommend_df["_recommend_score"] = recommend_df.apply(
    lambda r: compute_recommend_score(r, v2_map.get(str(r["sku_id"]))),
    axis=1,
)
recommend_df = (
    recommend_df
    .sort_values("_recommend_score", ascending=False)
    .reset_index(drop=True)
    .head(50)
    .copy()
)


# =========================
# 4. 生成 phones.js（列表页）
# =========================
phones_list = []

for idx, (_, row) in enumerate(recommend_df.iterrows(), start=1):
    sku_id       = str(safe_value(row.get("sku_id")))
    real_name    = build_real_name(row)
    display_id   = build_display_id(idx)
    v2_row       = v2_map.get(sku_id)
    has_absa     = v2_row is not None

    item = {
        "sku_id":       sku_id,
        "display_id":   display_id,
        "display_name": real_name,
        "original_name": real_name,

        # 核心展示分（百分制，0~100）
        "recommend_score": round_or_none(row.get("_recommend_score"), 2),

        # 列表页辅助指标
        "avg_sentiment":      round_or_none(row.get("avg_sentiment"), 4),
        "effective_ratio":    round_or_none(row.get("effective_ratio"), 4),
        "effective_comments": int_or_zero(row.get("effective_comments")),
        "total_comments":     int_or_zero(row.get("total_comments")),
        "has_absa":           has_absa,
    }

    if has_absa:
        item.update({
            "absa_comment_count":    int_or_zero(v2_row.get("absa_comment_count")),
            "aspect_sentiment_mean": round_or_none(v2_row.get("aspect_sentiment_mean"), 4),
            "aspect_positive_ratio": round_or_none(v2_row.get("aspect_positive_ratio"), 4),
            "aspect_negative_ratio": round_or_none(v2_row.get("aspect_negative_ratio"), 4),
            "absa_confidence_mean":  round_or_none(v2_row.get("absa_confidence_mean"), 4),
        })
    else:
        item.update({
            "absa_comment_count":    0,
            "aspect_sentiment_mean": None,
            "aspect_positive_ratio": None,
            "aspect_negative_ratio": None,
            "absa_confidence_mean":  None,
        })

    phones_list.append(item)

with open(PHONES_JS, "w", encoding="utf-8") as f:
    f.write(to_pretty_js_module(phones_list))


# =========================
# 5. 生成 details.js（详情页）
# =========================
details_dict = {}

for idx, (_, row) in enumerate(recommend_df.iterrows(), start=1):
    sku_id     = str(safe_value(row.get("sku_id")))
    real_name  = build_real_name(row)
    display_id = build_display_id(idx)
    v2_row     = v2_map.get(sku_id)
    has_absa   = v2_row is not None

    detail = {
        "sku_id":       sku_id,
        "display_id":   display_id,
        "display_name": real_name,
        "original_name": real_name,

        # 核心展示分（百分制）
        "recommend_score": round_or_none(row.get("_recommend_score"), 2),
        # V1 情感推荐分（用于详情页分数来源说明）
        "v1_score": round_or_none(row.get("recommend_index"), 2),
        "has_absa": has_absa,

        # 整体情感统计
        "avg_sentiment":      round_or_none(row.get("avg_sentiment"), 4),
        "std_sentiment":      round_or_none(row.get("std_sentiment"), 4),
        "n_sentiment":        int_or_zero(row.get("n_sentiment")),
        "effective_ratio":    round_or_none(row.get("effective_ratio"), 4),
        "effective_comments": int_or_zero(row.get("effective_comments")),
        "total_comments":     int_or_zero(row.get("total_comments")),
    }

    # metrics 表补充
    met_row = metrics_df[metrics_df["sku_id"].astype(str) == sku_id]
    if not met_row.empty:
        met = met_row.iloc[0]
        detail.update({
            "pos_ratio":         round_or_none(met.get("pos_ratio"), 4),
            "neg_ratio":         round_or_none(met.get("neg_ratio"), 4),
            "topic_top1_ratio":  round_or_none(met.get("topic_top1_ratio"), 4),
            "avg_rating_norm":   round_or_none(met.get("avg_rating_norm"), 4),
            "volume_factor":     round_or_none(met.get("volume_factor"), 4),
        })
    else:
        detail.update({
            "pos_ratio": None, "neg_ratio": None,
            "topic_top1_ratio": None, "avg_rating_norm": None, "volume_factor": None,
        })

    # ABSA 方面级字段
    if has_absa:
        detail.update({
            "absa_comment_count":        int_or_zero(v2_row.get("absa_comment_count")),
            "aspect_sentiment_mean":     round_or_none(v2_row.get("aspect_sentiment_mean"), 4),
            "aspect_sentiment_abs_mean": round_or_none(v2_row.get("aspect_sentiment_abs_mean"), 4),
            "aspect_positive_ratio":     round_or_none(v2_row.get("aspect_positive_ratio"), 4),
            "aspect_negative_ratio":     round_or_none(v2_row.get("aspect_negative_ratio"), 4),
            "aspect_neutral_ratio":      round_or_none(v2_row.get("aspect_neutral_ratio"), 4),
            "aspect_known_ratio":        round_or_none(v2_row.get("aspect_known_ratio"), 4),
            "absa_confidence_mean":      round_or_none(v2_row.get("absa_confidence_mean"), 4),
        })
    else:
        detail.update({
            "absa_comment_count": 0,
            "aspect_sentiment_mean": None, "aspect_sentiment_abs_mean": None,
            "aspect_positive_ratio": None, "aspect_negative_ratio": None,
            "aspect_neutral_ratio": None,  "aspect_known_ratio": None,
            "absa_confidence_mean": None,
        })

    # 主题关键词
    topic_rows = top3_df[top3_df["sku_id"].astype(str) == sku_id].copy()
    topic_rows = topic_rows.sort_values("ratio", ascending=False)
    topics = [
        {
            "topic_id": safe_value(t.get("topic_id")),
            "ratio":    round_or_none(t.get("ratio"), 4),
            "keywords": safe_value(t.get("topic_keywords")) or "",
        }
        for _, t in topic_rows.iterrows()
    ]

    details_dict[sku_id] = {"detail": detail, "topics": topics}

with open(DETAILS_JS, "w", encoding="utf-8") as f:
    f.write(to_pretty_js_module(details_dict))

print("已生成：")
print(PHONES_JS)
print(DETAILS_JS)
print(f"共生成 {len(phones_list)} 条数据")