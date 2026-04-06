from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"

# 脚本目录
SCRIPTS_DIR = BASE_DIR / "scripts"
V1_DIR = SCRIPTS_DIR / "v1"
V2_ABSA_DIR = SCRIPTS_DIR / "v2_absa"
APP_DIR = SCRIPTS_DIR / "app"

# 模型目录
V2_MODEL_DIR = BASE_DIR / "v2_absa_model"

# 原始数据
RAW_COMMENTS_FILE = RAW_DIR / "京东评论数据.csv"

# 中间文件
ABSA_FULL_RESULTS_FILE = PROCESSED_DIR / "absa_full_results.csv"
ABSA_FULL_RESULTS_PARTIAL_FILE = PROCESSED_DIR / "absa_full_results_partial.csv"
ABSA_FULL_PARSED_FILE = PROCESSED_DIR / "absa_full_parsed.csv"

ABSA_SMALL_RESULTS_FILE = PROCESSED_DIR / "absa_small_results.csv"
ABSA_SMALL_PARSED_FILE = PROCESSED_DIR / "absa_small_parsed.csv"

COMMENT_WITH_SPAM_SENTIMENT_FILE = PROCESSED_DIR / "comment_with_spam_and_sentiment.csv"

# 结果文件
SKU_METRICS_FILE = RESULTS_DIR / "sku_metrics.csv"
SKU_ABSA_FEATURES_FILE = RESULTS_DIR / "sku_absa_features.csv"
SKU_RECOMMEND_INDEX_FILE = RESULTS_DIR / "sku_recommend_index.csv"
SKU_RECOMMEND_INDEX_V2_FILE = RESULTS_DIR / "sku_recommend_index_v2.csv"

COMPARE_V1_V2_FULL_FILE = RESULTS_DIR / "compare_v1_v2_full.csv"
COMPARE_V1_V2_TOP_RISE_FILE = RESULTS_DIR / "compare_v1_v2_top_rise.csv"
COMPARE_V1_V2_TOP_DROP_FILE = RESULTS_DIR / "compare_v1_v2_top_drop.csv"

# 微信小程序路径（按你的实际情况）
WECHAT_APP_DIR = Path(r"F:\WeChat project\goodsrecommend")
WECHAT_DATA_DIR = WECHAT_APP_DIR / "utils" / "data"
WECHAT_OLD_DETAILS_FILE = WECHAT_DATA_DIR / "details.js"
WECHAT_OLD_PHONES_FILE = WECHAT_DATA_DIR / "phones.js"
WECHAT_NEW_DETAILS_FILE = WECHAT_DATA_DIR / "details_new.js"
WECHAT_NEW_PHONES_FILE = WECHAT_DATA_DIR / "phones_new.js"


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)