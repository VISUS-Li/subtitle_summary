import axios from 'axios'
import type { VideoResult, Progress } from '@/types/bili'
import { API_CONFIG } from '@/config/api'

const API_BASE_URL = `${API_CONFIG.VIDEO}`


export const videoService = {
  async processVideoUrl(url: string, topic: string): Promise<VideoResult> {
    try {
      const response = await axios.post(`${API_BASE_URL}/process`, {
        url: url,
        language: 'zh',
        topic: topic
      })
      return response.data
    } catch (error: any) {
      console.error('处理视频URL失败:', error)
      throw error
    }
  }
} 