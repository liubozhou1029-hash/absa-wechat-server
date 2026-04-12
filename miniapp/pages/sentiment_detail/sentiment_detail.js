// pages/sentiment_detail/sentiment_detail.js
const detailsData = require('../../utils/data/details_new');

function fmt(v, d) {
  const n = Number(v);
  if (isNaN(n)) return '--';
  return n.toFixed(d === undefined ? 2 : d);
}

Page({
  data: { detail: null, aspects: [], isGood: true },

  onLoad(options) {
    const skuId  = decodeURIComponent(options.sku_id || '');
    const isGood = (options.tab || 'good') === 'good';
    const item   = detailsData[skuId];
    if (!item) { wx.showToast({ title: '未找到数据', icon: 'none' }); return; }

    const d = item.detail;
    const pos = Number(d.aspect_positive_ratio || 0) * 100;
    const neg = Number(d.aspect_negative_ratio || 0) * 100;
    const neu = Math.max(0, 100 - pos - neg);
    const n   = Number(d.absa_comment_count || 0);

    const detail = {
      ...d,
      score_text: fmt(d.recommend_score, 1),
      pos_bar: pos.toFixed(1), neg_bar: neg.toFixed(1), neu_bar: neu.toFixed(1),
      pos_text: pos.toFixed(1), neg_text: neg.toFixed(1), neu_text: neu.toFixed(1),
    };

    // 方面数据：带正/负向条数估算
    const aspects = (item.aspects || [])
      .map(a => {
        const cnt    = Number(a.aspect_count || 0);
        const posR   = Number(a.aspect_positive_ratio || 0);
        const negR   = Number(a.aspect_negative_ratio || 0);
        return {
          ...a,
          pos_pct:   (posR * 100).toFixed(1),
          neg_pct:   (negR * 100).toFixed(1),
          pos_count: Math.round(cnt * posR),
          neg_count: Math.round(cnt * negR),
        };
      })
      .sort((a, b) => isGood
        ? Number(b.aspect_positive_ratio) - Number(a.aspect_positive_ratio)
        : Number(b.aspect_negative_ratio) - Number(a.aspect_negative_ratio)
      );

    this.setData({ detail, aspects, isGood });
    wx.setNavigationBarTitle({ title: isGood ? '好评方面详情' : '差评方面详情' });
  }
});
