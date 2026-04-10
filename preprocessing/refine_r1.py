"""
二次精化脚本 - 使用 DeepSeek-R1 重新推断含"推断"字样的条目
逻辑：
  - 含"推断"字样 → R1重新推断，能确定保留，仍不确定剔除
  - 无"推断"字样 → 原样保留
输出：reviews_final.csv
"""

import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from openai import OpenAI

# ─── 配置区 ───────────────────────────────────────────────────────────────────
INPUT_FILE    = "reviews_filtered.csv"   # 上一步过滤后的文件
OUTPUT_FILE   = "reviews_final.csv"      # 最终输出文件
PROGRESS_FILE = "progress_r1.json"       # 独立进度文件，不与主脚本混用

MAX_WORKERS = 5       # R1较慢，并发不宜太高
BATCH_SIZE  = 50      # 每批保存一次
MODEL       = "deepseek-reasoner"        # DeepSeek-R1 的模型名
MAX_TOKENS  = 50

# 仍不确定时的标记词，命中这些词的行会被剔除
UNCERTAIN_KEYWORDS = ["无法", "不确定", "未知", "无从", "看不出", "无法判断", "不清楚"]
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("refine_r1.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

PROMPT_TEMPLATE = (
    "你是资深图书编辑，擅长从书评中识别书名。\n"
    "请从以下书评中推断被评论的【书名】。\n\n"
    "规则：\n"
    "① 若能从评论内容、作者名、书中观点、人名等线索推断出书名，直接返回书名\n"
    "② 若评论提到了作者，返回'作者名+的作品'\n"
    "③ 若完全无法判断，只返回'无法确定'四个字，不要其他内容\n\n"
    "重要：只返回书名本身或'无法确定'，不加引号，不解释，不超过25字。\n\n"
    "书评：{review}"
)


def is_uncertain(result: str) -> bool:
    """判断R1的返回结果是否仍然不确定"""
    for kw in UNCERTAIN_KEYWORDS:
        if kw in result:
            return True
    return False


def refine_entity(client: OpenAI, row_id: int, review: str, old_predict: str) -> dict:
    """用R1重新推断单条书评的书名"""
    prompt = PROMPT_TEMPLATE.format(review=review[:500])

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.choices[0].message.content.strip()
            result = result.strip("「」『』【】《》\"'")

            if is_uncertain(result):
                return {"id": row_id, "predict": result, "status": "drop"}
            else:
                return {"id": row_id, "predict": result, "status": "ok"}

        except Exception as e:
            err_msg = str(e)
            if "rate" in err_msg.lower() or "429" in err_msg:
                wait = 2 ** attempt * 8
                log.warning(f"Row {row_id} 限流，{wait}秒后重试...")
                time.sleep(wait)
            else:
                log.error(f"Row {row_id} 错误(attempt {attempt+1}): {err_msg[:80]}")
                if attempt == 2:
                    return {"id": row_id, "predict": old_predict, "status": "keep"}
                time.sleep(3)

    return {"id": row_id, "predict": old_predict, "status": "keep"}


def load_progress() -> dict:
    """加载进度：返回 {row_id: {"predict": ..., "status": ...}}"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"检测到进度文件，已处理 {len(data)} 条，继续上次进度...")
        return data
    return {}


def save_progress(done: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False)


def process_batch(client, batch_df, done) -> list:
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
                results.append({"id": row_id, "predict": "", "status": "keep"})
    return results


def main():
    log.info("=" * 60)
    log.info("二次精化脚本（DeepSeek-R1）启动")
    log.info("=" * 60)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        log.error("❌ 未检测到 DEEPSEEK_API_KEY 环境变量！")
        return

    # 读取数据
    try:
        df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(INPUT_FILE, encoding="gb18030")

    log.info(f"读取数据：{len(df)} 条")

    # 分离：需要重跑 vs 直接保留
    mask_infer = df["predict"].str.contains("推断", na=False)
    df_infer   = df[mask_infer].copy().reset_index(drop=False)   # 含"推断"→重跑
    df_keep    = df[~mask_infer].copy()                           # 无"推断"→保留

    df_infer["_id"] = df_infer["index"]   # 保留原始行号用于进度追踪

    log.info(f"需要R1重跑：{len(df_infer)} 条（含'推断'）")
    log.info(f"直接保留： {len(df_keep)} 条（无'推断'）")

    # 加载进度
    done = load_progress()  # {str(row_id): {"predict": ..., "status": ...}}
    todo_df = df_infer[~df_infer["_id"].astype(str).isin(done.keys())].copy()
    log.info(f"待处理：{len(todo_df)} 条 / 已完成：{len(done)} 条")

    if not todo_df.empty:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        total_batches = (len(todo_df) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end   = min(start + BATCH_SIZE, len(todo_df))
            batch = todo_df.iloc[start:end]

            log.info(f"批次 {batch_idx+1}/{total_batches}（行 {start}~{end-1}）")
            batch_results = process_batch(client, batch, done)

            for r in batch_results:
                done[str(r["id"])] = {"predict": r["predict"], "status": r["status"]}

            save_progress(done)

            ok   = sum(1 for r in batch_results if r["status"] == "ok")
            drop = sum(1 for r in batch_results if r["status"] == "drop")
            keep = sum(1 for r in batch_results if r["status"] == "keep")
            log.info(f"  ✅ 确定 {ok}  ❌ 剔除 {drop}  ⏭️ 保留原值 {keep}")

            if batch_idx < total_batches - 1:
                time.sleep(0.5)

    # ── 合并结果 ──────────────────────────────────────────────────
    log.info("合并结果...")

    # 把R1结果写回df_infer
    drop_ids = set()
    for row_id_str, info in done.items():
        row_id = int(row_id_str)
        mask = df_infer["_id"] == row_id
        if info["status"] == "drop":
            drop_ids.add(row_id)
        else:
            df_infer.loc[mask, "predict"] = info["predict"]

    # 剔除drop行
    df_infer_final = df_infer[~df_infer["_id"].isin(drop_ids)].drop(
        columns=["_id", "index"], errors="ignore"
    )

    # 合并保留行和精化后的行
    df_final = pd.concat([df_keep, df_infer_final], ignore_index=True)

    # 输出
    df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    # ── 统计报告 ──────────────────────────────────────────────────
    log.info(f"\n🎉 精化完成！结果已保存至：{OUTPUT_FILE}")
    log.info(f"原始行数：    {len(df)}")
    log.info(f"R1重跑行数：  {len(df_infer)}")
    log.info(f"R1剔除行数：  {len(drop_ids)}")
    log.info(f"最终保留行数：{len(df_final)}")

    print("\n各品类最终条数：")
    print(df_final.groupby("cat").size().to_string())

    if os.path.exists(PROGRESS_FILE) and len(drop_ids) + len(df_infer_final) == len(df_infer):
        os.remove(PROGRESS_FILE)
        log.info("进度文件已清除")


if __name__ == "__main__":
    main()
