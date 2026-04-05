import pandas as pd

def main():
    print("1) 读取旧版和新版推荐结果...")
    v1 = pd.read_csv("sku_recommend_index.csv")
    v2 = pd.read_csv("sku_recommend_index_v2.csv")

    # 给两边加排名
    v1 = v1.copy()
    v2 = v2.copy()

    v1 = v1.reset_index(drop=True)
    v2 = v2.reset_index(drop=True)

    v1["rank_v1"] = v1.index + 1
    v2["rank_v2"] = v2.index + 1

    # 兼容旧版字段名：recommend_index
    if "recommend_index" not in v1.columns:
        raise ValueError("旧版文件中未找到 recommend_index 列")

    if "recommend_index_v2" not in v2.columns:
        raise ValueError("新版文件中未找到 recommend_index_v2 列")

    print("2) 合并排名与分数...")
    cols_v1 = ["sku_id", "generated_name", "recommend_index", "rank_v1"]
    cols_v2 = [
        "sku_id", "recommend_index_v2", "rank_v2",
        "aspect_sentiment_mean", "aspect_positive_ratio",
        "absa_confidence_mean"
    ]

    df = v1[cols_v1].merge(v2[cols_v2], on="sku_id", how="outer")

    # 名称缺失兜底
    df["generated_name"] = df["generated_name"].fillna("")

    # 计算排名变化：正数表示上升
    df["rank_change"] = df["rank_v1"] - df["rank_v2"]

    # 计算分数变化
    df["score_change"] = df["recommend_index_v2"] - df["recommend_index"]

    print("3) 导出完整对比表...")
    df.to_csv("compare_v1_v2_full.csv", index=False, encoding="utf-8-sig")

    print("4) 导出上升最多和下降最多样本...")
    up = df.sort_values("rank_change", ascending=False)
    down = df.sort_values("rank_change", ascending=True)

    up.head(20).to_csv("compare_v1_v2_top_rise.csv", index=False, encoding="utf-8-sig")
    down.head(20).to_csv("compare_v1_v2_top_drop.csv", index=False, encoding="utf-8-sig")

    print("\n=== 排名上升最多 Top10 ===")
    print(up[[
        "sku_id", "generated_name",
        "rank_v1", "rank_v2", "rank_change",
        "recommend_index", "recommend_index_v2", "score_change"
    ]].head(10))

    print("\n=== 排名下降最多 Top10 ===")
    print(down[[
        "sku_id", "generated_name",
        "rank_v1", "rank_v2", "rank_change",
        "recommend_index", "recommend_index_v2", "score_change"
    ]].head(10))

    print("\n=== 新版 Top10 ===")
    print(v2[[
        "sku_id", "generated_name", "recommend_index_v2",
        "aspect_sentiment_mean", "aspect_positive_ratio"
    ]].head(10))

    print("\n5) 已导出：")
    print("   compare_v1_v2_full.csv")
    print("   compare_v1_v2_top_rise.csv")
    print("   compare_v1_v2_top_drop.csv")

if __name__ == "__main__":
    main()