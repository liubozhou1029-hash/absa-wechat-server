const phonesData = require('../../utils/data/phones');

function formatPercent(value) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return (num * 100).toFixed(1);
}

function formatNumber(value, digits) {
  if (digits === undefined) digits = 4;
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(digits);
}

function safeText(value, fallback) {
  if (fallback === undefined) fallback = '--';
  if (value === undefined || value === null || value === '') return fallback;
  return String(value);
}

function safeInt(value, fallback) {
  if (fallback === undefined) fallback = 0;
  const num = Number(value);
  if (Number.isNaN(num)) return fallback;
  return Math.round(num);
}

function pickDisplayName(item) {
  if (item.display_name !== undefined && item.display_name !== null && item.display_name !== '') {
    return String(item.display_name);
  }
  if (item.original_name !== undefined && item.original_name !== null && item.original_name !== '') {
    return String(item.original_name);
  }
  return '未命名商品';
}

Page({
  data: {
    loading: true,
    list: []
  },

  onLoad() {
    const list = phonesData.map((item) => {
      return Object.assign({}, item, {
        display_name_text: pickDisplayName(item),
        recommend_index_v2_text: formatNumber(item.recommend_index_v2, 2),
        sentiment_index_text: formatNumber(item.sentiment_index, 2),
        aspect_sentiment_mean_text: formatNumber(item.aspect_sentiment_mean, 4),
        avg_sentiment_text: formatNumber(item.avg_sentiment, 4),
        aspect_positive_ratio_text: formatPercent(item.aspect_positive_ratio),
        effective_ratio_text: formatPercent(item.effective_ratio),
        effective_comments_text: safeInt(item.effective_comments, 0)
      });
    });

    list.sort((a, b) => {
      const va = Number(a.recommend_index_v2);
      const vb = Number(b.recommend_index_v2);
      const na = Number.isNaN(va) ? 0 : va;
      const nb = Number.isNaN(vb) ? 0 : vb;
      return nb - na;
    });

    this.setData({
      list: list,
      loading: false
    });
  },

  goDetail(e) {
    const skuId = e.currentTarget.dataset.sku;
    wx.navigateTo({
      url: `/pages/detail/detail?sku_id=${skuId}`
    });
  }
});