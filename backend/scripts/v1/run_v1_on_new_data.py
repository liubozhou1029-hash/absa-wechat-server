"""
run_v1_on_new_data.py
=====================
用 main.py 的老模型逻辑（情感分 + 有效率 + 评论量）
跑新数据集 reviews_final.csv，生成 sku_recommend_index_v1_new.csv。
再与已有的 sku_recommend_index_v2.csv 对比，输出图2-8数据。

不依赖 BERTopic，运行速度快。
topic_top1_ratio（主题一致性）因无法在新数据上复现，用固定值 0.5 填充，
与 V2 对比时两边该分量相同，不影响排名差异的意义。

使用前修改下方「配置区」三个路径即可。
"""

# ==============================
# 配置区
# ==============================
REVIEWS_CSV   = r"F:\Pythoncode\goodsrecommend\backend\data\raw\reviews_final.csv"
SKU_V2_CSV    = r"F:\Pythoncode\goodsrecommend\backend\data\results\sku_recommend_index_v2.csv"
OUTPUT_DIR    = r"F:\Pythoncode\goodsrecommend\backend\data\compare"   # 留空则输出到脚本同目录

# V1 老模型权重（与 main.py DEFAULT_WEIGHTS 完全一致）
WEIGHTS = {
    "sentiment":   0.40,
    "rating":      0.15,   # 新数据无星级，用情感分代替
    "effective":   0.20,
    "consistency": 0.15,   # 无 BERTopic，固定 0.5
    "volume":      0.10,
}

MIN_SKU_REVIEWS = 3   # sku 最少评论数
NEAR_DUP_THRESHOLD = 0.90

# ==============================
# 导入
# ==============================
import re, math, html
from pathlib import Path
from collections import defaultdict

import pandas as pd

OUT = Path(OUTPUT_DIR) if OUTPUT_DIR else Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)

# ==============================
# 工具函数（与 main.py 一致）
# ==============================
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    for p in ["此用户未填写评价内容", "NO_MESSAGE"]:
        text = text.replace(p, " ")
    text = re.sub(r"\s+", " ", text).strip().lstrip("?？\ufeff").strip()
    return text

GENERIC_SHORT = [
    "很好","不错","可以","满意","一般","还行","还可以","挺好",
    "好评","五星","支持","喜欢","值得","推荐",
    "物流快","发货快","包装好","质量好","正品",
]
def is_minimal(text, max_len=8):
    if not isinstance(text, str): return True
    t = text.strip()
    if not t or len(t) <= 2: return True
    if len(t) <= max_len:
        t_norm = re.sub(r"[^\u4e00-\u9fff0-9a-zA-Z]+", "", t)
        if len(t_norm) <= 2: return True
        for p in GENERIC_SHORT:
            if p in t: return True
    return False

def norm_dup(text):
    return re.sub(r"[^\u4e00-\u9fff0-9a-z]+", "", text.lower()) if text else ""

SPAM_TEMPLATES = ["物流很快","发货很快","包装很好","质量不错","值得购买",
                  "非常满意","五星好评","好评","满意","不错","挺好"]

def detect_spam(texts):
    n = len(texts)
    is_spam = [False]*n
    reasons = [""]*n

    # 1) 完全重复
    norm_map = defaultdict(list)
    for i, t in enumerate(texts):
        k = norm_dup(t)
        if k: norm_map[k].append(i)
    for _, idxs in norm_map.items():
        for j in idxs[1:]:
            is_spam[j] = True
            reasons[j] = (reasons[j]+";dup_exact").strip(";")

    # 2) 近重复
    keep = [i for i in range(n) if not is_spam[i]]
    if len(keep) >= 2:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            from sklearn.neighbors import NearestNeighbors
            sub = [texts[i] for i in keep]
            vec = TfidfVectorizer(analyzer="char", ngram_range=(2,4), min_df=1, max_features=50000)
            X = vec.fit_transform(sub)
            if X.shape[0] <= 500:
                sim = cosine_similarity(X)
                for a in range(sim.shape[0]):
                    for b in range(a+1, sim.shape[0]):
                        if sim[a,b] >= NEAR_DUP_THRESHOLD:
                            gb = keep[b]
                            if not is_spam[gb]:
                                is_spam[gb] = True
                                reasons[gb] = (reasons[gb]+f";dup_near({sim[a,b]:.2f})").strip(";")
            else:
                k = min(10, X.shape[0]-1)
                nn = NearestNeighbors(n_neighbors=k+1, metric="cosine", algorithm="brute")
                nn.fit(X)
                dists, inds = nn.kneighbors(X)
                for a in range(X.shape[0]):
                    for pos in range(1, inds.shape[1]):
                        b = inds[a,pos]; s = 1-dists[a,pos]
                        if s >= NEAR_DUP_THRESHOLD and b > a:
                            gb = keep[b]
                            if not is_spam[gb]:
                                is_spam[gb] = True
                                reasons[gb] = (reasons[gb]+f";dup_nearNN({s:.2f})").strip(";")
        except ImportError:
            pass

    # 3) 极简
    for i, t in enumerate(texts):
        if is_minimal(t):
            if not is_spam[i]: is_spam[i] = True
            reasons[i] = (reasons[i]+";minimal_review").strip(";")

    return is_spam, reasons

# ==============================
# 主流程
# ==============================
def main():
    print("=" * 55)
    print("Step 1 | 读取 & 清洗")
    print("=" * 55)
    df = pd.read_csv(REVIEWS_CSV, encoding="utf-8-sig")
    df["sku_id"] = df["predict"].fillna("未知")          # 直接用商品名作 sku_id
    df["clean_review"] = df["review"].apply(clean_text)
    df = df[df["clean_review"].str.len() > 5].copy().reset_index(drop=True)

    # 过滤评论数不足的 sku
    cnt = df.groupby("sku_id").size()
    df = df[df["sku_id"].isin(cnt[cnt >= MIN_SKU_REVIEWS].index)].copy().reset_index(drop=True)
    print(f"  有效行数: {len(df)}  |  SKU 数: {df['sku_id'].nunique()}")

    print("\nStep 2 | 情感分（label 直接映射）")
    df["sentiment_score"] = pd.to_numeric(df["label"], errors="coerce").clip(0, 1)

    print("\nStep 3 | 垃圾评论识别")
    df["is_spam"] = 0
    df["spam_reason"] = ""
    for sku, g in df.groupby("sku_id", sort=False):
        idxs = g.index.tolist()
        flags, rsns = detect_spam(g["clean_review"].tolist())
        df.loc[idxs, "is_spam"]     = [1 if x else 0 for x in flags]
        df.loc[idxs, "spam_reason"] = rsns

    spam_n = int(df["is_spam"].sum())
    print(f"  垃圾评论: {spam_n}/{len(df)} ({spam_n/len(df):.2%})")
    exact_n = df["spam_reason"].str.contains("dup_exact",      na=False).sum()
    near_n  = df["spam_reason"].str.contains("dup_near",       na=False).sum()
    mini_n  = df["spam_reason"].str.contains("minimal_review", na=False).sum()
    print(f"    完全重复: {exact_n}  近重复: {near_n}  低信息短评: {mini_n}")

    df_eff = df[df["is_spam"] == 0].copy().reset_index(drop=True)
    print(f"  有效评论（建模用）: {len(df_eff)}")

    print("\nStep 4 | SKU 指标聚合")
    sku_total = df.groupby("sku_id").size().rename("total_comments").reset_index()
    sku_eff_n = df_eff.groupby("sku_id").size().rename("effective_comments").reset_index()
    m = sku_total.merge(sku_eff_n, on="sku_id", how="left")
    m["effective_comments"] = m["effective_comments"].fillna(0).astype(int)
    m["effective_ratio"] = m["effective_comments"] / m["total_comments"]

    sagg = (df_eff.groupby("sku_id")["sentiment_score"]
            .agg(["mean","std","count"]).reset_index()
            .rename(columns={"mean":"avg_sentiment","std":"std_sentiment","count":"n_sentiment"}))
    m = m.merge(sagg, on="sku_id", how="left")
    m["avg_sentiment"] = m["avg_sentiment"].fillna(0.5)

    # 正负比例
    tmp = df_eff.copy()
    tmp["is_pos"] = (tmp["sentiment_score"] >= 0.5).astype(int)
    pr = tmp.groupby("sku_id")[["is_pos"]].mean().reset_index()
    pr = pr.rename(columns={"is_pos":"pos_ratio"})
    pr["neg_ratio"] = 1 - pr["pos_ratio"]
    m = m.merge(pr, on="sku_id", how="left")

    # 无星级 → 用情感分代替（与 main.py 兜底一致）
    m["avg_rating_norm"] = m["avg_sentiment"]

    # 主题一致性：无 BERTopic，固定 0.5（V1/V2 对比时该项相同，不引入偏差）
    m["topic_top1_ratio"] = 0.5

    # 评论量因子
    max_n = max(1, int(m["effective_comments"].max()))
    m["volume_factor"] = m["effective_comments"].apply(
        lambda n: math.log1p(n) / math.log1p(max_n)
    )

    # 品类
    cat_map = df[["sku_id","cat"]].drop_duplicates("sku_id")
    m = m.merge(cat_map, on="sku_id", how="left")

    print("\nStep 5 | 推荐指数计算（V1 老模型权重）")
    m["recommend_index"] = (
        WEIGHTS["sentiment"]   * m["avg_sentiment"].clip(0,1)
        + WEIGHTS["rating"]    * m["avg_rating_norm"].clip(0,1)
        + WEIGHTS["effective"] * m["effective_ratio"].clip(0,1)
        + WEIGHTS["consistency"] * m["topic_top1_ratio"].clip(0,1)
        + WEIGHTS["volume"]    * m["volume_factor"].clip(0,1)
    ) * 100
    m["recommend_index"] = m["recommend_index"].round(2)
    m = m.sort_values("recommend_index", ascending=False).reset_index(drop=True)
    m["rank_v1"] = m.index + 1

    out_v1 = OUT / "sku_recommend_index_v1_new.csv"
    m.to_csv(out_v1, index=False, encoding="utf-8-sig")
    print(f"  ✅ 已保存: {out_v1}")
    print("\n  Top10：")
    print(m[["rank_v1","sku_id","cat","recommend_index",
             "avg_sentiment","effective_ratio","effective_comments"]].head(10).to_string())

    print("\nStep 6 | 图2-8：V1 vs V2 排名对比")
    v2 = pd.read_csv(SKU_V2_CSV, encoding="utf-8-sig")
    v2 = v2.reset_index(drop=True)
    v2["rank_v2"] = v2.index + 1   # V2 文件本身已按 recommend_score 排好序

    # join on sku_id（两边都用商品名）
    cmp = m[["sku_id","rank_v1","recommend_index"]].merge(
          v2[["sku_id","rank_v2","recommend_score"]], on="sku_id", how="inner")
    print(f"  能对上的 SKU 数: {len(cmp)}")

    cmp["rank_change"] = cmp["rank_v1"] - cmp["rank_v2"]

    top_rise = (cmp[cmp["rank_change"] > 0]
                .sort_values("rank_change", ascending=False).head(20))
    top_drop = (cmp[cmp["rank_change"] < 0]
                .sort_values("rank_change", ascending=True).head(20))
    result = pd.concat([top_rise, top_drop], ignore_index=True)
    result["方向"] = result["rank_change"].apply(lambda x: "上升" if x > 0 else "下降")

    out_fig28 = OUT / "fig2_8_rank_compare.csv"
    result.to_csv(out_fig28, index=False, encoding="utf-8-sig")
    print(f"  ✅ 已保存: {out_fig28}")

    print("\n  排名上升最多 Top10：")
    print(top_rise[["sku_id","rank_v1","rank_v2","rank_change"]].head(10).to_string())
    print("\n  排名下降最多 Top10：")
    print(top_drop[["sku_id","rank_v1","rank_v2","rank_change"]].head(10).to_string())

    # 同时保存全量对比表（画图用）
    full_cmp = m[["sku_id","cat","rank_v1","recommend_index"]].merge(
               v2[["sku_id","rank_v2","recommend_score"]], on="sku_id", how="inner")
    full_cmp["rank_change"] = full_cmp["rank_v1"] - full_cmp["rank_v2"]
    full_cmp.to_csv(OUT / "fig2_8_full_compare.csv", index=False, encoding="utf-8-sig")
    print(f"\n  ✅ 全量对比表已保存: fig2_8_full_compare.csv")

    print("\n" + "=" * 55)
    print("完成！输出文件：")
    print(f"  {out_v1}")
    print(f"  {out_fig28}")
    print(f"  {OUT / 'fig2_8_full_compare.csv'}")

if __name__ == "__main__":
    main()
