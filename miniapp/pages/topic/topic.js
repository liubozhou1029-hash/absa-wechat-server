const detailsData = require('../../utils/data/details');

function formatPercent(value) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return (num * 100).toFixed(1);
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
        const topics = item.topics ? item.topics : [];

        result.push({
          sku_id: item.detail.sku_id,
          display_id: item.detail.display_id,
          display_name_text: pickDisplayName(item.detail),
          topic_top1_ratio: item.detail.topic_top1_ratio,
          topic_top1_ratio_text: formatPercent(item.detail.topic_top1_ratio),
          topic_count: topics.length,
          topic_keywords: topics.length > 0 ? topics[0].keywords : '暂无关键词',
          topics: topics
        });
      }
    });

    result.sort((a, b) => {
      const va = Number(a.topic_top1_ratio);
      const vb = Number(b.topic_top1_ratio);
      const na = Number.isNaN(va) ? 0 : va;
      const nb = Number.isNaN(vb) ? 0 : vb;
      return nb - na;
    });

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