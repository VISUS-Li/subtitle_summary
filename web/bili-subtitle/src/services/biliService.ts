import axios from 'axios'
import type { CookieForm, VideoResult, SearchResult, BatchResult, Progress } from '@/types/bili'
import { API_CONFIG } from '@/config/api'
import { configService } from './configService'

const API_BASE_URL = API_CONFIG.BILI

function extractBvid(input: string): string {
  if (input.includes('bilibili.com/video/')) {
    const match = input.match(/\/video\/(BV[a-zA-Z0-9]+)/)
    return match ? match[1] : input
  }
  return input
}

export const biliService = {
  async setCookies(cookies: CookieForm) {
    // 分别设置每个cookie配置项
    await Promise.all([
      configService.setServiceConfig('bilibili', 'sessdata', cookies.sessdata),
      configService.setServiceConfig('bilibili', 'bili_jct', cookies.bili_jct),
      configService.setServiceConfig('bilibili', 'buvid3', cookies.buvid3)
    ])
    return { message: 'Cookies设置成功' }
  },

  async getCookies(): Promise<CookieForm | null> {
    try {
      const configs = await configService.getAllConfigs('bilibili')
      // 检查是否获取到所有必需的cookie配置
      const cookies = {
        sessdata: configs.find((c: any) => c.config_key === 'sessdata')?.value,
        bili_jct: configs.find((c: any) => c.config_key === 'bili_jct')?.value,
        buvid3: configs.find((c: any) => c.config_key === 'buvid3')?.value
      }
      
      // 只有当所有cookie值都存在且非空时才返回
      if (cookies.sessdata && cookies.bili_jct && cookies.buvid3) {
        return cookies
      }
      return null  // 任何cookie缺失都返回null
    } catch (error: any) {
      console.error('获取cookies失败:', error)
      return null
    }
  },

  async getVideoTextWithProgress(topic: string, bvid: string, onProgress: (progress: Progress) => void): Promise<{ task_id: string }> {
    try {
      // 使用POST方法并明确设置超时
      const response = await axios.post(
        `${API_BASE_URL}/video/${extractBvid(bvid)}`,
        { topic }, // 确保传递topic
        {
          timeout: 3000, // 明确设置超时

          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      // 立即处理响应
      if (!response.data?.task_id) {
        throw new Error('Invalid response format');
      }
      
      // 立即建立WebSocket连接
      const ws = new WebSocket(`${API_CONFIG.WS_BILI}/${response.data.task_id}`);
      
      return { task_id: response.data.task_id };
    } catch (error) {
      console.error('API request error:', error)
      throw error
    }
  },

  async searchVideos(
    keyword: string,
    page = 1,
    pageSize = 20
  ): Promise<SearchResult[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/search`, {
        params: { 
          keyword, 
          page, 
          page_size: pageSize 
        }
      })
      return response.data
    } catch (error) {
      console.error('搜索视频失败:', error)
      throw error
    }
  },

  async batchProcess(
    topic: string, // 确保topic参数
    keyword: string,
    maxResults = 5
  ): Promise<{ task_id: string }> {
    try {
      const response = await axios.post(`${API_BASE_URL}/batch`, null, {
        params: { 
          topic, // 确保传递topic
          keyword, 
          max_results: maxResults 
        }
      })
      
      if (!response.data?.task_id) {
        throw new Error('Invalid response format')
      }

      // 建立WebSocket连接监听进度
      const ws = new WebSocket(`${API_CONFIG.WS_BILI}/${response.data.task_id}`)
      
      return { task_id: response.data.task_id }
    } catch (error) {
      console.error('批量处理失败:', error)
      throw error
    }
  }
} 