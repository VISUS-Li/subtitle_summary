import axios from 'axios'
import type { CookieForm, VideoResult, SearchResult, BatchResult, Progress } from '@/types/bili'
import { API_CONFIG } from '@/config/api'

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
    const response = await axios.post(`${API_BASE_URL}/cookies`, cookies)
    return response.data
  },

  async getCookies(): Promise<CookieForm> {
    const response = await axios.get(`${API_BASE_URL}/cookies`)
    return response.data
  },

  async getVideoTextWithProgress(
    bvid: string,
    progressCallback: (progress: Progress) => void
  ): Promise<VideoResult> {
    console.log('Starting request for BV:', bvid)
    
    try {
      // 首先获取task_id
      const response = await axios.get(`${API_BASE_URL}/video/${extractBvid(bvid)}`)
      const taskId = response.data.task_id
      
      if (!taskId) {
        throw new Error('未获取到任务ID')
      }
      
      console.log('Got task ID:', taskId)
      
      // 创建WebSocket连接
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.hostname}:8000/bili/ws/${taskId}`
      
      return new Promise((resolve, reject) => {
        let reconnectAttempts = 0
        const maxReconnectAttempts = 3
        let lastProgress: Progress | null = null
        
        function connect() {
          const ws = new WebSocket(wsUrl)
          
          ws.onopen = () => {
            console.log('WebSocket connected')
            // 连接建立时发送初始状态
            const initialProgress: Progress = {
              status: 'processing',
              progress: 0,
              message: '已连接到服务器...'
            }
            progressCallback(initialProgress)
          }
          
          ws.onmessage = (event) => {
            const progress: Progress = JSON.parse(event.data)
            console.log('WebSocket message:', progress)
            
            // 检查是否与上一条消息相同
            if (!lastProgress || 
                lastProgress.status !== progress.status || 
                lastProgress.message !== progress.message || 
                Math.abs((lastProgress.progress || 0) - (progress.progress || 0)) >= 1) {
              
              // 更新最后一条消息记录
              lastProgress = progress
              
              // 回调通知前端更新
              progressCallback(progress)
              
              // 处理完成或失败的情况
              if (progress.status === 'completed' && progress.result) {
                resolve(progress.result)
                ws.close()
              } else if (progress.status === 'failed') {
                reject(new Error(progress.message || '处理失败'))
                ws.close()
              }
            }
          }
          
          ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            progressCallback({
              status: 'failed',
              progress: 0,
              message: '连接错误，正在重试...'
            })
            
            if (reconnectAttempts < maxReconnectAttempts) {
              reconnectAttempts++
              setTimeout(connect, 1000 * reconnectAttempts)
            } else {
              reject(error)
            }
          }
          
          ws.onclose = () => {
            console.log('WebSocket connection closed')
          }
        }
        
        connect()
        
        // 添加超时处理
        setTimeout(() => {
          reject(new Error('处理超时'))
        }, 300000) // 5分钟超时
      })
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