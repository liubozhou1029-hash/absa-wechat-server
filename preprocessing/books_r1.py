"""
书籍类R1精化脚本
只重跑reviews_final.csv中cat==书籍的行，其余品类原样保留
直接在原文件上修改，输出reviews_final.csv（覆盖）
"""

import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from openai import OpenAI

INPUT_FILE    = "reviews_final.csv"      # 直接读取并覆盖
PROGRESS_FILE = "progress_books_r1.json"

MAX_WORKERS = 15
BATCH_SIZE  = 50
MODEL       = "deepseek-reasoner"
MAX_TOKENS  = 3000

UNCERTAIN_KEYWORDS = ["无法", "不确定", "未知", "无从", "看不出", "无法判断", "不清楚"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("books_r1.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

PROMPT = (
    "你是资深图书编辑，擅长从书评中识别书名。\n"
    "请从以下书评中推断被评论的【书名】。\n\n"
    "规则：\n"
    "① 若评论中明确出现书名，直接返回书名\n"
    "② 若评论提到了作者，返回'作者名的作品'\n"
    "③ 若完全无法判断，只返回'无法确定'\n\n"
    "严禁：不允许输出评论中未明确出现的书名，不允许根据内容推测编造书名。\n"
    "重要：只返回书名本身或'无法确定'，不加引号，不解释，不超过25字。不需要长篇思考，直接给出答案。\n\n"
    "书评：{review}"
)


def is_uncertain(result):
    return any(kw in result for kw in UNCERTAIN_KEYWORDS)


def refine_entity(client, row_id, review, old_predict):
    prompt = PROMPT.format(review=review[:500])
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL, max_tokens=MAX_TOKENS, temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            result = (response.choices[0].message.content or "").strip().strip("「」『』【】《》\"'")
            if not result:
                result = "抽取失败"
            status = "uncertain" if is_uncertain(result) else "ok"
            return {"id": row_id, "predict": result, "status": status}
        except Exception as e:
            err = str(e)
            if "rate" in err.lower() or "429" in err:
                wait = 2 ** attempt * 8
                log.warning(f"Row {row_id} 限流，{wait}秒后重试...")
                time.sleep(wait)
            else:
                log.error(f"Row {row_id} 错误(attempt {attempt+1}): {err[:80]}")
                if attempt == 2:
                    return {"id": row_id, "predict": old_predict, "status": "error"}
                time.sleep(3)
    return {"id": row_id, "predict": old_predict, "status": "error"}


def process_batch(client, batch_df):
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                refine_entity, client,
                int(row["_id"]), str(row["review"]), str(row["predict"])
            ): int(row["_id"])
            for _, row in batch_df.iterrows()
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                row_id = futures[future]
                log.error(f"Row {row_id} 未捕获异常: {e}")
                results.append({"id": row_id, "predict": "", "status": "error"})
    return results


def main():
    log.info("=" * 60)
    log.info("书籍类R1精化脚本启动")
    log.info("=" * 60)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        log.error("❌ 未检测到 DEEPSEEK_API_KEY！")
        return

    # 读取文件
    df = None
    for enc in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            _df = pd.read_csv(INPUT_FILE, encoding=enc)
            if "predict" in _df.columns and "cat" in _df.columns:
                df = _df
                log.info(f"读取成功，编码：{enc}，总行数：{len(df)}")
                break
        except UnicodeDecodeError:
            continue
    if df is None:
        log.error("❌ 无法读取文件！")
        return

    # 只取书籍行，保留原始索引
    df["_id"] = df.index
    books_df = df[df["cat"] == "书籍"].copy()
    log.info(f"书籍行数：{len(books_df)}，其余品类：{len(df) - len(books_df)} 条（原样保留）")

    # 加载进度
    done = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            done = json.load(f)
        log.info(f"已完成：{len(done)} 条，继续上次进度...")

    todo = books_df[~books_df["_id"].astype(str).isin(done.keys())].copy()
    log.info(f"待处理：{len(todo)} 条")

    if not todo.empty:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        total_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end   = min(start + BATCH_SIZE, len(todo))
            batch = todo.iloc[start:end]

            log.info(f"批次 {batch_idx+1}/{total_batches}（行 {start}~{end-1}）")
            results = process_batch(client, batch)

            for r in results:
                done[str(r["id"])] = {"predict": r["predict"], "status": r["status"]}

            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(done, f, ensure_ascii=False)

            ok       = sum(1 for r in results if r["status"] == "ok")
            uncertain = sum(1 for r in results if r["status"] == "uncertain")
            log.info(f"  ✅ 确定 {ok}  ⚠️ 不确定 {uncertain}  📊 累计 {len(done)} 条")

            if batch_idx < total_batches - 1:
                time.sleep(0.5)

    # ── 把R1结果写回df，只改书籍行的predict ──
    log.info("合并结果...")
    for row_id_str, info in done.items():
        row_id = int(row_id_str)
        df.loc[df["_id"] == row_id, "predict"] = info["predict"]

    # 输出（覆盖原文件）
    df.drop(columns=["_id"]).to_csv(INPUT_FILE, index=False, encoding="utf-8-sig")
    log.info(f"\n🎉 完成！已覆盖保存至：{INPUT_FILE}")

    # 统计
    books_result = df[df["cat"] == "书籍"]["predict"].astype(str)
    uncertain_count = books_result.str.contains("无法确定", na=False).sum()
    fail_count = books_result.str.contains("抽取失败", na=False).sum()
    log.info(f"书籍总计：{len(books_df)} 条")
    log.info(f"无法确定：{uncertain_count} 条")
    log.info(f"抽取失败：{fail_count} 条")
    log.info(f"有效结果：{len(books_df) - uncertain_count - fail_count} 条")
    log.info(f"进度文件保留在：{PROGRESS_FILE}，确认无误后可手动删除")


if __name__ == "__main__":
    main()
