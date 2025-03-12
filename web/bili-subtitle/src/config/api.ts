// API基础地址配置
const BASE_URL = `${window.location.protocol}//${window.location.hostname}:3200`
const WS_BASE_URL = `${BASE_URL.replace('http', 'ws')}`

export const API_CONFIG = {
  CONFIG: `${BASE_URL}/config`,
  BILI: `${BASE_URL}/bili`,
  YOUTUBE: `${BASE_URL}/youtube`,
  XIAOYUZHOU: `${BASE_URL}/xiaoyuzhou`, // 添加小宇宙API
  WS_BILI: `${WS_BASE_URL}/bili/ws`,
  WS_YOUTUBE: `${WS_BASE_URL}/youtube/ws`,
  WS_XIAOYUZHOU: `${WS_BASE_URL}/xiaoyuzhou/ws`, // 添加小宇宙WebSocket
  VIDEO: `${BASE_URL}/video`,
  HISTORY: `${BASE_URL}/history`,
}

export default API_CONFIG