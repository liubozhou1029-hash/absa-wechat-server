// pages/profile/profile.js
// 历史记录存在本地storage，key: 'recommend_history'
// 每次智能推荐成功后由recommend.js写入

Page({
  data: {
    records: [],
  },

  onShow() {
    // 每次进入页面重新读取，确保数据最新
    this.loadRecords();
  },

  loadRecords() {
    try {
      const raw = wx.getStorageSync('recommend_history') || '[]';
      const records = JSON.parse(raw);
      // 最新的排在前面
      records.reverse();
      this.setData({ records });
    } catch (e) {
      this.setData({ records: [] });
    }
  },

  clearAll() {
    wx.showModal({
      title: '确认清空',
      content: '将删除所有历史记录，无法恢复',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('recommend_history');
          this.setData({ records: [] });
          wx.showToast({ title: '已清空', icon: 'success' });
        }
      }
    });
  }
});
