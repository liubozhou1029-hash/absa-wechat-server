// pages/index/index.js
Page({
  goRecommend() {
    wx.navigateTo({ url: '/pages/recommend/recommend' });
  },
  goData() {
    wx.navigateTo({ url: '/pages/phones/phones' });
  },
  goEmotion() {
    wx.navigateTo({ url: '/pages/sentiment/sentiment' });
  },
  goProfile() {
    wx.navigateTo({ url: '/pages/profile/profile' });
  }
});
