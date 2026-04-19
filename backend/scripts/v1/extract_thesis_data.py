"""
extract_thesis_data.py
======================
从 reviews_final.csv 提取论文图2-3、图2-7、图2-8 所需数据。
直接运行即可，无需修改 main.py。

使用方式：
    python extract_thesis_data.py

输出文件（与脚本同目录）：
    fig2_3_filter_stats.csv      → 图2-3：过滤前后评论数量对比
    fig2_7_topic_distribution.csv → 图2-7：BERTopic 主题分布（若安装了 bertopic）
    fig2_8_rank_compare.csv      → 图2-8：V1 vs V2 推荐排名对比（若有排名结果文件）
"""

import sys
import re
import html
import pandas as pd
from collections import defaultdict
from pathlib import Path

# ==========================
# 配置：修改这两个路径即可
# ==========================
REVIEWS_CSV = r"F:\Pythoncode\goodsrecommend\backend\data\raw\reviews_final.csv"

# 若已生成 V1/V2 推荐排名文件，填写路径；否则留空字符串跳过图2-8
SKU_RANK_V1_CSV = r""   # 例如 r"F:\...\sku_recommend_index.csv"
SKU_RANK_V2_CSV = r""   # 例如 r"F:\...\sku_recommend_index_v2.csv"

# 输出目录（默认与脚本同目录）
OUT_DIR = Path(__file__).parent


# ==========================
# 工具函数（与 main.py 保持一致）
# ==========================
INVALID_PATTERNS = ["此用户未填写评价内容", "NO_MESSAGE"]

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b(nbsp|hellip|bull)\b", " ", text, flags=re.I)
    for p in INVALID_PATTERNS:
        text = text.replace(p, " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


GENERIC_SHORT_PHRASES = [
    "很好", "不错", "可以", "满意", "一般", "还行", "还可以", "挺好",
    "好评", "五星", "支持", "喜欢", "值得", "推荐",
    "物流快", "发货快", "包装好", "质量好", "正品",
]

def is_minimal_review(text: str, max_len: int = 8) -> bool:
    if not isinstance(text, str):
        return True
    t = text.strip()
    if not t:
        return True
    if len(t) <= 2:
        return True
    if len(t) <= max_len:
        t_norm = re.sub(r"[^\u4e00-\u9fff0-9a-zA-Z]+", "", t)
        if len(t_norm) <= 2:
            return True
        tl = t.lower()
        for p in GENERIC_SHORT_PHRASES:
            if p.lower() in tl:
                return True
    return False


def _normalize_for_dup(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^\u4e00-\u9fff0-9a-z]+", "", t)
    return t


SPAM_TEMPLATES = [
    "物流很快", "发货很快", "包装很好", "质量不错", "值得购买",
    "非常满意", "五星好评", "好评", "满意", "不错", "挺好",
]

def _template_score(text: str) -> int:
    tl = text.lower()
    return sum(1 for s in SPAM_TEMPLATES if s.lower() in tl)


def classify_review(text: str) -> str:
    """
    返回该条评论的过滤原因（或 'valid'）。
    优先级：minimal_review > dup_exact（此处按全局检测，近重复需按组）
    注意：近重复（dup_near）需在同品类内批量判断，单条无法判定。
    """
    if is_minimal_review(text, max_len=8):
        return "minimal_review"
    return "valid"


# ==========================
# 图2-3：过滤前后评论数量统计
# 按品类（cat）做垃圾识别，统计各类过滤数量
# ==========================
def compute_filter_stats(df: pd.DataFrame) -> dict:
    """
    df 需要有 'cat'（品类）和 'clean_review'（清洗后文本）列。
    返回全局统计字典。
    """
    total_raw = len(df)

    # ---- 1) 极简/低信息 ----
    df = df.copy()
    df["is_minimal"] = df["clean_review"].apply(lambda t: is_minimal_review(t, max_len=8))

    # ---- 2) 完全重复（按品类分组）----
    df["norm_text"] = df["clean_review"].apply(_normalize_for_dup)
    df["is_exact_dup"] = False

    for cat, group in df.groupby("cat"):
        idxs = group.index.tolist()
        norm_map = defaultdict(list)
        for i in idxs:
            key = df.at[i, "norm_text"]
            if key:
                norm_map[key].append(i)
        for _, dup_idxs in norm_map.items():
            if len(dup_idxs) >= 2:
                for j in dup_idxs[1:]:
                    df.at[j, "is_exact_dup"] = True

    # ---- 3) 近重复（TF-IDF，按品类，仅对未被标记者）----
    #    因数据量大，这里用轻量版：仅统计 is_exact_dup=False & is_minimal=False 的评论
    #    若品类评论数 >5000，改用 NearestNeighbors，否则用全矩阵
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.neighbors import NearestNeighbors

        df["is_near_dup"] = False
        NEAR_DUP_THRESHOLD = 0.90
        LARGE_GROUP = 1000

        print("  正在检测近重复评论（按品类）...")
        for cat, group in df.groupby("cat"):
            candidate_mask = (~df["is_exact_dup"]) & (~df["is_minimal"]) & (df["cat"] == cat)
            cand_idx = df[candidate_mask].index.tolist()
            if len(cand_idx) < 2:
                continue

            sub_texts = df.loc[cand_idx, "clean_review"].tolist()
            try:
                vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1, max_features=30000)
                X = vec.fit_transform(sub_texts)
            except Exception:
                continue

            if X.shape[0] <= LARGE_GROUP:
                sim = cosine_similarity(X)
                for a in range(sim.shape[0]):
                    for b in range(a + 1, sim.shape[0]):
                        if sim[a, b] >= NEAR_DUP_THRESHOLD:
                            global_b = cand_idx[b]
                            if not df.at[global_b, "is_near_dup"]:
                                df.at[global_b, "is_near_dup"] = True
            else:
                k = min(10, X.shape[0] - 1)
                nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine", algorithm="brute")
                nn.fit(X)
                distances, indices = nn.kneighbors(X)
                for a in range(X.shape[0]):
                    for pos in range(1, indices.shape[1]):
                        b = indices[a, pos]
                        sim_ab = 1 - distances[a, pos]
                        if sim_ab >= NEAR_DUP_THRESHOLD and b > a:
                            global_b = cand_idx[b]
                            if not df.at[global_b, "is_near_dup"]:
                                df.at[global_b, "is_near_dup"] = True

    except ImportError:
        print("  [跳过] sklearn 未安装，近重复检测跳过。")
        df["is_near_dup"] = False

    # ---- 汇总 ----
    n_exact_dup  = int(df["is_exact_dup"].sum())
    n_near_dup   = int((df["is_near_dup"] & ~df["is_exact_dup"]).sum())
    n_minimal    = int((df["is_minimal"] & ~df["is_exact_dup"] & ~df["is_near_dup"]).sum())
    n_filtered   = n_exact_dup + n_near_dup + n_minimal
    n_valid      = total_raw - n_filtered

    stats = {
        "原始评论总数": total_raw,
        "完全重复评论": n_exact_dup,
        "近重复评论":   n_near_dup,
        "低信息短评":   n_minimal,
        "过滤总数":     n_filtered,
        "过滤后有效评论": n_valid,
        "有效率":       round(n_valid / total_raw, 4),
    }
    return stats, df


# ==========================
# 图2-7：BERTopic 主题分布（可选）
# 若未安装 bertopic，输出空文件并提示
# ==========================
def compute_topic_distribution(df_valid: pd.DataFrame, sample_n: int = 5000):
    """
    对有效评论抽样做 BERTopic，输出各品类 Top5 主题关键词+占比。
    sample_n: 抽样量（避免耗时过长）。设为 None 则全量。
    """
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  [跳过] bertopic/sentence_transformers 未安装，图2-7 跳过。")
        return pd.DataFrame()

    records = []
    for cat, group in df_valid.groupby("cat"):
        texts = group["clean_review"].tolist()
        if sample_n and len(texts) > sample_n:
            import random
            random.seed(42)
            texts = random.sample(texts, sample_n)

        print(f"  BERTopic 训练 [{cat}]，共 {len(texts)} 条...")
        try:
            emb_model = SentenceTransformer("shibing624/text2vec-base-chinese")
            model = BERTopic(embedding_model=emb_model, language="chinese",
                             calculate_probabilities=False, verbose=False)
            topics, _ = model.fit_transform(texts)
            topic_series = pd.Series(topics)

            info = model.get_topic_info()
            total = len(topics)
            for _, row in info[info["Topic"] != -1].head(5).iterrows():
                tid = row["Topic"]
                cnt = (topic_series == tid).sum()
                kws_raw = model.get_topic(tid) or []
                kws = "、".join([w for w, _ in kws_raw[:6]])
                records.append({
                    "cat": cat,
                    "topic_id": tid,
                    "topic_keywords": kws,
                    "count": int(cnt),
                    "ratio": round(cnt / total, 4),
                })
        except Exception as e:
            print(f"  [{cat}] BERTopic 失败：{e}")
            continue

    return pd.DataFrame(records)


# ==========================
# 图2-8：V1 vs V2 推荐排名对比（需要排名文件）
# ==========================
def compute_rank_compare(v1_path: str, v2_path: str) -> pd.DataFrame:
    if not v1_path or not v2_path:
        print("  [跳过] 未提供 V1/V2 排名文件路径，图2-8 跳过。")
        return pd.DataFrame()

    v1 = pd.read_csv(v1_path)
    v2 = pd.read_csv(v2_path)

    v1 = v1.reset_index(drop=True)
    v2 = v2.reset_index(drop=True)
    v1["rank_v1"] = v1.index + 1
    v2["rank_v2"] = v2.index + 1

    cols_v1 = [c for c in ["sku_id", "generated_name", "recommend_index", "rank_v1"] if c in v1.columns]
    cols_v2 = [c for c in ["sku_id", "recommend_index_v2", "rank_v2"] if c in v2.columns]

    df = v1[cols_v1].merge(v2[cols_v2], on="sku_id", how="outer")
    df["rank_change"] = df["rank_v1"] - df["rank_v2"]

    # 排名上升最多 Top10
    top_rise = (df[df["rank_change"] > 0]
                .sort_values("rank_change", ascending=False)
                .head(10))
    # 排名下降最多 Top10
    top_drop = (df[df["rank_change"] < 0]
                .sort_values("rank_change", ascending=True)
                .head(10))

    result = pd.concat([top_rise, top_drop], ignore_index=True)
    result["方向"] = result["rank_change"].apply(lambda x: "上升" if x > 0 else "下降")
    return result


# ==========================
# 主流程
# ==========================
def main():
    print("=" * 50)
    print("读取数据：", REVIEWS_CSV)
    df_raw = pd.read_csv(REVIEWS_CSV, encoding="utf-8-sig")
    print(f"  原始行数：{len(df_raw)}，列：{df_raw.columns.tolist()}")

    # 适配列名（reviews_final.csv 用 'review' 列，main.py 用 'content'）
    text_col = "review" if "review" in df_raw.columns else "content"
    cat_col  = "cat"    if "cat"    in df_raw.columns else "label"

    df_raw["clean_review"] = df_raw[text_col].apply(clean_text)
    # 去掉清洗后长度 <=5 的（与 main.py 一致）
    df_raw = df_raw[df_raw["clean_review"].str.len() > 5].copy()
    print(f"  清洗后行数（去空/超短）：{len(df_raw)}")

    # ---- 图2-3 ----
    print("\n[图2-3] 计算过滤统计...")
    stats, df_labeled = compute_filter_stats(df_raw)

    print("\n  汇总：")
    for k, v in stats.items():
        print(f"    {k}: {v}")

    # 保存为表格
    stats_df = pd.DataFrame([stats])
    out_fig23 = OUT_DIR / "fig2_3_filter_stats.csv"
    stats_df.to_csv(out_fig23, index=False, encoding="utf-8-sig")
    print(f"\n  ✅ 已保存：{out_fig23}")

    # 同时保存品类维度的过滤明细
    cat_stats = []
    for cat, g in df_labeled.groupby(cat_col):
        n_raw = len(g)
        n_exact = int(g["is_exact_dup"].sum())
        n_near  = int((g["is_near_dup"] & ~g["is_exact_dup"]).sum())
        n_min   = int((g["is_minimal"] & ~g["is_exact_dup"] & ~g["is_near_dup"]).sum())
        n_valid = n_raw - n_exact - n_near - n_min
        cat_stats.append({
            "品类": cat,
            "原始评论数": n_raw,
            "完全重复": n_exact,
            "近重复": n_near,
            "低信息短评": n_min,
            "有效评论数": n_valid,
            "有效率": round(n_valid / n_raw, 4),
        })
    cat_df = pd.DataFrame(cat_stats)
    out_cat = OUT_DIR / "fig2_3_filter_stats_by_cat.csv"
    cat_df.to_csv(out_cat, index=False, encoding="utf-8-sig")
    print(f"  ✅ 品类明细已保存：{out_cat}")

    # ---- 图2-7 ----
    print("\n[图2-7] BERTopic 主题分布（可能耗时较长）...")
    df_valid = df_labeled[
        (~df_labeled["is_exact_dup"]) &
        (~df_labeled["is_near_dup"]) &
        (~df_labeled["is_minimal"])
    ].copy()
    topic_df = compute_topic_distribution(df_valid, sample_n=3000)
    if not topic_df.empty:
        out_fig27 = OUT_DIR / "fig2_7_topic_distribution.csv"
        topic_df.to_csv(out_fig27, index=False, encoding="utf-8-sig")
        print(f"  ✅ 已保存：{out_fig27}")
        print(topic_df.head(10).to_string())

    # ---- 图2-8 ----
    print("\n[图2-8] V1 vs V2 排名对比...")
    rank_df = compute_rank_compare(SKU_RANK_V1_CSV, SKU_RANK_V2_CSV)
    if not rank_df.empty:
        out_fig28 = OUT_DIR / "fig2_8_rank_compare.csv"
        rank_df.to_csv(out_fig28, index=False, encoding="utf-8-sig")
        print(f"  ✅ 已保存：{out_fig28}")
        print(rank_df.to_string())

    print("\n全部完成！")


if __name__ == "__main__":
    main()
