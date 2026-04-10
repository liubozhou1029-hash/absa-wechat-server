"""
商品实体抽取器 - DeepSeek API 版本
支持分类：书籍、平板、手机、水果、洗发水、热水器、蒙牛、衣服、计算机、酒店
特性：断点续传、并发处理、按品类定制Prompt
"""

import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from openai import OpenAI   # DeepSeek 兼容 OpenAI SDK

# ─── 配置区（按需修改）────────────────────────────────────────────────────────
INPUT_FILE    = "online_shopping_10_cats.csv"  # 原始数据文件
OUTPUT_FILE   = "reviews_labeled.csv"          # 输出文件
PROGRESS_FILE = "progress.json"                # 断点续传进度文件

# ⚠️  列名：请确认和你CSV实际列名一致（运行前用 python check_columns.py 验证）
COL_CATEGORY  = "cat"       # 品类列
COL_REVIEW    = "review"    # 评论列
COL_RESULT    = "predict"   # 新增结果列（追加在原文件末尾）

MAX_WORKERS = 80      # 并发线程数（DeepSeek免费额度建议3，付费可调到8）
BATCH_SIZE  = 100    # 每批处理条数（每批完成后保存一次进度）
MODEL       = "deepseek-chat"   # DeepSeek-V3，性价比最高
MAX_TOKENS  = 30     # 商品名很短，30个token绰绰有余
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("extractor.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ─── 10个品类的定制 Prompt ────────────────────────────────────────────────────
CATEGORY_PROMPTS = {
    "书籍": (
        "你是图书信息抽取专家。从书评中提取【书名】。\n"
        "规则：①有书名直接返回书名 ②只有作者则返回'XX的作品' ③能推断则返回'XX（推断）' ④无法判断返回'未知书籍'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "平板": (
        "你是数码产品信息抽取专家。从平板评论中提取【品牌+型号】。\n"
        "规则：①有品牌+型号直接返回如'华为MatePad Pro' ②只有品牌返回'XX平板' ③无法判断返回'未知平板'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "手机": (
        "你是数码产品信息抽取专家。从手机评论中提取【品牌+型号】。\n"
        "规则：①有品牌+型号直接返回如'iPhone 15 Pro'、'小米14' ②只有品牌返回'XX手机' ③无法判断返回'未知手机'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "水果": (
        "你是农产品信息抽取专家。从水果评论中提取【品种+产地】。\n"
        "规则：①有品种+产地返回如'烟台富士苹果' ②只有品种返回品种名如'阳光玫瑰葡萄' ③无法判断返回'未知水果'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "洗发水": (
        "你是快消品信息抽取专家。从洗发水评论中提取【品牌+系列】。\n"
        "规则：①有品牌+系列返回如'海飞丝去屑洗发水'、'潘婷修护' ②只有品牌返回'XX洗发水' ③无法判断返回'未知洗发水'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "热水器": (
        "你是家电信息抽取专家。从热水器评论中提取【品牌+类型+关键型号】。\n"
        "规则：①尽量返回'品牌+类型'如'美的燃气热水器'、'史密斯电热水器16升' ②只有品牌返回'XX热水器' ③无法判断返回'未知热水器'\n"
        "只返回结果本身，不加引号不解释，不超过25字。\n\n评论：{review}"
    ),
    "蒙牛": (
        "你是乳品信息抽取专家。从蒙牛产品评论中提取【具体产品系列名】。\n"
        "规则：①尽量返回具体产品名如'蒙牛纯甄酸奶'、'蒙牛特仑苏' ②不确定系列返回'蒙牛乳品' ③完全无法判断返回'蒙牛未知产品'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "衣服": (
        "你是服装信息抽取专家。从衣服评论中提取【品牌+品类】。\n"
        "规则：①有品牌+品类返回如'优衣库羽绒服'、'波司登羽绒服' ②只有品类返回品类名如'羽绒服'、'T恤' ③无法判断返回'未知服装'\n"
        "只返回结果本身，不加引号不解释，不超过20字。\n\n评论：{review}"
    ),
    "计算机": (
        "你是数码产品信息抽取专家。从电脑评论中提取【品牌+型号/系列】。\n"
        "规则：①有品牌+型号返回如'联想ThinkPad X1'、'MacBook Pro M3' ②只有品牌返回'XX电脑' ③无法判断返回'未知电脑'\n"
        "只返回结果本身，不加引号不解释，不超过25字。\n\n评论：{review}"
    ),
    "酒店": (
        "你是酒店信息抽取专家。从酒店评论中提取【酒店名称或品牌+城市】。\n"
        "规则：①有具体酒店名返回全名如'北京国贸大酒店' ②只有品牌返回'XX酒店' ③只有城市返回'XX某酒店' ④无法判断返回'未知酒店'\n"
        "只返回结果本身，不加引号不解释，不超过25字。\n\n评论：{review}"
    ),
}

CATEGORY_MAP = {
    "书": "书籍", "图书": "书籍", "小说": "书籍", "教材": "书籍",
    "平板电脑": "平板", "pad": "平板", "ipad": "平板",
    "智能手机": "手机",
    "生鲜": "水果",
    "洗发液": "洗发水", "洗发露": "洗发水",
    "电热水器": "热水器", "燃气热水器": "热水器",
    "牛奶": "蒙牛",
    "服装": "衣服",
    "电脑": "计算机", "笔记本": "计算机",
    "宾馆": "酒店", "旅馆": "酒店",
}


def get_prompt(category: str, review: str) -> str:
    cat = str(category).strip()
    if cat in CATEGORY_PROMPTS:
        template = CATEGORY_PROMPTS[cat]
    else:
        matched = next((v for k, v in CATEGORY_MAP.items() if k in cat), None)
        template = CATEGORY_PROMPTS.get(matched, CATEGORY_PROMPTS["书籍"])
    return template.format(review=review[:400])


def extract_entity(client: OpenAI, row_id: int, category: str, review: str) -> dict:
    prompt = get_prompt(category, review)

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
            return {"id": row_id, "predict": result, "status": "ok"}

        except Exception as e:
            err_msg = str(e)
            if "rate" in err_msg.lower() or "429" in err_msg:
                wait = 2 ** attempt * 5
                log.warning(f"Row {row_id} 限流，{wait}秒后重试...")
                time.sleep(wait)
            else:
                log.error(f"Row {row_id} 错误(attempt {attempt+1}): {err_msg[:80]}")
                if attempt == 2:
                    return {"id": row_id, "predict": "抽取失败", "status": "error"}
                time.sleep(2)

    return {"id": row_id, "predict": "抽取失败", "status": "error"}


def load_progress() -> set:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        log.info(f"检测到进度文件，已处理 {len(data['done'])} 条，继续上次进度...")
        return set(data["done"])
    return set()


def save_progress(done_ids: set):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"done": list(done_ids)}, f)


def process_batch(client, batch_df) -> list:
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                extract_entity, client,
                int(row["_id"]), str(row[COL_CATEGORY]), str(row[COL_REVIEW])
            ): int(row["_id"])
            for _, row in batch_df.iterrows()
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                row_id = futures[future]
                log.error(f"Row {row_id} 未捕获异常: {e}")
                results.append({"id": row_id, "predict": "处理异常", "status": "error"})
    return results


def main():
    log.info("=" * 60)
    log.info("商品实体抽取器（DeepSeek版）启动")
    log.info("=" * 60)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    # 读取数据
    if not os.path.exists(INPUT_FILE):
        log.error(f"❌ 找不到数据文件：{INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE, encoding="gb18030")
    log.info(f"共 {len(df)} 条评论\n品类分布：\n{df[COL_CATEGORY].value_counts().to_string()}")

    # 检查列名
    for col in [COL_CATEGORY, COL_REVIEW]:
        if col not in df.columns:
            log.error(f"❌ 列名 '{col}' 不存在！实际列名：{list(df.columns)}")
            log.error("请修改脚本顶部 COL_CATEGORY / COL_REVIEW 的值")
            return

    # ── 关键修复：优先从已有输出文件读取结果，避免重启时覆盖已有数据 ──
    if os.path.exists(OUTPUT_FILE):
        try:
            df_existing = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
            if COL_RESULT in df_existing.columns and len(df_existing) == len(df):
                df[COL_RESULT] = df_existing[COL_RESULT].values
                filled = df[COL_RESULT].notna() & (df[COL_RESULT] != "")
                log.info(f"从已有输出文件恢复 {filled.sum()} 条已有结果，不会被覆盖")
            else:
                log.warning("输出文件行数与原始文件不符，从空白开始")
                df[COL_RESULT] = ""
        except Exception as e:
            log.warning(f"读取已有输出文件失败，从空白开始：{e}")
            df[COL_RESULT] = ""
    else:
        df[COL_RESULT] = ""
    # ────────────────────────────────────────────────────────────────────

    df["_id"] = df.index

    # 断点续传
    done_ids = load_progress()
    todo_df = df[~df["_id"].isin(done_ids)].copy()
    log.info(f"待处理: {len(todo_df)} 条 / 已完成: {len(done_ids)} 条")

    if todo_df.empty:
        log.info("✅ 所有数据已处理完成！")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        total_batches = (len(todo_df) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end   = min(start + BATCH_SIZE, len(todo_df))
            batch = todo_df.iloc[start:end]

            log.info(f"批次 {batch_idx + 1}/{total_batches}（行 {start}~{end-1}）")
            batch_results = process_batch(client, batch)

            for r in batch_results:
                df.loc[df["_id"] == r["id"], COL_RESULT] = r["predict"]
                done_ids.add(r["id"])

            save_progress(done_ids)
            df.drop(columns=["_id"]).to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

            ok  = sum(1 for r in batch_results if r["status"] == "ok")
            err = len(batch_results) - ok
            log.info(f"  ✅ {ok} 成功  ❌ {err} 失败")

            if batch_idx < total_batches - 1:
                time.sleep(0.3)

    df.drop(columns=["_id"], errors="ignore").to_csv(
        OUTPUT_FILE, index=False, encoding="utf-8-sig"
    )
    log.info(f"\n🎉 处理完成！结果已保存至：{OUTPUT_FILE}")

    final = pd.read_csv(OUTPUT_FILE)
    fail  = final[COL_RESULT].isin(["抽取失败", "处理异常", ""]).sum()
    log.info(f"总计 {len(final)} 条，成功 {len(final)-fail} 条，失败 {fail} 条（{fail/len(final)*100:.1f}%）")

    if os.path.exists(PROGRESS_FILE) and fail == 0:
        os.remove(PROGRESS_FILE)
        log.info("进度文件已清除")


if __name__ == "__main__":
    main()
