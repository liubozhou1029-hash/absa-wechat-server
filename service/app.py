from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import math

app = Flask(__name__)
CORS(app)

# =========================
# 1. 读取 CSV 数据
# =========================
recommend_df = pd.read_csv("sku_recommend_index.csv")
top3_df = pd.read_csv("sku_top3_topics.csv")
metrics_df = pd.read_csv("sku_metrics.csv")


def safe_value(x):
    """把 NaN / inf 之类不安全值处理掉，避免 JSON 报错"""
    if pd.isna(x):
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def clean_record(record: dict):
    return {k: safe_value(v) for k, v in record.items()}


# =========================
# 2. 健康检查接口
# =========================
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "code": 0,
        "msg": "backend ok"
    })


# =========================
# 3. 手机推荐列表接口
# =========================
@app.route("/api/phones", methods=["GET"])
def get_phones():
    df = recommend_df.copy()

    # 按推荐指数从高到低排序
    df = df.sort_values("recommend_index", ascending=False)

    # 第一版只取前 20 条
    df = df.head(20)

    result = []
    for _, row in df.iterrows():
        item = {
            "sku_id": str(safe_value(row.get("sku_id"))),
            "name": safe_value(row.get("generated_name")) or "未知手机",
            "recommend_index": round(float(row.get("recommend_index", 0)), 2),
            "avg_sentiment": round(float(row.get("avg_sentiment", 0)), 4) if pd.notna(row.get("avg_sentiment")) else None,
            "effective_ratio": round(float(row.get("effective_ratio", 0)), 4) if pd.notna(row.get("effective_ratio")) else None,
            "effective_comments": int(row.get("effective_comments", 0)) if pd.notna(row.get("effective_comments")) else 0
        }
        result.append(item)

    return jsonify({
        "code": 0,
        "data": result
    })


# =========================
# 4. 手机详情接口
# =========================
@app.route("/api/phone_detail", methods=["GET"])
def get_phone_detail():
    sku_id = request.args.get("sku_id")

    if not sku_id:
        return jsonify({
            "code": 1,
            "msg": "missing sku_id"
        })

    rec_row = recommend_df[recommend_df["sku_id"].astype(str) == str(sku_id)]
    met_row = metrics_df[metrics_df["sku_id"].astype(str) == str(sku_id)]
    topic_rows = top3_df[top3_df["sku_id"].astype(str) == str(sku_id)].copy()

    if rec_row.empty:
        return jsonify({
            "code": 2,
            "msg": "sku not found"
        })

    rec = clean_record(rec_row.iloc[0].to_dict())

    detail = {
        "sku_id": str(rec.get("sku_id")),
        "name": rec.get("generated_name") or "未知手机",
        "recommend_index": round(float(rec.get("recommend_index", 0)), 2),
        "avg_sentiment": round(float(rec.get("avg_sentiment", 0)), 4) if rec.get("avg_sentiment") is not None else None,
        "effective_ratio": round(float(rec.get("effective_ratio", 0)), 4) if rec.get("effective_ratio") is not None else None,
        "effective_comments": int(rec.get("effective_comments", 0)) if rec.get("effective_comments") is not None else 0
    }

    if not met_row.empty:
        met = clean_record(met_row.iloc[0].to_dict())
        detail.update({
            "pos_ratio": round(float(met.get("pos_ratio", 0)), 4) if met.get("pos_ratio") is not None else None,
            "neg_ratio": round(float(met.get("neg_ratio", 0)), 4) if met.get("neg_ratio") is not None else None,
            "topic_top1_ratio": round(float(met.get("topic_top1_ratio", 0)), 4) if met.get("topic_top1_ratio") is not None else None,
            "avg_rating_norm": round(float(met.get("avg_rating_norm", 0)), 4) if met.get("avg_rating_norm") is not None else None,
            "volume_factor": round(float(met.get("volume_factor", 0)), 4) if met.get("volume_factor") is not None else None
        })

    topics = []
    if not topic_rows.empty:
        topic_rows = topic_rows.sort_values("ratio", ascending=False)
        for _, row in topic_rows.iterrows():
            topics.append({
                "topic_id": safe_value(row.get("topic_id")),
                "ratio": round(float(row.get("ratio", 0)), 4) if pd.notna(row.get("ratio")) else None,
                "keywords": safe_value(row.get("topic_keywords")) or ""
            })

    return jsonify({
        "code": 0,
        "data": {
            "detail": detail,
            "topics": topics
        }
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)