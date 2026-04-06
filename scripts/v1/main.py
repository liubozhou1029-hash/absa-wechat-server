# =========================
# 0. import 区（永远放最上面）
# =========================
import pandas as pd
import re
import html
import math
from collections import Counter, defaultdict

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# 垃圾评论/近重复识别
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors


# =========================
# 1. 工具函数区（不直接执行）
# =========================
INVALID_PATTERNS = [
    "此用户未填写评价内容",
    "NO_MESSAGE",
]

def clean_text(text):
    """最小但有效的清洗：去HTML残留、去固定无意义句、空白归一"""
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


def topic_keywords(topic_id, topic_model, topn=6):
    """把 topic_id 转成关键词串，便于展示与写论文"""
    words = topic_model.get_topic(topic_id) or []
    return "、".join([w for w, _ in words[:topn]])


def explain_topic(topic_id, topic_model, n_words=10, n_docs=3):
    """
    解释 topic_id 指代什么：
    - 关键词（主题指纹）
    - 代表评论（Representative_Docs）
    """
    kws = topic_model.get_topic(topic_id) or []
    kws = [w for w, _ in kws[:n_words]]

    info = topic_model.get_topic_info()
    row = info[info["Topic"] == topic_id]
    reps = []
    if not row.empty and "Representative_Docs" in row.columns:
        reps = row["Representative_Docs"].iloc[0][:n_docs]

    return {
        "topic_id": topic_id,
        "keywords": kws,
        "representative_docs": reps
    }

# =========================
# 极简评价/低信息短评过滤（新增）
# =========================
GENERIC_SHORT_PHRASES = [
    "很好", "不错", "可以", "满意", "一般", "还行", "还可以", "挺好",
    "好评", "五星", "支持", "喜欢", "值得", "推荐",
    "物流快", "发货快", "包装好", "质量好", "正品",
]

def is_minimal_review(text: str, max_len: int = 8) -> bool:
    """
    判断是否为“极简/低信息”评价：
    - 字符长度很短（默认<=8）
    - 且主要由泛化词组成（如 很好/不错/满意/物流快 等）
    """
    if not isinstance(text, str):
        return True
    t = text.strip()
    if not t:
        return True

    # 很短：直接判定为极简（你也可以改成 <=6 更严格）
    if len(t) <= 2:
        return True

    if len(t) <= max_len:
        # 去掉标点和空白
        t_norm = re.sub(r"[^\u4e00-\u9fff0-9a-zA-Z]+", "", t)
        # 如果去掉符号后更短，也更像“嗯/好/行”
        if len(t_norm) <= 2:
            return True

        # 命中常见泛化短语，判为极简
        hits = 0
        tl = t.lower()
        for p in GENERIC_SHORT_PHRASES:
            if p.lower() in tl:
                hits += 1

        # 规则：短文本且命中 >=1 个泛化词 → 极简
        if hits >= 1:
            return True

    return False


# =========================
# 1.1 垃圾评论 / 水军识别模块
# =========================
SPAM_TEMPLATES = [
    "物流很快", "发货很快", "包装很好", "质量不错", "值得购买",
    "非常满意", "五星好评", "好评", "满意", "不错", "挺好",
]

def _normalize_for_dup(text: str) -> str:
    """用于重复检测的更严格归一：去标点/空白/大小写，保留中文英文数字"""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^\u4e00-\u9fff0-9a-z]+", "", t)
    return t

def _template_score(text: str) -> int:
    tl = text.lower()
    score = 0
    for s in SPAM_TEMPLATES:
        if s.lower() in tl:
            score += 1
    return score

def detect_spam_for_sku(
    sku_texts: list[str],
    tfidf_sim_threshold: float = 0.90,
    nn_large_group_threshold: int = 500,
    nn_neighbors: int = 10,
):
    """
    对同一 sku 内的评论做垃圾评论检测：
    1) 完全重复（归一后完全一致）
    2) 近重复（TF-IDF + 余弦相似度）
    3) 规则辅助：短文本 + 模板句命中
    4) 极简评价：低信息短评直接过滤（新增）
    """
    n = len(sku_texts)
    is_spam = [False] * n
    reasons = [""] * n

    # 1) 完全重复
    norm_map = defaultdict(list)
    for i, t in enumerate(sku_texts):
        key = _normalize_for_dup(t)
        if key:
            norm_map[key].append(i)

    for _, idxs in norm_map.items():
        if len(idxs) >= 2:
            for j in idxs[1:]:
                is_spam[j] = True
                reasons[j] = (reasons[j] + ";dup_exact").strip(";")

    # 2) 近重复（仅对未判垃圾者）
    keep_idx = [i for i in range(n) if not is_spam[i]]
    if len(keep_idx) >= 2:
        sub_texts = [sku_texts[i] for i in keep_idx]

        vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            min_df=1,
            max_features=50000
        )
        X = vectorizer.fit_transform(sub_texts)

        if X.shape[0] <= nn_large_group_threshold:
            sim = cosine_similarity(X)
            for a in range(sim.shape[0]):
                for b in range(a + 1, sim.shape[0]):
                    if sim[a, b] >= tfidf_sim_threshold:
                        global_b = keep_idx[b]
                        if not is_spam[global_b]:
                            is_spam[global_b] = True
                            reasons[global_b] = (reasons[global_b] + f";dup_near({sim[a,b]:.2f})").strip(";")
        else:
            k = min(nn_neighbors, X.shape[0] - 1)
            nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine", algorithm="brute")
            nn.fit(X)
            distances, indices = nn.kneighbors(X)
            for a in range(X.shape[0]):
                for pos in range(1, indices.shape[1]):
                    b = indices[a, pos]
                    sim_ab = 1 - distances[a, pos]
                    if sim_ab >= tfidf_sim_threshold and b > a:
                        global_b = keep_idx[b]
                        if not is_spam[global_b]:
                            is_spam[global_b] = True
                            reasons[global_b] = (reasons[global_b] + f";dup_nearNN({sim_ab:.2f})").strip(";")

    # 3) 规则辅助
    for i, t in enumerate(sku_texts):
        tl = t.strip()
        if not tl:
            continue
        tmpl = _template_score(tl)
        if len(tl) <= 12 and tmpl >= 2:
            if is_spam[i]:
                reasons[i] = (reasons[i] + ";template_short").strip(";")
            else:
                reasons[i] = (reasons[i] + ";susp_template_short").strip(";")

    # 4) 极简评价直接过滤（新增）—— 放在 return 前面！
    for i, t in enumerate(sku_texts):
        if is_minimal_review(t, max_len=8):
            if not is_spam[i]:
                is_spam[i] = True
            reasons[i] = (reasons[i] + ";minimal_review").strip(";")

    return is_spam, reasons


def add_spam_labels(df: pd.DataFrame, text_col="clean_content", sku_col="sku_id"):
    df = df.copy()
    df["is_spam"] = 0
    df["spam_reason"] = ""

    for sku, g in df.groupby(sku_col, sort=False):
        idxs = g.index.tolist()
        texts = g[text_col].tolist()
        flags, reasons = detect_spam_for_sku(texts)
        df.loc[idxs, "is_spam"] = [1 if x else 0 for x in flags]
        df.loc[idxs, "spam_reason"] = reasons

    return df


# =========================
# 1.2 情感特征模块（新增）
# =========================
def _try_build_sentiment_pipeline():
    """
    尝试使用 transformers 的中文情感模型。
    若环境没装 transformers 或模型下载失败，返回 None 并自动走降级方案。
    """
    try:
        from transformers import pipeline
        model_name = "uer/roberta-base-finetuned-jd-binary-chinese"
        clf = pipeline(
            "text-classification",
            model=model_name,
            tokenizer=model_name,
            return_all_scores=True,
            device=-1  # CPU
        )
        return clf
    except Exception as e:
        print("[情感模块] transformers 情感模型不可用，将自动降级使用 score(星级) 作为情感代理。原因：", repr(e))
        return None

def compute_sentiment_scores(df: pd.DataFrame, text_col="clean_content", score_col="score"):
    """
    输出 df['sentiment_score'] ∈ [0,1]，值越大越正向。
    优先：transformers 情感模型（带 truncation 防止 512 超限报错）
    降级：用星级 score 映射 (1~5 -> 0~1)
    """
    df = df.copy()
    clf = _try_build_sentiment_pipeline()

    # ---------- 降级方案：星级映射 ----------
    if clf is None:
        def map_score_to_sent(x):
            try:
                v = float(x)
                v = max(1.0, min(5.0, v))
                return (v - 1.0) / 4.0
            except Exception:
                return 0.5

        df["sentiment_score"] = df[score_col].apply(map_score_to_sent)
        df["sentiment_source"] = "rating_proxy"
        return df

    # ---------- transformers 推理（关键：truncation=True,max_length=512） ----------
    texts = df[text_col].fillna("").astype(str).tolist()

    # 可选：在送入模型前先做一次“字符级硬截断”，进一步提速&降低极端长文本风险
    # 一般中文 800~1200 字符就足以接近 512 tokens
    def hard_clip(s, max_chars=1200):
        s = s.strip()
        return s[:max_chars] if len(s) > max_chars else s

    texts = [hard_clip(t, 1200) for t in texts]

    batch_size = 32
    scores = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        # ✅ 关键修复：强制截断到 512
        outputs = clf(
            batch,
            truncation=True,
            padding=True,
            max_length=512
        )

        for out in outputs:
            pos = None

            # 优先识别 POSITIVE/NEGATIVE
            for item in out:
                lab = str(item.get("label", "")).lower()
                if "pos" in lab or "positive" in lab:
                    pos = float(item["score"])
                    break

            # 兼容 label_1
            if pos is None:
                for item in out:
                    lab = str(item.get("label", "")).lower()
                    if lab in ("label_1", "1"):
                        pos = float(item["score"])
                        break

            # 最后兜底
            if pos is None:
                pos = float(max(out, key=lambda z: z["score"])["score"])

            scores.append(pos)

    df["sentiment_score"] = scores
    df["sentiment_source"] = "transformers"
    return df

    # --- transformers 正式方案 ---
    texts = df[text_col].fillna("").astype(str).tolist()

    # 分批推理，避免一次性太多文本
    batch_size = 32
    scores = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        outputs = clf(batch)  # return_all_scores=True -> list[list[{label,score}]]

        for out in outputs:
            # 找出正向概率：不同模型 label 可能是 POSITIVE/NEGATIVE 或 label_0/label_1
            # 我们做更稳妥的适配：优先按包含 "pos" 的 label，其次取 score 最大的那个作为正向(不太理想但兜底)
            pos = None
            for item in out:
                lab = str(item.get("label", "")).lower()
                if "pos" in lab or "positive" in lab:
                    pos = float(item["score"])
                    break
            if pos is None:
                # 有些模型用 label_1 表示正类，这里再尝试
                for item in out:
                    lab = str(item.get("label", "")).lower()
                    if lab in ("label_1", "1"):
                        pos = float(item["score"])
                        break
            if pos is None:
                # 最后兜底：取最高分当作“更可信”，但不保证就是正向
                pos = float(max(out, key=lambda z: z["score"])["score"])
            scores.append(pos)

    df["sentiment_score"] = scores
    df["sentiment_source"] = "transformers"
    return df


# =========================
# 1.3 商品名（品牌+型号）推断模块（保留你的新增）
# =========================
BRANDS = [
    "小米", "红米", "华为", "荣耀", "vivo", "oppo", "OPPO",
    "三星", "魅族", "一加", "realme"
]

MODEL_PATTERN = re.compile(
    r"("
    r"(?:mate|p|x|k|r|a|note|mix)\s?-?\s?\d{1,3}"
    r"|"
    r"(?:荣耀|红米|小米)\s?\d{1,3}(?:[a-z]{0,2})?"
    r"|"
    r"\b[a-z]{1,6}\d{1,4}\b"
    r")",
    re.I
)

def infer_brand_model(texts):
    brand_counter = Counter()
    model_counter = Counter()

    for t in texts:
        tl = t.lower()
        for b in BRANDS:
            if b.lower() in tl:
                brand_counter[b] += 1

        for m in MODEL_PATTERN.findall(t):
            m = m.strip().replace(" ", "").lower()
            if m.isdigit():
                continue
            if m in {"32", "64", "128", "256", "512"}:
                continue
            if m in {"2018", "2019", "2020", "2021", "2022", "2023", "2024"}:
                continue
            OS_BLACKLIST_PREFIX = ("ios", "android", "miui", "emui", "oneui", "coloros", "flyme")
            if m.lower().startswith(OS_BLACKLIST_PREFIX):
                continue
            model_counter[m] += 1

    brand = brand_counter.most_common(1)
    model = model_counter.most_common(1)
    brand = brand[0][0] if brand else ""
    model = model[0][0] if model else ""
    return brand, model


# =========================
# 2. 数据读取与预处理区
# =========================
df = pd.read_csv("京东评论数据.csv")
df = df[["sku_id", "item_name", "content", "score"]]

df["clean_content"] = df["content"].apply(clean_text)
df = df[df["clean_content"].str.len() > 5].copy()
print("清洗后评论数：", len(df))

# 2.1 垃圾评论识别
df = add_spam_labels(df, text_col="clean_content", sku_col="sku_id")
spam_cnt = int(df["is_spam"].sum())
print(f"识别到疑似垃圾评论：{spam_cnt} / {len(df)}  ({spam_cnt/len(df):.2%})")

# 2.2 情感特征（对全量评论做也行；做完后再过滤，更利于“过滤前后对比”）
df = compute_sentiment_scores(df, text_col="clean_content", score_col="score")
print("情感特征生成完成。sentiment_source =", df["sentiment_source"].iloc[0])

# 2.3 过滤垃圾评论，进入建模
df_model = df[df["is_spam"] == 0].copy()
texts = df_model["clean_content"].tolist()
print("建模使用评论数（过滤后）：", len(texts))
print("示例：", texts[:3])

# =========================
# 3. 语义主题模型构建 + 训练（只能出现一次）
# =========================
embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese")

topic_model = BERTopic(
    embedding_model=embedding_model,
    language="chinese",
    calculate_probabilities=True,
    verbose=True
)

topics, probs = topic_model.fit_transform(texts)
df_model["topic_id"] = topics


# =========================
# 3.1 sku 级主题聚合（count + ratio）
# =========================
df_valid = df_model[df_model["topic_id"] != -1].copy()

sku_topic_counts = (
    df_valid.groupby(["sku_id", "topic_id"])
    .size()
    .reset_index(name="cnt")
)

sku_totals = (
    df_valid.groupby("sku_id")
    .size()
    .reset_index(name="total_valid")
)

sku_topic = sku_topic_counts.merge(sku_totals, on="sku_id", how="left")
sku_topic["ratio"] = sku_topic["cnt"] / sku_topic["total_valid"]

top3 = (
    sku_topic.sort_values(["sku_id", "ratio"], ascending=[True, False])
    .groupby("sku_id")
    .head(3)
    .reset_index(drop=True)
)

top3["topic_keywords"] = top3["topic_id"].apply(lambda x: topic_keywords(x, topic_model, topn=6))
sku_name = df_model[["sku_id", "item_name"]].drop_duplicates("sku_id")
top3 = top3.merge(sku_name, on="sku_id", how="left")

print("\n[sku_top3_topics + topic_keywords] 示例：")
print(top3.head(10))


# =========================
# 3.2 近似商品名（品牌+型号）生成
# =========================
sku_names = []
for sku, group in df_model.groupby("sku_id"):
    sku_texts = group["clean_content"].tolist()
    brand, model = infer_brand_model(sku_texts)

    sku_top = top3[top3["sku_id"] == sku]

    def compact_keywords(sku_top_df, max_topics=2, kw_per_topic=3):
        kws = []
        for _, row in sku_top_df.head(max_topics).iterrows():
            parts = row["topic_keywords"].split("、")[:kw_per_topic]
            parts = [p for p in parts if 1 <= len(p) <= 8]
            kws.extend(parts)
        seen = set()
        out = []
        for x in kws:
            if x and x not in seen:
                out.append(x)
                seen.add(x)
        return "、".join(out)

    kw_fallback = compact_keywords(sku_top, max_topics=2, kw_per_topic=3)

    if brand and model:
        if model.lower().startswith(brand.lower()):
            generated_name = f"{model} 手机"
        else:
            generated_name = f"{brand} {model} 手机"
    elif brand:
        generated_name = f"{brand} 手机（{kw_fallback}）"
    else:
        generated_name = f"手机（{kw_fallback}）"

    sku_names.append({
        "sku_id": sku,
        "generated_name": generated_name,
        "brand_guess": brand,
        "model_guess": model
    })

sku_name_df = pd.DataFrame(sku_names)
top3 = top3.merge(sku_name_df[["sku_id", "generated_name"]], on="sku_id", how="left")


# =========================
# 4. sku 级情感聚合 + 综合评价 / 推荐指数（新增）
# =========================
def safe_float(x, default=None):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def build_sku_metrics(df_all: pd.DataFrame, df_effective: pd.DataFrame, top3_df: pd.DataFrame):
    """
    df_all: 含 is_spam、sentiment_score 的全量评论（未过滤）
    df_effective: 过滤垃圾后的评论（用于主题、有效情感、等）
    top3_df: sku top3 topic ratio
    输出 sku_metrics：每个 sku 一行
    """
    # sku 维度计数
    sku_total = df_all.groupby("sku_id").size().rename("total_comments").reset_index()
    sku_effective = df_effective.groupby("sku_id").size().rename("effective_comments").reset_index()
    m = sku_total.merge(sku_effective, on="sku_id", how="left")
    m["effective_comments"] = m["effective_comments"].fillna(0).astype(int)
    m["effective_ratio"] = m["effective_comments"] / m["total_comments"]

    # sku 维度情感聚合（用有效评论）
    sagg = df_effective.groupby("sku_id")["sentiment_score"].agg(["mean", "std", "count"]).reset_index()
    sagg = sagg.rename(columns={"mean": "avg_sentiment", "std": "std_sentiment", "count": "n_sentiment"})
    m = m.merge(sagg, on="sku_id", how="left")
    m["avg_sentiment"] = m["avg_sentiment"].fillna(0.5)
    m["std_sentiment"] = m["std_sentiment"].fillna(0.0)

    # 正负比例（以 0.5 为阈值）
    tmp = df_effective.copy()
    tmp["is_pos"] = (tmp["sentiment_score"] >= 0.5).astype(int)
    tmp["is_neg"] = (tmp["sentiment_score"] < 0.5).astype(int)
    pr = tmp.groupby("sku_id")[["is_pos", "is_neg"]].mean().reset_index()
    pr = pr.rename(columns={"is_pos": "pos_ratio", "is_neg": "neg_ratio"})
    m = m.merge(pr, on="sku_id", how="left")
    m["pos_ratio"] = m["pos_ratio"].fillna(0.5)
    m["neg_ratio"] = m["neg_ratio"].fillna(0.5)

    # 星级（若存在）作为辅助（归一到 0~1）
    def normalize_rating(v):
        v = safe_float(v, default=None)
        if v is None:
            return None
        v = max(1.0, min(5.0, v))
        return (v - 1.0) / 4.0

    if "score" in df_effective.columns:
        r = df_effective.groupby("sku_id")["score"].apply(lambda x: pd.Series([normalize_rating(v) for v in x]).dropna().mean())
        r = r.reset_index().rename(columns={"score": "avg_rating_norm"})
        m = m.merge(r, on="sku_id", how="left")
        m["avg_rating_norm"] = m["avg_rating_norm"].fillna(m["avg_sentiment"])  # 没有评分就用情感兜底
    else:
        m["avg_rating_norm"] = m["avg_sentiment"]

    # 主题一致性：Top1 主题占比（越大越“评价集中”）
    top1 = (
        top3_df.sort_values(["sku_id", "ratio"], ascending=[True, False])
        .groupby("sku_id")
        .head(1)[["sku_id", "ratio"]]
        .rename(columns={"ratio": "topic_top1_ratio"})
    )
    m = m.merge(top1, on="sku_id", how="left")
    m["topic_top1_ratio"] = m["topic_top1_ratio"].fillna(0.0)

    # 评论量因子（归一到 0~1）：log(1+n)/log(1+max_n)
    max_n = max(1, int(m["effective_comments"].max()))
    m["volume_factor"] = m["effective_comments"].apply(lambda n: math.log1p(n) / math.log1p(max_n))

    # 生成名合并（便于展示）
    m = m.merge(sku_name_df[["sku_id", "generated_name", "brand_guess", "model_guess"]], on="sku_id", how="left")

    return m

sku_metrics = build_sku_metrics(df_all=df, df_effective=df_model, top3_df=top3)

# -------------------------
# 4.1 推荐指数（可调权重）
# -------------------------
DEFAULT_WEIGHTS = {
    # 口碑：情感 + 星级
    "sentiment": 0.40,
    "rating":    0.15,
    # 数据可靠性：有效评论比例（过滤水军后剩多少）
    "effective": 0.20,
    # 评论一致性：主题集中度（Top1 topic ratio）
    "consistency": 0.15,
    # 讨论热度：评论量因子
    "volume": 0.10,
}

def compute_recommend_index(m: pd.DataFrame, weights=None):
    """
    输出 recommend_index: 0~100
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    m = m.copy()

    # 基础分量均需在 0~1
    sentiment = m["avg_sentiment"].clip(0, 1)
    rating = m["avg_rating_norm"].clip(0, 1)
    effective = m["effective_ratio"].clip(0, 1)
    consistency = m["topic_top1_ratio"].clip(0, 1)
    volume = m["volume_factor"].clip(0, 1)

    score01 = (
        weights["sentiment"] * sentiment
        + weights["rating"] * rating
        + weights["effective"] * effective
        + weights["consistency"] * consistency
        + weights["volume"] * volume
    )

    m["recommend_index"] = (score01 * 100).round(2)

    # 同时给出分量，方便论文做消融/解释
    m["comp_sentiment"] = sentiment
    m["comp_rating"] = rating
    m["comp_effective"] = effective
    m["comp_consistency"] = consistency
    m["comp_volume"] = volume

    return m

sku_rank = compute_recommend_index(sku_metrics, weights=DEFAULT_WEIGHTS)
sku_rank = sku_rank.sort_values("recommend_index", ascending=False)

print("\n[sku 推荐指数 Top10]：")
print(sku_rank[["sku_id", "generated_name", "recommend_index", "avg_sentiment", "effective_ratio", "topic_top1_ratio", "effective_comments"]].head(10))


# =========================
# 5. 输出与辅助分析
# =========================
topic_info = topic_model.get_topic_info()
print("\n[topic_info] 前10条：")
print(topic_info.head(10))

for tid in topic_info["Topic"].head(5):
    print(f"\nTopic {tid}:")
    print(topic_model.get_topic(tid))

demo = explain_topic(topic_id=3, topic_model=topic_model, n_words=10, n_docs=2)
print("\n[解释 Topic 3 示例]：")
print(demo)

# 导出：评论级 + sku级
df.to_csv("comment_with_spam_and_sentiment.csv", index=False, encoding="utf-8-sig")
df_model.to_csv("comment_effective_with_topics_sentiment.csv", index=False, encoding="utf-8-sig")
top3.to_csv("sku_top3_topics.csv", index=False, encoding="utf-8-sig")
sku_name_df.to_csv("sku_generated_name.csv", index=False, encoding="utf-8-sig")

sku_metrics.to_csv("sku_metrics.csv", index=False, encoding="utf-8-sig")
sku_rank.to_csv("sku_recommend_index.csv", index=False, encoding="utf-8-sig")

print("\n已导出：")
print("1) comment_with_spam_and_sentiment.csv （全量评论：含 is_spam/spam_reason/sentiment）")
print("2) comment_effective_with_topics_sentiment.csv （过滤后：含 topic_id + sentiment）")
print("3) sku_top3_topics.csv")
print("4) sku_generated_name.csv")
print("5) sku_metrics.csv （sku 聚合指标：情感/有效率/一致性/评论量等）")
print("6) sku_recommend_index.csv （含 recommend_index 0~100，可直接排序推荐）")


# =========================
# 实验一：SKU 评论质量统计表
# =========================

# 原始评论数
sku_raw_cnt = (
    df.groupby("sku_id")
    .size()
    .reset_index(name="raw_comment_cnt")
)

# 有效评论数（过滤垃圾评论后）
sku_valid_cnt = (
    df_model.groupby("sku_id")
    .size()
    .reset_index(name="valid_comment_cnt")
)

# 合并
sku_quality = sku_raw_cnt.merge(sku_valid_cnt, on="sku_id", how="left")
sku_quality["valid_comment_cnt"] = sku_quality["valid_comment_cnt"].fillna(0).astype(int)

# 有效评论比例
sku_quality["valid_ratio"] = (
    sku_quality["valid_comment_cnt"] / sku_quality["raw_comment_cnt"]
).round(4)

# 合并商品名，方便论文展示
sku_quality = sku_quality.merge(
    sku_name_df[["sku_id", "generated_name"]],
    on="sku_id",
    how="left"
)

# 排序（按有效评论比例从低到高，便于观察异常）
sku_quality = sku_quality.sort_values("valid_ratio")

# 导出
sku_quality.to_csv("exp1_sku_quality_stats.csv", index=False, encoding="utf-8-sig")

print("\n[实验1] SKU 评论质量统计表示例：")
print(sku_quality.head(10))


# =========================
# 实验二（1）：整体过滤前 vs 过滤后对比（补全过滤前 topic -1 + delta）
# =========================

# 过滤前：清洗后、长度>5，但未过滤垃圾/极简的 df
overall_before = {
    "avg_sentiment": df["sentiment_score"].mean(),
}

# ✅ 用同一个 topic_model 对“过滤前文本”做 transform，得到 topic_id_before
texts_before = df["clean_content"].tolist()
topics_before, _ = topic_model.transform(texts_before)

topic_minus1_ratio_before = (pd.Series(topics_before) == -1).mean()
topic_minus1_ratio_after = (df_model["topic_id"] == -1).mean()

overall_after = {
    "avg_sentiment": df_model["sentiment_score"].mean(),
}

overall_compare = pd.DataFrame(
    [
        {
            "stage": "before_filter",
            "avg_sentiment": overall_before["avg_sentiment"],
            "topic_-1_ratio": topic_minus1_ratio_before
        },
        {
            "stage": "after_filter",
            "avg_sentiment": overall_after["avg_sentiment"],
            "topic_-1_ratio": topic_minus1_ratio_after
        },
    ]
)

# ✅ 加一行差值（after - before）
overall_delta = pd.DataFrame([{
    "stage": "delta(after-before)",
    "avg_sentiment": overall_compare.loc[1, "avg_sentiment"] - overall_compare.loc[0, "avg_sentiment"],
    "topic_-1_ratio": overall_compare.loc[1, "topic_-1_ratio"] - overall_compare.loc[0, "topic_-1_ratio"],
}])

overall_compare_full = pd.concat([overall_compare, overall_delta], ignore_index=True)

overall_compare_full.to_csv("exp2_overall_compare.csv", index=False, encoding="utf-8-sig")

print("\n[实验2-整体] 过滤前 vs 过滤后（含过滤前 topic_-1_ratio & delta）：")
print(overall_compare_full)


# =========================
# （关键补全）创建 df_before_topics（供 SKU 级 -1 统计使用）
# =========================
df_before_topics = df.copy()
df_before_topics["topic_id_before"] = topics_before


# =========================
# （可选）SKU 级 Topic -1 占比：过滤前 vs 过滤后
# =========================
sku_t1_before = (
    df_before_topics.groupby("sku_id")["topic_id_before"]
    .apply(lambda x: (x == -1).mean())
    .reset_index(name="topic_-1_ratio_before")
)

sku_t1_after = (
    df_model.groupby("sku_id")["topic_id"]
    .apply(lambda x: (x == -1).mean())
    .reset_index(name="topic_-1_ratio_after")
)

sku_t1_compare = sku_t1_before.merge(sku_t1_after, on="sku_id", how="outer").fillna(0)
sku_t1_compare = sku_t1_compare.merge(
    sku_name_df[["sku_id", "generated_name"]],
    on="sku_id",
    how="left"
)

sku_t1_compare.to_csv("exp2_sku_topic_minus1_before_after.csv", index=False, encoding="utf-8-sig")
print("\n[SKU级 Topic -1 前后对比] 示例：")
print(sku_t1_compare.sort_values("topic_-1_ratio_before", ascending=False).head(10))


# =========================
# 实验二（2）：SKU 级案例分析（补全 before 的 topic_-1_ratio）
# =========================

# 选评论数最多的前 8 个 SKU
top_skus = (
    df.groupby("sku_id")
    .size()
    .sort_values(ascending=False)
    .head(8)
    .index
)

records = []

for sku in top_skus:
    df_before = df[df["sku_id"] == sku]
    df_after = df_model[df_model["sku_id"] == sku]

    # 过滤前 topic -1（用 df_before_topics 的 topic_id_before）
    before_t1 = (
        df_before_topics[df_before_topics["sku_id"] == sku]["topic_id_before"].eq(-1).mean()
        if len(df_before_topics[df_before_topics["sku_id"] == sku]) > 0 else 0.0
    )

    rec = {
        "sku_id": sku,
        "generated_name": sku_name_df.loc[sku_name_df["sku_id"] == sku, "generated_name"].values[0]
        if sku in sku_name_df["sku_id"].values else "",
        "raw_cnt": len(df_before),
        "valid_cnt": len(df_after),
        "valid_ratio": round(len(df_after) / max(1, len(df_before)), 4),
        "avg_sentiment_before": round(df_before["sentiment_score"].mean(), 4),
        "avg_sentiment_after": round(df_after["sentiment_score"].mean(), 4),

        # ✅ 补全：过滤前 vs 过滤后 topic -1
        "topic_-1_ratio_before": round(before_t1, 4),
        "topic_-1_ratio_after": round((df_after["topic_id"] == -1).mean(), 4),
    }
    records.append(rec)

sku_case_compare = pd.DataFrame(records)
sku_case_compare.to_csv("exp2_sku_case_compare.csv", index=False, encoding="utf-8-sig")

print("\n[实验2-SKU案例] 示例：")
print(sku_case_compare)

