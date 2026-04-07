const detailsData = require('../../utils/data/details');

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

function pickDisplayName(detail) {
  if (detail.display_name !== undefined && detail.display_name !== null && detail.display_name !== '') {
    return String(detail.display_name);
  }
  if (detail.original_name !== undefined && detail.original_name !== null && detail.original_name !== '') {
    return String(detail.original_name);
  }
  return '未命名商品';
}

Page({
  data: {
    loading: true,
    list: []
  },

  onLoad() {
    const result = [];

    Object.keys(detailsData).forEach((skuId) => {
      const item = detailsData[skuId];
      if (item && item.detail) {
        const d = item.detail;

        result.push({
          sku_id: d.sku_id,
          display_name_text: pickDisplayName(d),
          sentiment_index_text: formatNumber(d.sentiment_index, 2),
          recommend_index_v2_text: formatNumber(d.recommend_index_v2, 2),
          avg_sentiment_text: formatNumber(d.avg_sentiment, 4),
          pos_ratio_text: formatPercent(d.pos_ratio),
          neg_ratio_text: formatPercent(d.neg_ratio),
          aspect_sentiment_mean_text: formatNumber(d.aspect_sentiment_mean, 4),
          aspect_positive_ratio_text: formatPercent(d.aspect_positive_ratio),
          aspect_negative_ratio_text: formatPercent(d.aspect_negative_ratio)
        });
      }
    });

    result.sort((a, b) => Number(b.recommend_index_v2_text) - Number(a.recommend_index_v2_text));

    this.setData({
      list: result,
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