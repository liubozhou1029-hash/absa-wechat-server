# 🧠 ABSA-Based Recommendation System

基于 **方面级情感分析（Aspect-Based Sentiment Analysis, ABSA）** 的商品推荐优化系统，结合用户评论语义与情感信息，对传统推荐结果进行重排序优化。

本项目构建了从 **评论数据 → 情感建模 → 特征构建 → 推荐优化 → 小程序展示** 的完整系统链路。

---

## 📌 项目概述

传统推荐系统主要依赖：

* 用户行为（点击、购买）
* 商品统计特征（评分、销量）

但存在明显不足：

> ❗ 无法理解评论中的细粒度语义信息

例如：

* “屏幕很好，但电池不行”
* “性价比高，但做工一般”

👉 本项目通过 **ABSA（方面级情感分析）** 建模评论细粒度信息，从而提升推荐质量与可解释性。

---

## 🏗️ 项目结构

```bash
absa-wechat-server/
├── backend/                # 核心算法与数据处理
│   ├── scripts/v2_absa/    # ABSA与推荐流程
│   ├── data/               # 数据（raw / processed / results）
│   ├── v2_absa_model/      # 模型文件
│   └── config.py           # 路径与配置管理
│
├── service/                # 轻量后端服务（数据接口）
│   ├── app.py
│   ├── build_static_json.py
│   └── *.csv               # 推荐结果数据
│
├── miniapp/                # 微信小程序前端
│   ├── pages/
│   ├── utils/
│   └── app.js
│
├── .gitignore
└── README.md
```

---

## ⚙️ 系统整体流程

```
用户评论数据
        ↓
ABSA情感分析（aspect + sentiment）
        ↓
情感解析（数值化）
        ↓
SKU级特征聚合
        ↓
推荐排序融合（v2）
        ↓
结果导出（JSON / CSV）
        ↓
小程序展示
```

---

## 🧩 核心方法

### 1️⃣ ABSA情感建模

对评论进行方面级分析：

* Aspect 抽取（规则 + 模型）
* 情感分类（Positive / Negative / Neutral）
* 置信度预测

---

### 2️⃣ 情感数值化建模

将情感标签转为连续值：

```text
Positive → +confidence
Negative → -confidence
Neutral  → 0
```

👉 构建可计算的情感信号

---

### 3️⃣ SKU级特征构建

对商品维度聚合：

| 特征                    | 含义    |
| --------------------- | ----- |
| aspect_sentiment_mean | 情感均值  |
| aspect_positive_ratio | 正面比例  |
| aspect_negative_ratio | 负面比例  |
| aspect_neutral_ratio  | 中性比例  |
| absa_confidence_mean  | 平均置信度 |

---

### 4️⃣ 推荐融合优化（核心创新）

采用 **排序融合（Rank Fusion）**：

```text
rank_score =
0.55 * rank_base 
0.20 * rank_sentiment 
0.20 * rank_negative 
0.05 * rank_confidence

recommend_index_v2 = -rank_score
```

👉 相比简单加权，更稳定、鲁棒性更强

---

## 📊 实验结果

### ✔ 排名提升商品

* 负面比例显著降低（≈ 0.00 ~ 0.06）
* 情感均值较高

---

### ✔ 排名下降商品

* 负面比例较高（≈ 0.10 ~ 0.17）

---

### ✔ 结论

👉 引入 ABSA 后：

* 推荐结果更加符合用户真实评价
* 推荐具备可解释性（可指出具体优缺点）

---

## 🧪 可复现实验流程

在 `backend/` 目录下运行：

```bash
python scripts/v2_absa/run_absa_full.py
python scripts/v2_absa/parse_absa_full.py
python scripts/v2_absa/aggregate_absa_full.py
python scripts/v2_absa/build_recommend_v2.py
python scripts/v2_absa/compare_v1_v2.py
```

---

## 🛠️ 技术栈

* Python 3.10+
* PyTorch
* PyABSA
* Transformers
* Pandas / NumPy
* Flask（轻量服务）
* 微信小程序

---

## ✨ 项目亮点

* 🔍 引入 ABSA，实现评论细粒度语义理解
* 📊 构建可解释推荐特征体系
* ⚖️ 采用排序融合，提高推荐稳定性
* 🔗 打通「模型 → 推荐 → 前端展示」完整链路
* 📱 支持微信小程序可视化展示

---

## 🔮 后续优化方向

* 用户个性化情感偏好建模
* Aspect 权重自学习（Attention / LTR）
* 时间衰减机制（Temporal Modeling）
* Learning to Rank / Deep Ranking

---

## 📚 应用场景

* 电商推荐系统
* 用户评论分析
* 商品质量评估
* 用户体验优化

---

## 👤 作者

刘泊舟
四川大学 · 计算机科学与技术

---

## 📌 项目说明

本项目为本科毕业设计 / 研究实验项目，用于探索情感分析与推荐系统的融合方法。
