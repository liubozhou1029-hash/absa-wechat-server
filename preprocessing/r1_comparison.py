"""
R1精化前后对比导出脚本（无需progress_r1.json版本）
直接对比 reviews_filtered.csv 和 reviews_final.csv
输出五列：cat / label / review / predict_before / predict_after
只包含原本含"推断"字样的行
"""

import pandas as pd

FILTERED_FILE = "reviews_filtered.csv"
FINAL_FILE    = "reviews_final.csv"
OUTPUT_FILE   = "r1_comparison.csv"

def read_csv_auto(path):
    for enc in ["utf-8-sig", "gb18030"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法读取文件：{path}")

df_before = read_csv_auto(FILTERED_FILE)
df_after  = read_csv_auto(FINAL_FILE)

print(f"过滤后文件行数：{len(df_before)}")
print(f"R1精化后行数：  {len(df_after)}")

# 找出含"推断"的行索引
mask = df_before["predict"].str.contains("推断", na=False)
infer_idx = df_before[mask].index
print(f"含'推断'的行数：{len(infer_idx)}")

# 提取对比数据
df_out = df_before.loc[infer_idx, ["cat", "label", "review"]].copy()
df_out["predict_before"] = df_before.loc[infer_idx, "predict"].values
df_out["predict_after"]  = df_after.loc[infer_idx, "predict"].values

# 统计
changed   = (df_out["predict_before"] != df_out["predict_after"]).sum()
unchanged = (df_out["predict_before"] == df_out["predict_after"]).sum()
print(f"\nR1精化结果统计：")
print(f"  ✅ 有变化（成功精化）：{changed} 条")
print(f"  ➡️  无变化（保留原值）：{unchanged} 条")

df_out = df_out.reset_index(drop=True)
df_out.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"\n✅ 对比文件已保存至：{OUTPUT_FILE}（共 {len(df_out)} 行）")