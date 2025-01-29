import axios from 'axios'
import type { VideoResult, SearchResult, BatchResult, Progress } from '@/types/bili'
import { API_CONFIG } from '@/config/api'

const API_BASE_URL = API_CONFIG.YOUTUBE

export const youtubeService = {
  extractVideoId(input: string): string {
    const urlPattern = /^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/
    const urlMatch = input.match(urlPattern)
    if (urlMatch) {
      return urlMatch[1]
    }
    
    const idPattern = /^[a-zA-Z0-9_-]{11}$/
    if (idPattern.test(input)) {
      return input
    }
    
    throw new Error('无效的 YouTube 视频 URL 或 ID')
  },

  async getVideoTextWithProgress(videoId: string, onProgress: (progress: Progress) => void): Promise<{ task_id: string }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/video/${this.extractVideoId(videoId)}`,
        {},
        {
          timeout: 3000,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      )
      
      if (!response.data?.task_id) {
        throw new Error('未获取到任务ID')
      }

      const ws = new WebSocket(`${API_CONFIG.WS_YOUTUBE}/${response.data.task_id}`)
      
      ws.onmessage = (event) => {
        const progress = JSON.parse(event.data)
        onProgress(progress)
      }
      
      return response.data
    } catch (error) {
      console.error('YouTube API请求错误:', error)
      throw error
    }
  },

  async searchVideos(
    keyword: string,
    page = 1,
    pageSize = 20
  ): Promise<SearchResult[]> {
    const response = await axios.get(`${API_BASE_URL}/search`, {
      params: { keyword, page, page_size: pageSize }
    })
    return response.data
  },

  async batchProcess(
    keyword: string,
    maxResults = 5
  ): Promise<BatchResult[]> {
    const response = await axios.get(`${API_BASE_URL}/batch`, {
      params: { keyword, max_results: maxResults }
    })
    return response.data
  }
} 