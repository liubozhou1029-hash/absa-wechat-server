const phonesData = require('../../utils/data/phones');

function formatPercent(value) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return (num * 100).toFixed(1);
}

function formatNumber(value, digits = 2) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(digits);
}

function safeInt(value, fallback = 0) {
  const num = Number(value);
  if (Number.isNaN(num)) return fallback;
  return Math.round(num);
}

function pickDisplayName(item) {
  if (item.display_name) return String(item.display_name);
  if (item.original_name) return String(item.original_name);
  return '未命名商品';
}

Page({
  data: {
    loading: true,
    list: []
  },

  onLoad() {
    const list = phonesData.map((item) => {
      return {
        ...item,
        display_name_text: pickDisplayName(item),
        score_text: formatNumber(item.recommend_score, 2),

        // 辅助指标
        avg_sentiment_text:         formatNumber(item.avg_sentiment, 4),
        aspect_sentiment_mean_text: formatNumber(item.aspect_sentiment_mean, 4),
        aspect_positive_ratio_text: formatPercent(item.aspect_positive_ratio),
        aspect_negative_ratio_text: formatPercent(item.aspect_negative_ratio),
        effective_ratio_text:       formatPercent(item.effective_ratio),
        effective_comments_text:    safeInt(item.effective_comments, 0),
        total_comments_text:        safeInt(item.total_comments, 0),
        absa_comment_count_text:    safeInt(item.absa_comment_count, 0),
      };
    });

    // 按推荐分降序（数据已排好序，前端保持一致）
    list.sort((a, b) => {
      const va = Number(a.recommend_score);
      const vb = Number(b.recommend_score);
      return (Number.isNaN(vb) ? -999999 : vb) - (Number.isNaN(va) ? -999999 : va);
    });

    this.setData({ list, loading: false });
  },

  goDetail(e) {
    const skuId = e.currentTarget.dataset.sku;
    wx.navigateTo({
      url: `/pages/detail/detail?sku_id=${skuId}`
    });
  }
});