"""
成本预估 & 小样本测试脚本
在正式跑6万条之前，先用这个验证效果和预估费用
"""

import anthropic
import pandas as pd
import random

# ─── 使用和主脚本相同的配置 ───────────────────────────────────────────
from product_entity_extractor import (
    extract_entity, get_prompt_key, CATEGORY_PROMPTS,
    COL_CATEGORY, COL_REVIEW, COL_RESULT, MODEL
)

INPUT_FILE = "reviews.csv"
TEST_SAMPLE = 20  # 每个品类抽多少条测试

# claude-haiku-4-5 定价（美元/百万token，2025年参考价）
INPUT_PRICE_PER_M  = 0.80   # $0.80/M input tokens
OUTPUT_PRICE_PER_M = 4.00   # $4.00/M output tokens
AVG_INPUT_TOKENS   = 250    # 平均每条输入token（Prompt+评论）
AVG_OUTPUT_TOKENS  = 15     # 平均输出token（商品名很短）
# ─────────────────────────────────────────────────────────────────────


def estimate_cost(total_rows: int) -> None:
    """预估总成本"""
    total_input  = total_rows * AVG_INPUT_TOKENS
    total_output = total_rows * AVG_OUTPUT_TOKENS
    cost_input   = total_input  / 1_000_000 * INPUT_PRICE_PER_M
    cost_output  = total_output / 1_000_000 * OUTPUT_PRICE_PER_M
    total_cost   = cost_input + cost_output

    print("\n" + "=" * 50)
    print("💰 成本预估")
    print("=" * 50)
    print(f"总条数:       {total_rows:,}")
    print(f"预计输入Token: {total_input:,}")
    print(f"预计输出Token: {total_output:,}")
    print(f"输入费用:     ${cost_input:.2f}")
    print(f"输出费用:     ${cost_output:.2f}")
    print(f"预计总费用:   ${total_cost:.2f} USD")
    print(f"（约 ¥{total_cost * 7.2:.0f} 人民币）")

    # 时间估算（5线程，每条约0.5秒）
    seconds = total_rows / 5 * 0.5
    hours = seconds / 3600
    print(f"\n⏱️  预计运行时间: {hours:.1f} 小时（5线程）")
    print("=" * 50)


def run_test(client, df: pd.DataFrame) -> None:
    """按品类各抽样测试"""
    print("\n" + "=" * 50)
    print("🧪 小样本测试结果")
    print("=" * 50)

    categories = df[COL_CATEGORY].unique()
    results = []

    for cat in categories:
        cat_df = df[df[COL_CATEGORY] == cat]
        sample = cat_df.sample(min(TEST_SAMPLE, len(cat_df)), random_state=42)

        print(f"\n【{cat}】（共{len(cat_df)}条，抽取{len(sample)}条测试）")
        print(f"  Prompt模板: {get_prompt_key(cat)}")
        print("-" * 40)

        for i, (_, row) in enumerate(sample.head(5).iterrows()):  # 只打印前5条
            result = extract_entity(client, i, row[COL_CATEGORY], row[COL_REVIEW])
            review_preview = row[COL_REVIEW][:60].replace("\n", " ")
            print(f"  评论: {review_preview}...")
            print(f"  → 抽取结果: 【{result['product']}】")
            print()
            results.append({
                "品类": cat,
                "评论片段": review_preview,
                "抽取结果": result["product"]
            })

    # 保存测试结果
    test_df = pd.DataFrame(results)
    test_df.to_csv("test_results.csv", index=False, encoding="utf-8-sig")
    print(f"\n✅ 测试结果已保存至 test_results.csv")


def main():
    print("=" * 50)
    print("商品实体抽取器 - 预检工具")
    print("=" * 50)

    # 读取数据
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")
    print(f"\n数据概览：共 {len(df)} 条")
    print(df[COL_CATEGORY].value_counts().to_string())

    # 成本预估
    estimate_cost(len(df))

    # 询问是否继续测试
    choice = input("\n是否进行小样本测试？(y/n): ").strip().lower()
    if choice == "y":
        client = anthropic.Anthropic()
        run_test(client, df)
    else:
        print("跳过测试。确认无误后，运行 product_entity_extractor.py 开始正式处理。")


if __name__ == "__main__":
    main()
