import axios from 'axios'
import type { VideoResult, SearchResult, BatchResult, Progress, BatchProcessRequest } from '@/types/bili'
import { API_CONFIG } from '@/config/api'
import { configService } from './configService'

// 提取视频ID的工具函数
const extractVideoId = {
  bilibili(input: string): string {
    if (input.includes('bilibili.com/video/')) {
      const match = input.match(/\/video\/(BV[a-zA-Z0-9]+)/)
      return match ? match[1] : input
    }
    return input
  },

  youtube(input: string): string {
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
  }
}

export const videoService = {
  // B站相关方法
  async setBiliCookies(cookies: CookieForm) {
    await Promise.all([
      configService.setServiceConfig('bilibili', 'sessdata', cookies.sessdata),
      configService.setServiceConfig('bilibili', 'bili_jct', cookies.bili_jct),
      configService.setServiceConfig('bilibili', 'buvid3', cookies.buvid3)
    ])
    return { message: 'Cookies设置成功' }
  },

  async getBiliCookies(): Promise<CookieForm | null> {
    try {
      const configs = await configService.getAllConfigs('bilibili')
      const cookies = {
        sessdata: configs.find((c: any) => c.config_key === 'sessdata')?.value,
        bili_jct: configs.find((c: any) => c.config_key === 'bili_jct')?.value,
        buvid3: configs.find((c: any) => c.config_key === 'buvid3')?.value
      }
      
      return (cookies.sessdata && cookies.bili_jct && cookies.buvid3) ? cookies : null
    } catch (error: any) {
      console.error('获取cookies失败:', error)
      return null
    }
  },

  // 视频处理方法
  async getVideoTextWithProgress(
    platform: 'bilibili' | 'youtube',
    topic: string, 
    videoId: string, 
    onProgress: (progress: Progress) => void
  ): Promise<{ task_id: string }> {
    try {
      const baseUrl = platform === 'bilibili' ? API_CONFIG.BILI : API_CONFIG.YOUTUBE
      const wsUrl = platform === 'bilibili' ? API_CONFIG.WS_BILI : API_CONFIG.WS_YOUTUBE
      const extractedId = platform === 'bilibili' 
        ? extractVideoId.bilibili(videoId)
        : extractVideoId.youtube(videoId)

      const response = await axios.post(
        `${baseUrl}/video/${extractedId}`,
        { topic },
        {
          timeout: 3000,
          headers: { 'Content-Type': 'application/json' }
        }
      )
      
      if (!response.data?.task_id) {
        throw new Error('未获取到任务ID')
      }

      const ws = new WebSocket(`${wsUrl}/${response.data.task_id}`)
      ws.onmessage = (event) => {
        const progress = JSON.parse(event.data)
        onProgress(progress)
      }
      
      return { task_id: response.data.task_id }
    } catch (error) {
      console.error('视频处理请求失败:', error)
      throw error
    }
  },

  // 搜索视频
  async searchVideos(
    platform: 'bilibili' | 'youtube',
    keyword: string,
    page = 1,
    pageSize = 20
  ): Promise<SearchResult[]> {
    try {
      const baseUrl = platform === 'bilibili' ? API_CONFIG.BILI : API_CONFIG.YOUTUBE
      const response = await axios.get(`${baseUrl}/search`, {
        params: { keyword, page, page_size: pageSize }
      })
      return response.data
    } catch (error) {
      console.error('搜索视频失败:', error)
      throw error
    }
  },

  // 批量处理
  async batchProcess(
    platform: 'bilibili' | 'youtube',
    request: BatchProcessRequest
  ): Promise<{ task_id: string }> {
    try {
      const baseUrl = platform === 'bilibili' ? API_CONFIG.BILI : API_CONFIG.YOUTUBE
      const wsUrl = platform === 'bilibili' ? API_CONFIG.WS_BILI : API_CONFIG.WS_YOUTUBE

      const response = await axios.post(`${baseUrl}/batch`, null, {
        params: request
      })
      
      if (!response.data?.task_id) {
        throw new Error('未获取到任务ID')
      }

      const ws = new WebSocket(`${wsUrl}/${response.data.task_id}`)
      
      return { task_id: response.data.task_id }
    } catch (error) {
      console.error('批量处理失败:', error)
      throw error
    }
  }
} 