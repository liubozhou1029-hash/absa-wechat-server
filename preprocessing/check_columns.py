"""
列名检查工具 - 运行前先执行这个，确认列名配置正确
"""
import pandas as pd
import sys

FILE = "online_shopping_10_cats.csv"

try:
    df = pd.read_csv(FILE, encoding="utf-8", nrows=3)
except UnicodeDecodeError:
    df = pd.read_csv(FILE, encoding="gbk", nrows=3)

print("=" * 55)
print(f"文件：{FILE}")
print(f"列名：{list(df.columns)}")
print(f"行数：约 {sum(1 for _ in open(FILE, encoding='utf-8', errors='ignore'))} 行（含表头）")
print()
print("前3行预览：")
print(df.to_string())
print("=" * 55)
print()
print("👉 请对照上面的列名，修改 product_entity_extractor.py 顶部：")
print("   COL_CATEGORY = '品类列的列名'")
print("   COL_REVIEW   = '评论文本列的列名'")
