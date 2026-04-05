import csv
import json
import re
from pathlib import Path
from typing import Any


# ========= 你可以按需修改的路径 =========
OLD_DETAILS_JS = Path(r"F:\WeChat project\goodsrecommend\utils\data\details.js")
OLD_PHONES_JS = Path(r"F:\WeChat project\goodsrecommend\utils\data\phones.js")
NEW_CSV = Path(r"F:\Pythoncode\goodsrecommend\sku_recommend_index_v2.csv")
OUT_DETAILS_JS = Path(r"F:\WeChat project\goodsrecommend\utils\data\details_new.js")
OUT_PHONES_JS = Path(r"F:\WeChat project\goodsrecommend\utils\data\phones_new.js")
# ======================================


def load_commonjs_module_obj(js_path: Path) -> Any:
    """
    读取形如：
    module.exports = {...};
    或
    module.exports = [...];
    的 JS 文件，提取后面的 JSON/JS 对象文本并转成 Python 对象。
    """
    text = js_path.read_text(encoding="utf-8")

    prefix = "module.exports ="
    idx = text.find(prefix)
    if idx == -1:
        raise ValueError(f"文件 {js_path} 中未找到 'module.exports ='")

    body = text[idx + len(prefix):].strip()

    if body.endswith(";"):
        body = body[:-1].strip()

    # 这里你的数据文件本质上就是 JSON 兼容格式
    return json.loads(body)


def write_commonjs(js_path: Path, data: Any) -> None:
    """
    写回 CommonJS 格式：
    module.exports = ...
    """
    content = "module.exports = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    js_path.write_text(content, encoding="utf-8")


def to_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def to_int(value, default=None):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def load_csv_map(csv_path: Path) -> dict[str, dict[str, Any]]:
    """
    按 sku_id 建索引。
    """
    result: dict[str, dict[str, Any]] = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku_id = str(row.get("sku_id", "")).strip()
            if not sku_id:
                continue
            result[sku_id] = row

    return result


def pick_real_name(csv_row: dict[str, Any] | None, old_detail: dict[str, Any]) -> str:
    """
    真实商品名优先级：
    1. 新版 generated_name
    2. 旧版 original_name
    3. 旧版 display_name
    """
    if csv_row:
        generated_name = str(csv_row.get("generated_name", "")).strip()
        if generated_name:
            return generated_name

    original_name = str(old_detail.get("original_name", "")).strip()
    if original_name:
        return original_name

    return str(old_detail.get("display_name", "")).strip()


def build_new_details(
    old_details: dict[str, Any],
    csv_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    new_details: dict[str, Any] = {}

    for sku_id, item in old_details.items():
        if not isinstance(item, dict):
            continue

        detail = item.get("detail", {}) or {}
        topics = item.get("topics", []) or []

        csv_row = csv_map.get(str(sku_id))

        real_name = pick_real_name(csv_row, detail)

        new_detail = {
            # 基础身份字段
            "sku_id": str(detail.get("sku_id", sku_id)),
            "display_id": str(detail.get("display_id", "")),
            # 这里直接让 display_name 也显示真实名字，页面不改也能显示真实名
            "display_name": real_name,
            "original_name": real_name,

            # ===== 旧版字段，保留 =====
            "sentiment_index": to_float(detail.get("sentiment_index"), 0.0),
            "avg_sentiment": to_float(
                (csv_row.get("avg_sentiment") if csv_row else detail.get("avg_sentiment")),
                to_float(detail.get("avg_sentiment"), 0.0)
            ),
            "effective_ratio": to_float(
                (csv_row.get("effective_ratio") if csv_row else detail.get("effective_ratio")),
                to_float(detail.get("effective_ratio"), 0.0)
            ),
            "effective_comments": to_int(
                (csv_row.get("effective_comments") if csv_row else detail.get("effective_comments")),
                to_int(detail.get("effective_comments"), 0)
            ),
            "pos_ratio": to_float(
                (csv_row.get("pos_ratio") if csv_row else detail.get("pos_ratio")),
                to_float(detail.get("pos_ratio"), 0.0)
            ),
            "neg_ratio": to_float(
                (csv_row.get("neg_ratio") if csv_row else detail.get("neg_ratio")),
                to_float(detail.get("neg_ratio"), 0.0)
            ),
            "topic_top1_ratio": to_float(
                (csv_row.get("topic_top1_ratio") if csv_row else detail.get("topic_top1_ratio")),
                to_float(detail.get("topic_top1_ratio"), 0.0)
            ),
            "avg_rating_norm": to_float(
                (csv_row.get("avg_rating_norm") if csv_row else detail.get("avg_rating_norm")),
                to_float(detail.get("avg_rating_norm"), 0.0)
            ),
            "volume_factor": to_float(
                (csv_row.get("volume_factor") if csv_row else detail.get("volume_factor")),
                to_float(detail.get("volume_factor"), 0.0)
            ),

            # ===== 新版字段，新增 =====
            "total_comments": to_int(csv_row.get("total_comments") if csv_row else None, None),
            "n_sentiment": to_int(csv_row.get("n_sentiment") if csv_row else None, None),
            "std_sentiment": to_float(csv_row.get("std_sentiment") if csv_row else None, None),

            "recommend_index_v2": to_float(csv_row.get("recommend_index_v2") if csv_row else None, None),
            "brand_guess": str(csv_row.get("brand_guess", "")).strip() if csv_row else "",
            "model_guess": str(csv_row.get("model_guess", "")).strip() if csv_row else "",

            "absa_comment_count": to_int(csv_row.get("absa_comment_count") if csv_row else None, None),
            "aspect_sentiment_mean": to_float(csv_row.get("aspect_sentiment_mean") if csv_row else None, None),
            "aspect_positive_ratio": to_float(csv_row.get("aspect_positive_ratio") if csv_row else None, None),
            "aspect_negative_ratio": to_float(csv_row.get("aspect_negative_ratio") if csv_row else None, None),
            "aspect_neutral_ratio": to_float(csv_row.get("aspect_neutral_ratio") if csv_row else None, None),
            "absa_confidence_mean": to_float(csv_row.get("absa_confidence_mean") if csv_row else None, None),
        }

        new_details[str(sku_id)] = {
            "detail": new_detail,
            "topics": topics
        }

    return new_details


def build_new_phones(
    new_details: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    根据新版 details 生成新版 phones 列表。
    """
    result: list[dict[str, Any]] = []

    for sku_id, item in new_details.items():
        detail = item.get("detail", {}) or {}

        result.append({
            "sku_id": detail.get("sku_id", sku_id),
            "display_id": detail.get("display_id", ""),
            "display_name": detail.get("display_name", ""),
            "original_name": detail.get("original_name", ""),

            # 旧字段保留，避免老页面直接报错
            "sentiment_index": detail.get("sentiment_index", 0.0),
            "avg_sentiment": detail.get("avg_sentiment", 0.0),
            "effective_ratio": detail.get("effective_ratio", 0.0),
            "effective_comments": detail.get("effective_comments", 0),

            # 新字段新增
            "recommend_index_v2": detail.get("recommend_index_v2", None),
            "aspect_sentiment_mean": detail.get("aspect_sentiment_mean", None),
            "aspect_positive_ratio": detail.get("aspect_positive_ratio", None),
            "aspect_negative_ratio": detail.get("aspect_negative_ratio", None),
            "absa_confidence_mean": detail.get("absa_confidence_mean", None),
        })

    # 默认按新版推荐指数降序；若缺失则按旧 sentiment_index 降序
    result.sort(
        key=lambda x: (
            x["recommend_index_v2"] if x["recommend_index_v2"] is not None else x.get("sentiment_index", 0.0)
        ),
        reverse=True
    )

    # 重新生成 display_id，保持列表展示更整齐
    for idx, item in enumerate(result, start=1):
        item["display_id"] = f"{idx:03d}"

    return result


def sync_display_id_back(new_details: dict[str, Any], new_phones: list[dict[str, Any]]) -> None:
    """
    让 details 中的 display_id 与 phones 列表排序一致。
    """
    for item in new_phones:
        sku_id = str(item["sku_id"])
        if sku_id in new_details:
            new_details[sku_id]["detail"]["display_id"] = item["display_id"]


def main():
    print("1) 读取旧版 details.js ...")
    old_details = load_commonjs_module_obj(OLD_DETAILS_JS)

    print("2) 读取旧版 phones.js（仅用于兼容检查）...")
    _ = load_commonjs_module_obj(OLD_PHONES_JS)

    print("3) 读取新版 sku_recommend_index_v2.csv ...")
    csv_map = load_csv_map(NEW_CSV)

    print("4) 构建新版 details 数据 ...")
    new_details = build_new_details(old_details, csv_map)

    print("5) 构建新版 phones 数据 ...")
    new_phones = build_new_phones(new_details)

    print("6) 同步 display_id ...")
    sync_display_id_back(new_details, new_phones)

    print("7) 写出 phones_new.js / details_new.js ...")
    write_commonjs(OUT_PHONES_JS, new_phones)
    write_commonjs(OUT_DETAILS_JS, new_details)

    print("完成。")
    print(f"已生成: {OUT_PHONES_JS}")
    print(f"已生成: {OUT_DETAILS_JS}")
    print(f"phones 条数: {len(new_phones)}")
    print(f"details 条数: {len(new_details)}")

    if new_phones:
        print("\nphones_new.js 第一条预览：")
        print(json.dumps(new_phones[0], ensure_ascii=False, indent=2))

        first_sku = str(new_phones[0]["sku_id"])
        print("\ndetails_new.js 对应 detail 预览：")
        print(json.dumps(new_details[first_sku]["detail"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()