# 商品评论实体抽取器

从6万条中文评论中，自动推断具体商品名称（书名、品牌型号、水果品种等）。

## 文件说明

| 文件 | 说明 |
|------|------|
| `product_entity_extractor.py` | 主处理脚本（正式运行用） |
| `cost_estimate_and_test.py`   | 预检工具（先跑这个！） |
| `requirements.txt`            | 依赖包 |

## 快速开始

### 第一步：安装依赖
```bash
pip install -r requirements.txt
```

### 第二步：配置 API Key
```bash
# Mac / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows CMD
set ANTHROPIC_API_KEY=sk-ant-...
```

### 第三步：修改配置（在主脚本顶部）
```python
INPUT_FILE   = "reviews.csv"   # 改成你的实际文件名
COL_CATEGORY = "category"      # 改成你的品类列名
COL_REVIEW   = "review"        # 改成你的评论列名
COL_SENTIMENT = "sentiment"    # 改成你的情感列名
```

### 第四步：先跑预检（强烈推荐）
```bash
python cost_estimate_and_test.py
```
这会告诉你预计费用和样本效果，确认满意后再正式运行。

### 第五步：正式运行
```bash
python product_entity_extractor.py
```

## CSV 列名说明

你的数据至少需要包含以下列：

| 列名（默认） | 含义 | 示例 |
|-------------|------|------|
| `category`  | 品类 | 书籍、平板、水果 |
| `sentiment` | 情感 | 0（负向）/ 1（正向） |
| `review`    | 评论文本 | "这本书写得很好..." |

输出文件会新增 `product` 列：
| `product` | 抽取结果 | 刘墉的作品、华为MatePad Pro |

## 断点续传

脚本运行中断后，重新运行会**自动从上次中断处继续**，不会重复处理已完成的数据。

中断恢复靠 `progress.json` 文件，请勿删除（全部完成后会自动清理）。

## 品类 Prompt 定制

在 `product_entity_extractor.py` 的 `CATEGORY_PROMPTS` 字典中，可以为每个品类单独调整提示词。

如果你的数据有新品类，在 `CATEGORY_MAP` 中添加关键词映射即可：
```python
CATEGORY_MAP = {
    "服装": "服饰",
    "衣服": "服饰",
    # ... 在这里加新品类
}
```

## 成本参考（claude-haiku-4-5）

| 规模 | 预估费用 |
|------|---------|
| 1万条 | ~$0.30 |
| 6万条 | ~$1.80 |
| 10万条 | ~$3.00 |

以上为粗略估算，实际取决于评论长度。
