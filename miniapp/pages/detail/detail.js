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
    topics: []
  },

  onLoad(options) {
    const skuId = options.sku_id || '';
    const item = detailsData[skuId];

    if (item) {
      const detail = item.detail || {};
      const topics = item.topics || [];

      const detailView = {
        ...detail,

        display_name_text: safeText(detail.display_name || detail.original_name, '未命名商品'),

        effective_comments_text: safeInt(detail.effective_comments, 0),
        absa_comment_count_text: safeInt(detail.absa_comment_count, 0),

        pos_ratio_text: formatPercent(detail.pos_ratio),
        neg_ratio_text: formatPercent(detail.neg_ratio),
        effective_ratio_text: formatPercent(detail.effective_ratio),
        topic_top1_ratio_text: formatPercent(detail.topic_top1_ratio),

        aspect_positive_ratio_text: formatPercent(detail.aspect_positive_ratio),
        aspect_negative_ratio_text: formatPercent(detail.aspect_negative_ratio),
        aspect_neutral_ratio_text: formatPercent(detail.aspect_neutral_ratio),

        avg_sentiment_text: formatNumber(detail.avg_sentiment, 4),
        avg_rating_norm_text: formatNumber(detail.avg_rating_norm, 4),
        volume_factor_text: formatNumber(detail.volume_factor, 4),
        aspect_sentiment_mean_text: formatNumber(detail.aspect_sentiment_mean, 4),
        absa_confidence_mean_text: formatNumber(detail.absa_confidence_mean, 4),
        recommend_index_v2_text: formatNumber(detail.recommend_index_v2, 2),
        sentiment_index_text: formatNumber(detail.sentiment_index, 2)
      };

      this.setData({
        sku_id: skuId,
        detail: detailView,
        topics
      });
    } else {
      wx.showToast({
        title: '未找到详情数据',
        icon: 'none'
      });
    }
  }
});