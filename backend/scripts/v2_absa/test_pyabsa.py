import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# 一定要放在 import pyabsa 之前
os.environ["HF_HOME"] = r"F:\hf_cache"
os.environ["HF_HUB_CACHE"] = r"F:\hf_cache\hub"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from pyabsa import AspectPolarityClassification as APC

classifier = APC.SentimentClassifier("multilingual")

samples = [
    ("这个手机续航不错，但是发热严重。", "续航"),
    ("这个手机续航不错，但是发热严重。", "发热"),
    ("屏幕显示很好，拍照也很清晰。", "屏幕"),
    ("屏幕显示很好，拍照也很清晰。", "拍照"),
    ("物流很快，但是价格偏贵。", "物流"),
    ("物流很快，但是价格偏贵。", "价格"),
]

texts = [f"[B-ASP]{aspect}[E-ASP] {text}" for text, aspect in samples]

result = classifier.predict(
    texts,
    print_result=True,
    save_result=False
)

print(result)