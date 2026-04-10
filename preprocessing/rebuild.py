# 把rebuild.py内容改成这个
import pandas as pd, json

df = pd.read_csv("reviews_labeled.csv", encoding="utf-8-sig")
done = df[df["predict"].notna() & (df["predict"] != "")].index.tolist()
print(f"已有结果：{len(done)} 条")
print(f"需要补跑：{62774 - len(done)} 条")
with open("progress.json", "w") as f:
    json.dump({"done": done}, f)
print("✅ 完成")