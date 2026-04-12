App({
  onLaunch() {
    // 初始化云开发
    wx.cloud.init({
      env: 'cloud1-6gjlz08n0e5d4903',
      traceUser: true,
    })

    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    wx.login({
      success: res => {}
    })
  },

  globalData: {
    userInfo: null,
    apiBase: 'http://127.0.0.1:5000'  // 本地测试保留，云函数配好后删掉
  }
})