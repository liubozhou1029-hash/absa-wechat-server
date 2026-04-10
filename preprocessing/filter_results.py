"""
过滤脚本：提取predict列不含"未知"的行，生成新文件并统计各类条数
"""

import pandas as pd

INPUT_FILE  = "reviews_labeled.csv"
OUTPUT_FILE = "reviews_filtered.csv"

# 读取数据
df = pd.read_csv(INPUT_FILE, encoding="gb18030")
print(f"原始总行数：{len(df)}")

# ── 过滤：排除含"未知"的行、空值行、抽取失败行 ──
mask = (
    df["predict"].notna() &
    (df["predict"] != "") &
    (~df["predict"].str.contains("未知", na=False)) &
    (~df["predict"].str.contains("抽取失败", na=False)) &
    (~df["predict"].str.contains("处理异常", na=False))
)

df_filtered = df[mask].copy()
df_excluded = df[~mask].copy()

print(f"过滤后保留：{len(df_filtered)} 行")
print(f"排除行数：  {len(df_excluded)} 行")
print(f"保留比例：  {len(df_filtered)/len(df)*100:.1f}%")

# ── 各品类统计 ──
print("\n" + "=" * 45)
print("各品类条数统计（过滤后）")
print("=" * 45)
cat_stats = df_filtered.groupby("cat").size().reset_index(name="count")
cat_stats["占比"] = (cat_stats["count"] / len(df_filtered) * 100).round(1).astype(str) + "%"
print(cat_stats.to_string(index=False))
print("=" * 45)
print(f"合计：{len(df_filtered)} 条")

# ── 各品类情感分布 ──
print("\n各品类情感分布（过滤后）")
print("=" * 45)
sentiment_stats = df_filtered.groupby(["cat", "label"]).size().unstack(fill_value=0)
sentiment_stats.columns = ["负向(0)", "正向(1)"] if 0 in sentiment_stats.columns else sentiment_stats.columns
print(sentiment_stats.to_string())

# ── 排除的内容分析 ──
print("\n排除行中predict值分布（Top10）：")
print(df_excluded["predict"].value_counts().head(10).to_string())

# ── 输出文件 ──
df_filtered.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"\n✅ 已保存至：{OUTPUT_FILE}")
