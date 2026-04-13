// pages/phones/phones.js
const phonesData = require('../../utils/data/phones_new');

function fmt(v, d) {
  if (v === undefined || v === null || v === '') return '--';
  const n = Number(v);
  if (isNaN(n)) return '--';
  return n.toFixed(d === undefined ? 2 : d);
}

function genReason(item) {
  const pos   = Number(item.aspect_positive_ratio || 0) * 100;
  const neg   = Number(item.aspect_negative_ratio || 0) * 100;
  const sent  = Number(item.aspect_sentiment_mean || 0);
  const n     = Number(item.absa_comment_count || 0);
  const score = Number(item.recommend_score || 0);
  let parts = [];
  if (pos >= 90) parts.push('基于' + n + '条评论，好评率高达' + pos.toFixed(0) + '%');
  else if (pos >= 70) parts.push('基于' + n + '条评论，好评率' + pos.toFixed(0) + '%');
  else parts.push('基于' + n + '条评论综合评估');
  if (sent >= 0.8) parts.push('用户方面情感高度正向');
  else if (sent >= 0.5) parts.push('用户方面情感整体偏正向');
  else if (sent >= 0) parts.push('用户情感较为中性');
  else parts.push('存在一定负面反馈');
  if (neg > 20) parts.push('差评率' + neg.toFixed(0) + '%需注意');
  parts.push('综合推荐分' + score.toFixed(1) + '分');
  return parts.join('，') + '。';
}

function processItem(item, rank) {
  const pos  = Number(item.aspect_positive_ratio || 0) * 100;
  const neg  = Number(item.aspect_negative_ratio || 0) * 100;
  const neu  = Math.max(0, 100 - pos - neg);
  const sent = Number(item.aspect_sentiment_mean || 0);
  return {
    ...item, rank,
    score_text: fmt(item.recommend_score, 1),
    sent_text:  fmt(item.aspect_sentiment_mean, 3),
    sent_class: sent >= 0 ? 'pos-val' : 'neg-val',
    conf_text:  fmt(item.absa_confidence_mean, 3),
    pos_bar: pos.toFixed(1), neg_bar: neg.toFixed(1), neu_bar: neu.toFixed(1),
    pos_text: pos.toFixed(1), neg_text: neg.toFixed(1), neu_text: neu.toFixed(1),
    reason: genReason(item),
  };
}

const CAT_ORDER = ['酒店','水果','衣服','书籍','平板','洗发水','蒙牛','计算机','手机','热水器'];
const CAT_ID_MAP = {
  '酒店':'jiudian','水果':'shuiguo','衣服':'yifu','书籍':'shuji',
  '平板':'pingban','洗发水':'xifashui','蒙牛':'mengniu',
  '计算机':'jisuanji','手机':'shouji','热水器':'reshuiqi'
};
const TOP_PER_CAT = 20;

Page({
  data: {
    loading: true,
    catGroups: [],
    catList: [],
    selectedCat: '酒店',
    chartData: [],
    searchText: '',
    searchResults: [],
    allList: [],  // 搜索用的完整列表
  },

  onLoad() {
    // 构建品类分组
    const catGroups = CAT_ORDER.map(cat => {
      const list = phonesData
        .filter(i => i.cat === cat)
        .sort((a, b) => Number(b.recommend_score) - Number(a.recommend_score))
        .slice(0, TOP_PER_CAT)
        .map((item, idx) => processItem(item, idx + 1));
      return { cat, catId: CAT_ID_MAP[cat] || cat, list, count: list.length };
    }).filter(g => g.count > 0);

    // 搜索用全量列表
    const allList = phonesData.map((item, idx) => processItem(item, idx + 1));

    // 品类好评率图表数据（取每个品类的平均好评率）
    const chartData = CAT_ORDER.map(cat => {
      const items = phonesData.filter(i => i.cat === cat);
      if (items.length === 0) return null;
      const avg = items.reduce((s, i) => s + Number(i.aspect_positive_ratio || 0), 0) / items.length;
      const posRate = Math.round(avg * 100);
      return { cat, pos_rate: posRate, pos_bar: posRate };
    }).filter(Boolean);

    this.setData({ catGroups, catList: CAT_ORDER, allList, chartData, loading: false });
  },

  onSearch(e) {
    const text = e.detail.value.trim();
    this.setData({ searchText: text });
    if (!text) {
      this.setData({ searchResults: [] });
      return;
    }
    const results = this.data.allList
      .filter(i => i.sku_id && i.sku_id.includes(text))
      .slice(0, 30);
    this.setData({ searchResults: results });
  },

  clearSearch() {
    this.setData({ searchText: '', searchResults: [] });
  },

  scrollToCat(e) {
    const cat   = e.currentTarget.dataset.cat;
    const catId = CAT_ID_MAP[cat] || cat;
    this.setData({ selectedCat: cat });
    wx.pageScrollTo({ selector: '#cat-' + catId, duration: 300, offsetTop: -180 });
  },

  goDetail(e) {
    const skuId = e.currentTarget.dataset.sku;
    wx.navigateTo({ url: '/pages/detail/detail?sku_id=' + encodeURIComponent(skuId) });
  }
});
