// pages/recommend/recommend.js
const app = getApp();

const EXAMPLE_TEXT = [
  "这本书内容深刻，作者文笔流畅，故事情节引人入胜，读完意犹未尽",
  "书的印刷质量很好，排版清晰，翻译也很地道，价格实惠值得购买",
  "作者写作功底深厚，内容有深度，装帧精美，物流很快包装完好",
  "文笔一般，内容有些重复，但价格便宜还算值得",
  "故事引人入胜，作者对细节把握很好，印刷清晰，客服也很热情"
].join("\n");

Page({
  data: {
    inputText: "",
    selectedTopK: 10,
    topkOptions: [5, 10, 15, 20],
    loading: false,
    loadingText: "正在分析...",
    hasResult: false,
    userCategory: "",
    preferences: [],
    sameCategory: { cat: "", reason: "", list: [] },
    crossCategory: { reason: "", list: [] },
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  fillExample() {
    this.setData({ inputText: EXAMPLE_TEXT });
  },

  selectTopK(e) {
    this.setData({ selectedTopK: e.currentTarget.dataset.val });
  },

  submit() {
    if (this.data.loading) return;

    const text = this.data.inputText.trim();
    if (!text) {
      wx.showToast({ title: "请先输入评论", icon: "none" });
      return;
    }

    const reviews = text.split("\n").map(r => r.trim()).filter(r => r.length > 0);
    if (reviews.length === 0) {
      wx.showToast({ title: "评论内容为空", icon: "none" });
      return;
    }

    this.setData({ loading: true, loadingText: "正在分析偏好...", hasResult: false });

    // 模拟loading文字切换
    let step = 0;
    const steps = ["正在分析偏好...", "正在匹配商品...", "生成推荐结果..."];
    const timer = setInterval(() => {
      step = (step + 1) % steps.length;
      this.setData({ loadingText: steps[step] });
    }, 2000);

    wx.cloud.callFunction({
      name: 'recommend',
      data: { reviews, top_k: this.data.selectedTopK },
      success: (res) => {
        clearInterval(timer);
        const data = res.result;
        console.log('云函数返回：', JSON.stringify(res.result));
        if (data.code !== 200) {
          wx.showToast({ title: data.message || "推荐失败", icon: "none" });
          this.setData({ loading: false });
          return;
        }
        const preferences = (data.preferences || []).map(p => ({
          ...p,
          barWidth: Math.round(Math.abs(p.score) * 100),
        }));
        const formatList = (list) => list.map(item => {
          // 找出用户偏好中与该商品最匹配的方面
          let match_aspect = '';
          let match_ratio = '';
          if (preferences && preferences.length > 0) {
            // 取用户最关注的正向方面（score最大的前3个）
            const topPrefs = preferences
              .filter(p => p.positive && p.score > 0.3)
              .slice(0, 3)
              .map(p => p.aspect);
            // 简单取第一个作为展示（实际匹配逻辑在后端）
            if (topPrefs.length > 0) {
              match_aspect = topPrefs[0];
              match_ratio = (item.positive_ratio * 100).toFixed(0);
            }
          }
          return {
            ...item,
            pos_ratio_text: (item.positive_ratio * 100).toFixed(0),
            match_aspect,
            match_ratio,
          };
        });
        this.setData({
          loading: false,
          hasResult: true,
          userCategory: data.user_category || "",
          preferences,
          sameCategory: {
            ...data.same_category,
            list: formatList(data.same_category.list || []),
          },
          crossCategory: {
            ...data.cross_category,
            list: formatList(data.cross_category.list || []),
          },
        });

        // 在 recommend.js 的 success 回调里，setData 之后加入以下代码：

// ── 保存历史记录到本地存储 ──
try {
  const now = new Date();
  const timeStr = now.getFullYear() + '/' +
    String(now.getMonth()+1).padStart(2,'0') + '/' +
    String(now.getDate()).padStart(2,'0') + ' ' +
    String(now.getHours()).padStart(2,'0') + ':' +
    String(now.getMinutes()).padStart(2,'0');

  const record = {
    time: timeStr,
    reviews: reviews,
    user_category: data.user_category || '',
    top_results: (data.cross_category.list || []).slice(0, 5).map(i => ({
      name: i.name,
      cat:  i.cat,
      score: i.score,
    })),
  };

  const raw = wx.getStorageSync('recommend_history') || '[]';
  const history = JSON.parse(raw);
  history.push(record);
  // 最多保留20条
  if (history.length > 20) history.shift();
  wx.setStorageSync('recommend_history', JSON.stringify(history));
} catch (e) {
  console.error('保存历史记录失败', e);
}

        wx.pageScrollTo({ scrollTop: 600, duration: 300 });
      },
      fail: (err) => {
        clearInterval(timer);
        console.error("云函数调用失败", err);
        wx.showToast({ title: "调用失败，请重试", icon: "none" });
        this.setData({ loading: false });
      }
    });
  },

  goRecDetail(e) {
    const item = e.currentTarget.dataset.item;
    wx.navigateTo({
      url: `/pages/detail/detail?sku_id=${encodeURIComponent(item.name)}`
    });
  },

  retry() {
    this.setData({
      hasResult: false,
      inputText: '',
      preferences: [],
      sameCategory: { cat: '', reason: '', list: [] },
      crossCategory: { reason: '', list: [] },
    });
    // 滚回顶部
    wx.pageScrollTo({ scrollTop: 0, duration: 300 });
  },

  onShareAppMessage() {
    const { userCategory, crossCategory } = this.data;
    const top = (crossCategory.list || [])[0];
    const title = top
      ? '我用AI推荐系统找到了「' + top.name + '」，快来试试！'
      : '基于ABSA情感分析的智能商品推荐，输入评论即可获取个性化推荐';
    return {
      title,
      path: '/pages/recommend/recommend',
      imageUrl: '',  // 可设置自定义分享图
    };
  },

  onShareTimeline() {
    return {
      title: '智能商品推荐——输入评论，AI帮你找好货',
      query: '',
    };
  },

});