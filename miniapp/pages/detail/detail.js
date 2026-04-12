// pages/detail/detail.js
const detailsData = require('../../utils/data/details_new');

function fmt(v, d) {
  if (v === undefined || v === null) return '--';
  const n = Number(v);
  if (isNaN(n)) return '--';
  return n.toFixed(d === undefined ? 2 : d);
}

Page({
  data: {
    detail: null,
    aspects: [],
  },

  onLoad(options) {
    const skuId = decodeURIComponent(options.sku_id || '');
    const item = detailsData[skuId];

    if (!item) {
      wx.showToast({ title: '未找到商品数据', icon: 'none' });
      return;
    }

    const d = item.detail;
    const pos = Number(d.aspect_positive_ratio || 0) * 100;
    const neg = Number(d.aspect_negative_ratio || 0) * 100;
    const neu = Math.max(0, 100 - pos - neg);
    const sent = Number(d.aspect_sentiment_mean || 0);

    const detail = {
      ...d,
      score_text: fmt(d.recommend_score, 1),
      sent_text:  fmt(d.aspect_sentiment_mean, 3),
      sent_class: sent >= 0 ? 'pos-val' : 'neg-val',
      abs_text:   fmt(d.aspect_sentiment_abs_mean, 3),
      conf_text:  fmt(d.absa_confidence_mean, 3),
      known_text: fmt(Number(d.aspect_known_ratio || 1) * 100, 1),
      pos_bar:    pos.toFixed(1),
      neg_bar:    neg.toFixed(1),
      neu_bar:    neu.toFixed(1),
      pos_text:   pos.toFixed(1),
      neg_text:   neg.toFixed(1),
      neu_text:   neu.toFixed(1),
    };

    // 方面数据处理
    const aspects = (item.aspects || []).map(a => {
      const s = Number(a.aspect_sentiment_mean || 0);
      // 条形图宽度：将[-1,1]映射到[0,100]
      const barW = Math.round((s + 1) / 2 * 100);
      return {
        ...a,
        sent_text:  fmt(a.aspect_sentiment_mean, 3),
        sent_class: s >= 0 ? 'pos-val' : 'neg-val',
        bar_width:  barW,
        pos_text:   fmt(Number(a.aspect_positive_ratio || 0) * 100, 1),
        neg_text:   fmt(Number(a.aspect_negative_ratio || 0) * 100, 1),
      };
    });

    this.setData({ detail, aspects });
  }
});
