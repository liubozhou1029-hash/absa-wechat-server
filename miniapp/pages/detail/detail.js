const detailsData = require('../../utils/data/details');

function formatPercent(value) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return (num * 100).toFixed(1);
}

function formatNumber(value, digits = 4) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(digits);
}

function safeText(value, fallback = '--') {
  if (value === undefined || value === null || value === '') return fallback;
  return String(value);
}

function safeInt(value, fallback = 0) {
  const num = Number(value);
  if (Number.isNaN(num)) return fallback;
  return Math.round(num);
}

Page({
  data: {
    sku_id: '',
    detail: null,
    topics: [],
    has_absa: false
  },

  onLoad(options) {
    const skuId = options.sku_id || '';
    const item = detailsData[skuId];

    if (item) {
      const detail = item.detail || {};
      const topics = item.topics || [];
      const has_absa = !!detail.has_absa;

      const detailView = {
        ...detail,

        display_name_text: safeText(detail.display_name || detail.original_name, '未命名商品'),

        // 核心推荐分（百分制）
        recommend_score_text: formatNumber(detail.recommend_score, 2),
        // V1 情感分（参考）
        v1_score_text: formatNumber(detail.v1_score, 2),
        // 分数来源标签
        score_source: has_absa ? '整体情感 + ABSA 方面级融合' : '整体情感推荐指数',
        // 情感统计卡片右上角角标：avg_sentiment × 100
        avg_sentiment_score_text: formatNumber(
          detail.avg_sentiment != null ? detail.avg_sentiment * 100 : null, 1
        ),

        // 整体情感统计
        total_comments_text:     safeInt(detail.total_comments, 0),
        effective_comments_text: safeInt(detail.effective_comments, 0),
        avg_sentiment_text:      formatNumber(detail.avg_sentiment, 4),
        std_sentiment_text:      formatNumber(detail.std_sentiment, 4),
        effective_ratio_text:    formatPercent(detail.effective_ratio),
        pos_ratio_text:          formatPercent(detail.pos_ratio),
        neg_ratio_text:          formatPercent(detail.neg_ratio),
        topic_top1_ratio_text:   formatPercent(detail.topic_top1_ratio),
        avg_rating_norm_text:    formatNumber(detail.avg_rating_norm, 4),
        volume_factor_text:      formatNumber(detail.volume_factor, 4),

        // ABSA 方面级
        absa_comment_count_text:        safeInt(detail.absa_comment_count, 0),
        aspect_sentiment_mean_text:     formatNumber(detail.aspect_sentiment_mean, 4),
        aspect_sentiment_abs_mean_text: formatNumber(detail.aspect_sentiment_abs_mean, 4),
        aspect_positive_ratio_text:     formatPercent(detail.aspect_positive_ratio),
        aspect_negative_ratio_text:     formatPercent(detail.aspect_negative_ratio),
        aspect_neutral_ratio_text:      formatPercent(detail.aspect_neutral_ratio),
        aspect_known_ratio_text:        formatPercent(detail.aspect_known_ratio),
        absa_confidence_mean_text:      formatNumber(detail.absa_confidence_mean, 4),
      };

      const topicView = topics.map((topic) => ({
        ...topic,
        ratio_text: `${formatPercent(topic.ratio)}%`
      }));

      this.setData({
        sku_id: skuId,
        detail: detailView,
        topics: topicView,
        has_absa
      });
    } else {
      wx.showToast({ title: '未找到详情数据', icon: 'none' });
    }
  }
});