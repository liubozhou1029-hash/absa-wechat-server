"""
最终过滤脚本
从reviews_final.csv中剔除无效predict行，输出情感分析数据集
"""

import pandas as pd

INPUT_FILE  = "reviews_final.csv"
OUTPUT_FILE = "dataset_final.csv"

# 读取
df = None
for enc in ["utf-8-sig", "utf-8", "gb18030"]:
    try:
        _df = pd.read_csv(INPUT_FILE, encoding=enc)
        if "predict" in _df.columns and "cat" in _df.columns:
            df = _df
            print(f"读取成功，编码：{enc}，总行数：{len(df)}")
            break
    except UnicodeDecodeError:
        continue

if df is None:
    print("❌ 无法读取文件！")
    exit()

print(f"\n过滤前各品类条数：")
print(df["cat"].value_counts().to_string())

# 过滤规则：剔除predict为无效值的行
invalid_keywords = ["无法确定", "抽取失败", "处理异常"]
mask_invalid = (
    df["predict"].isna() |
    (df["predict"] == "") |
    df["predict"].astype(str).str.contains("|".join(invalid_keywords), na=False)
)

df_clean = df[~mask_invalid].copy().reset_index(drop=True)
df_removed = df[mask_invalid].copy()

print(f"\n剔除行数：{len(df_removed)}")
print(f"剔除行中品类分布：")
print(df_removed["cat"].value_counts().to_string())

print(f"\n过滤后各品类条数：")
cat_stats = df_clean.groupby("cat").agg(
    总数=("label", "count"),
    正向=("label", lambda x: (x == 1).sum()),
    负向=("label", lambda x: (x == 0).sum()),
).reset_index()
cat_stats["正向率"] = (cat_stats["正向"] / cat_stats["总数"] * 100).round(1).astype(str) + "%"
print(cat_stats.to_string(index=False))
print(f"\n合计：{len(df_clean)} 条")

# 输出
df_clean.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"\n✅ 已保存至：{OUTPUT_FILE}")
