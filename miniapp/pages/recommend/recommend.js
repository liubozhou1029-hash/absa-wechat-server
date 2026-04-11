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

    wx.request({
      url: `${app.globalData.apiBase}/recommend`,
      method: "POST",
      header: { "Content-Type": "application/json" },
      data: { reviews, top_k: this.data.selectedTopK },
      timeout: 120000, // ABSA推理较慢，2分钟超时
      success: (res) => {
        clearInterval(timer);
        const data = res.data;
        if (data.code !== 200) {
          wx.showToast({ title: data.message || "推荐失败", icon: "none" });
          this.setData({ loading: false });
          return;
        }

        // 处理偏好展示数据（加上进度条宽度）
        const preferences = (data.preferences || []).map(p => ({
          ...p,
          barWidth: Math.round(Math.abs(p.score) * 100),
        }));

        // 处理推荐列表（加格式化字段）
        const formatList = (list) => list.map(item => ({
          ...item,
          pos_ratio_text: (item.positive_ratio * 100).toFixed(0),
        }));

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

        // 滚动到结果区
        wx.pageScrollTo({ scrollTop: 600, duration: 300 });
      },
      fail: (err) => {
        clearInterval(timer);
        console.error("请求失败", err);
        wx.showToast({ title: "网络错误，请检查后端服务", icon: "none" });
        this.setData({ loading: false });
      }
    });
  },

  goRecDetail(e) {
    const item = e.currentTarget.dataset.item;
    // 将商品信息传到详情页
    wx.navigateTo({
      url: `/pages/rec_detail/rec_detail?name=${encodeURIComponent(item.name)}&cat=${item.cat}&score=${item.score}`
    });
  }
});
