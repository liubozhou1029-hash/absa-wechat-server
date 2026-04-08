const detailsData = require('../../utils/data/details');

function formatPercent(value) {
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return (num * 100).toFixed(1);
}

function formatNumber(value, digits) {
  if (digits === undefined) digits = 2;
  if (value === undefined || value === null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(digits);
}

function pickDisplayName(detail) {
  if (detail.display_name) return String(detail.display_name);
  if (detail.original_name) return String(detail.original_name);
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
      if (!item || !item.detail) return;
      const d = item.detail;

      // 情感分布条宽度（直接用百分比数值，wx:style 里填 %）
      const posRatio  = d.pos_ratio  != null ? (d.pos_ratio  * 100) : 0;
      const negRatio  = d.neg_ratio  != null ? (d.neg_ratio  * 100) : 0;
      const neuRatio  = Math.max(0, 100 - posRatio - negRatio);

      result.push({
        sku_id: d.sku_id,
        display_name_text: pickDisplayName(d),

        // 右上角：百分制推荐分
        recommend_score_text: formatNumber(d.recommend_score, 2),

        // 情感指数（avg_sentiment × 100）
        avg_sentiment_score_text: d.avg_sentiment != null
          ? formatNumber(d.avg_sentiment * 100, 1)
          : '--',

        // 正负向文本比例
        pos_ratio_text: formatPercent(d.pos_ratio),
        neg_ratio_text: formatPercent(d.neg_ratio),
        pos_bar_width:  posRatio.toFixed(1),
        neg_bar_width:  negRatio.toFixed(1),
        neu_bar_width:  neuRatio.toFixed(1),

        // ABSA 方面级
        has_absa: !!d.has_absa,
        aspect_sentiment_mean_text:  formatNumber(d.aspect_sentiment_mean, 4),
        aspect_positive_ratio_text:  formatPercent(d.aspect_positive_ratio),
        aspect_negative_ratio_text:  formatPercent(d.aspect_negative_ratio),
      });
    });

    // 按推荐分降序
    result.sort((a, b) => {
      const va = Number(a.recommend_score_text);
      const vb = Number(b.recommend_score_text);
      return (isNaN(vb) ? -999 : vb) - (isNaN(va) ? -999 : va);
    });

    this.setData({ list: result, loading: false });
  },

  goDetail(e) {
    const skuId = e.currentTarget.dataset.sku;
    wx.navigateTo({ url: `/pages/detail/detail?sku_id=${skuId}` });
  }
});