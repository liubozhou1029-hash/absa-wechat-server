// app.js
App({
  onLaunch() {
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    wx.login({
      success: res => {
        // 发送 res.code 到后台换取 openId, sessionKey, unionId
      }
    })
  },

  globalData: {
    userInfo: null,
    // ⚠️ 本地测试用127.0.0.1，部署微信云后改为云函数URL
    apiBase: 'http://127.0.0.1:5000'
  }
})
