import axios from 'axios'
import API_CONFIG from '@/config/api'

// 更新 API_CONFIG
const HISTORY_API = `${API_CONFIG.HISTORY}`

export interface HistoryParams {
  keyword?: string
  topic?: string
  platform?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
  sortField?: string
  sortOrder?: 'asc' | 'desc'
}
export interface KeywordResponse {
  search_keywords: string[];
  topics: string[];
}

export const historyApi = {
  // 获取视频历史
  getVideoHistory: (params: HistoryParams) => {
    return axios.get(`${HISTORY_API}/videos`, { params })
  },

  // 获取字幕历史
  getSubtitleHistory: (params: HistoryParams) => {
    return axios.get(`${HISTORY_API}/subtitles`, { params })
  },

  // 获取总结历史
  getSummaryHistory: (params: HistoryParams) => {
    return axios.get(`${HISTORY_API}/summaries`, { params })
  },

  // 获取脚本历史
  getScriptHistory: (params: HistoryParams) => {
    return axios.get(`${HISTORY_API}/scripts`, { params })
  },

  // 全局搜索
  searchAll: (params: HistoryParams) => {
    return axios.get(`${HISTORY_API}/search`, { params })
  },

  // 获取关键词列表
  getKeywords: () => {
    return axios.get<KeywordResponse>(`${HISTORY_API}/keywords`)
  },

  // 获取视频详情
  getVideoDetail: (videoId: string) => {
    return axios.get(`${HISTORY_API}/videos/${videoId}`)
  }
} 