# 🧠 ABSA-Based Recommendation System

基于**方面级情感分析（Aspect-Based Sentiment Analysis, ABSA）**的商品推荐优化系统。

本项目通过对用户评论进行方面级情感分析，构建商品情感特征，并将其融合到推荐模型中，实现推荐结果的优化与重排。

---

## 📌 项目背景

传统推荐系统主要依赖：

- 用户行为（点击、购买）
- 商品特征（评分、销量）

但存在问题：

> ❗ 无法细粒度理解用户评论中的具体优缺点

例如：

- “屏幕很好，但电池不行”
- “性价比高，但做工一般”

👉 ABSA 可以解决这个问题。

---

## 🚀 项目目标

- 提取评论中的方面信息（aspect）
- 判断每个方面的情感极性
- 构建 SKU 级情感特征
- 优化推荐排序，提高推荐质量与可解释性

---

## 🏗️ 项目结构

```bash
absa-wechat-server/
├── scripts/
│   └── v2_absa/
│       ├── run_absa_full.py
│       ├── parse_absa_full.py
│       ├── aggregate_absa_full.py
│       ├── build_recommend_v2.py
│       └── compare_v1_v2.py
│
├── config.py
├── .gitignore
└── README.md
```
---

## ⚙️ 核心流程
评论数据
↓
ABSA模型（方面 + 情感）
↓
情感解析（数值化）
↓
SKU级特征聚合
↓
排序融合重排
↓
推荐结果优化

---

## 🧩 方法说明

### 1️⃣ ABSA情感建模

对每条评论进行：

- aspect抽取
- 情感分类（Positive / Negative / Neutral）
- 置信度预测

---

### 2️⃣ 情感数值化
Positive → score = confidence
Negative → score = 1 - confidence
Neutral → score = 0.5

---

### 3️⃣ SKU级特征构建

| 特征 | 含义 |
|------|------|
| aspect_sentiment_mean | 情感均值 |
| aspect_positive_ratio | 正面比例 |
| aspect_negative_ratio | 负面比例 |
| aspect_neutral_ratio  | 中性比例 |
| absa_confidence_mean  | 平均置信度 |

---

### 4️⃣ 推荐融合（核心创新）

采用排序融合方法：
rank_score =
0.55 * rank_base

0.20 * rank_sentiment
0.20 * rank_negative
0.05 * rank_confidence
recommend_index_v2 = -rank_score

---

## 📊 实验结果

### ✔ 排名上升商品

- 负面比例较低（约 0.00 ~ 0.06）

### ✔ 排名下降商品

- 负面比例较高（约 0.10 ~ 0.17）

👉 说明情感特征对推荐排序产生有效影响

---

### ✔ 新版 Top 推荐特征

- 正面比例高
- 负面比例低

👉 推荐质量得到提升

---

## 🧪 实验流程（可复现）
python scripts/v2_absa/run_absa_full.py
python scripts/v2_absa/parse_absa_full.py
python scripts/v2_absa/aggregate_absa_full.py
python scripts/v2_absa/build_recommend_v2.py
python scripts/v2_absa/compare_v1_v2.py

---

## 🛠️ 环境依赖

- Python 3.10+
- PyTorch（支持GPU）
- pandas
- PyABSA
- transformers

---

## ✨ 项目亮点

- 引入ABSA细粒度情感分析
- 构建可解释推荐特征
- 使用排序融合提升稳定性
- 推荐结果具备可解释性

---

## 🔮 后续优化方向

- 用户个性化情感偏好建模
- 不同方面权重学习
- 时间衰减机制
- Learning to Rank 模型

---

## 📚 适用场景

- 电商推荐系统
- 评论分析系统
- 商品质量评估
- 用户体验分析

---

## 👤 作者

刘泊舟  
四川大学计算机科学与技术

---

## 📌 说明

本项目为毕业设计/研究实验项目，仅用于学术研究。
