from pathlib import Path

# backend/config.py
# 当前文件位置：仓库根目录/backend/config.py

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

# =========================
# backend 内部目录
# =========================
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
TEMP_DIR = DATA_DIR / "temp"

SCRIPTS_DIR = BACKEND_DIR / "scripts"
V1_DIR = SCRIPTS_DIR / "v1"
V2_ABSA_DIR = SCRIPTS_DIR / "v2_absa"
APP_DIR = SCRIPTS_DIR / "app"

V2_MODEL_DIR = BACKEND_DIR / "v2_absa_model"

# =========================
# service / miniapp 路径
# =========================
SERVICE_DIR = REPO_ROOT / "service"
MINIAPP_DIR = REPO_ROOT / "miniapp"
MINIAPP_DATA_DIR = MINIAPP_DIR / "utils" / "data"

HF_CACHE_DIR = REPO_ROOT / "hf_cache"

# =========================
# 原始数据
# =========================
RAW_COMMENTS_FILE = RAW_DIR / "京东评论数据.csv"

# =========================
# ABSA 中间文件
# =========================
ABSA_FULL_RESULTS_FILE = PROCESSED_DIR / "absa_full_results.csv"
ABSA_FULL_RESULTS_PARTIAL_FILE = PROCESSED_DIR / "absa_full_results_partial.csv"
ABSA_FULL_PARSED_FILE = PROCESSED_DIR / "absa_full_parsed.csv"

ABSA_SMALL_RESULTS_FILE = PROCESSED_DIR / "absa_small_results.csv"
ABSA_SMALL_PARSED_FILE = PROCESSED_DIR / "absa_small_parsed.csv"

COMMENT_WITH_SPAM_SENTIMENT_FILE = PROCESSED_DIR / "comment_with_spam_and_sentiment.csv"

# =========================
# 聚合 / 推荐结果
# =========================
SKU_METRICS_FILE = RESULTS_DIR / "sku_metrics.csv"
SKU_ABSA_FEATURES_FILE = RESULTS_DIR / "sku_absa_features.csv"
SKU_RECOMMEND_INDEX_FILE = RESULTS_DIR / "sku_recommend_index.csv"
SKU_RECOMMEND_INDEX_V2_FILE = RESULTS_DIR / "sku_recommend_index_v2.csv"

COMPARE_V1_V2_FULL_FILE = RESULTS_DIR / "compare_v1_v2_full.csv"
COMPARE_V1_V2_TOP_RISE_FILE = RESULTS_DIR / "compare_v1_v2_top_rise.csv"
COMPARE_V1_V2_TOP_DROP_FILE = RESULTS_DIR / "compare_v1_v2_top_drop.csv"

# =========================
# 微信小程序导出文件
# =========================
WECHAT_OLD_DETAILS_FILE = MINIAPP_DATA_DIR / "details.js"
WECHAT_OLD_PHONES_FILE = MINIAPP_DATA_DIR / "phones.js"
WECHAT_NEW_DETAILS_FILE = MINIAPP_DATA_DIR / "details_new.js"
WECHAT_NEW_PHONES_FILE = MINIAPP_DATA_DIR / "phones_new.js"


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MINIAPP_DATA_DIR.mkdir(parents=True, exist_ok=True)