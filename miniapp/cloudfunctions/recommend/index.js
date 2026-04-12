const cloud = require('wx-server-sdk')
const axios = require('axios')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

// ⚠️ 每次cpolar重启后这里的URL会变，需要更新
const FLASK_URL = 'https://1a5a5086.r28.cpolar.top'

exports.main = async (event, context) => {
  try {
    const response = await axios.post(`${FLASK_URL}/recommend`, {
      reviews: event.reviews,
      top_k: event.top_k || 10
    }, {
      timeout: 120000
    })
    return response.data
  } catch (err) {
    return {
      code: 500,
      message: '推荐服务暂时不可用：' + err.message
    }
  }
}