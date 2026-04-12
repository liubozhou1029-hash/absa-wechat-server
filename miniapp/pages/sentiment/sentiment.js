// pages/sentiment/sentiment.js
const phonesData = require('../../utils/data/phones_new');

function fmt(v, d) {
  if (v === undefined || v === null) return '--';
  const n = Number(v);
  if (isNaN(n)) return '--';
  return n.toFixed(d === undefined ? 2 : d);
}

function processItem(item) {
  const pos = Number(item.aspect_positive_ratio || 0) * 100;
  const neg = Number(item.aspect_negative_ratio || 0) * 100;
  const neu = Math.max(0, 100 - pos - neg);
  return {
    ...item,
    score_text: fmt(item.recommend_score, 1),
    pos_bar: pos.toFixed(1), neg_bar: neg.toFixed(1), neu_bar: neu.toFixed(1),
    pos_text: pos.toFixed(1), neg_text: neg.toFixed(1), neu_text: neu.toFixed(1),
  };
}

const CAT_ORDER = ['酒店','水果','衣服','书籍','平板','洗发水','蒙牛','计算机','手机','热水器'];
const TOP_PER_CAT = 5;

// 中文品类→拼音ID映射（避免中文ID在小程序里失效）
const CAT_ID_MAP = {
  '酒店': 'jiudian', '水果': 'shuiguo', '衣服': 'yifu',
  '书籍': 'shuji', '平板': 'pingban', '洗发水': 'xifashui',
  '蒙牛': 'mengniu', '计算机': 'jisuanji', '手机': 'shouji', '热水器': 'reshuiqi'
};

function buildGroups(data, sortKey) {
  return CAT_ORDER.map(cat => {
    const list = data
      .filter(i => i.cat === cat)
      .sort((a, b) => Number(b[sortKey]) - Number(a[sortKey]))
      .slice(0, TOP_PER_CAT)
      .map(processItem);
    return { cat, catId: CAT_ID_MAP[cat] || cat, list, count: list.length };
  }).filter(g => g.count > 0);
}

Page({
  data: {
    loading: true,
    activeTab: 'good',
    selectedCat: '酒店',
    catList: CAT_ORDER,
    catIdMap: CAT_ID_MAP,
    goodGroups: [],
    badGroups: [],
  },

  onLoad() {
    const goodGroups = buildGroups(phonesData, 'aspect_positive_ratio');
    const badGroups  = buildGroups(phonesData, 'aspect_negative_ratio');
    this.setData({ goodGroups, badGroups, loading: false });
  },

  switchTab(e) {
    this.setData({ activeTab: e.currentTarget.dataset.tab, selectedCat: '酒店' });
  },

  scrollToCat(e) {
    const cat   = e.currentTarget.dataset.cat;
    const tab   = this.data.activeTab;
    const catId = CAT_ID_MAP[cat] || cat;
    this.setData({ selectedCat: cat });
    wx.pageScrollTo({
      selector: '#' + tab + '-' + catId,
      duration: 300,
      offsetTop: -180,
    });
  },

  goDetail(e) {
    const skuId = e.currentTarget.dataset.sku;
    const tab   = e.currentTarget.dataset.tab;
    wx.navigateTo({
      url: `/pages/sentiment_detail/sentiment_detail?sku_id=${encodeURIComponent(skuId)}&tab=${tab}`
    });
  }
});
