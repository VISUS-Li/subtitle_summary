// API基础地址配置
const BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`
const WS_BASE_URL = `${BASE_URL.replace('http', 'ws')}`

export const API_CONFIG = {
  CONFIG: `${BASE_URL}/config`,
  BILI: `${BASE_URL}/bili`,
  YOUTUBE: `${BASE_URL}/youtube`,
  WS_BILI: `${WS_BASE_URL}/bili/ws`,
  WS_YOUTUBE: `${WS_BASE_URL}/youtube/ws`,
  VIDEO: `${BASE_URL}/video`,
}

export default API_CONFIG 