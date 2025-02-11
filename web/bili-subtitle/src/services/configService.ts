import axios from 'axios'
import type { WhisperConfig, SystemConfig } from '@/types/config'
import { API_CONFIG } from '@/config/api'

const API_BASE_URL = API_CONFIG.CONFIG

export interface ConfigItem {
  service_name: string
  config_key: string
  value: any
  description: string | null
  category: string
  created_at: string
  updated_at: string
}

interface ConfigDetail {
  value: any;
  description: string | null;
  category: string | null;
  updated_at: string | null;
}

export const configService = {
  async getSystemConfig(): Promise<SystemConfig> {
    const response = await axios.get(`${API_BASE_URL}/system`)
    return response.data
  },

  async setSystemConfig(config: SystemConfig) {
    const response = await axios.post(`${API_BASE_URL}/system`, config)
    return response.data
  },

  async getWhisperConfig(): Promise<WhisperConfig> {
    const response = await axios.get(`${API_BASE_URL}/whisper`)
    return response.data
  },

  async setWhisperConfig(config: WhisperConfig) {
    const response = await axios.post(`${API_BASE_URL}/whisper`, config)
    return response.data
  },

  async getAllConfigs(serviceName: string): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/services/${serviceName}`)
      return response.data || []  // 确保返回空数组而不是null
    } catch (error: any) {
      console.error(`获取${serviceName}配置失败:`, error)
      return []  // 发生错误时返回空数组
    }
  },

  async getServiceConfigs(serviceName: string): Promise<Record<string, ConfigDetail>> {
    const response = await axios.get(`${API_BASE_URL}/services/${serviceName}`)
    return response.data.configs || {}
  },

  async getCategoryConfigs(category: string): Promise<Record<string, Record<string, any>>> {
    const response = await axios.get(`${API_BASE_URL}/categories/${category}`)
    return response.data.configs || {}
  },

  async setServiceConfig(
    serviceName: string,
    configKey: string,
    value: any,
    description?: string
  ): Promise<void> {
    await axios.post(`${API_BASE_URL}/set`, {
      service_name: serviceName,
      config_key: configKey,
      value,
      description
    })
  },

  async getServiceConfig(serviceName: string, key: string): Promise<any> {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/services/${serviceName}/${key}`
      )
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null  // 配置不存在时返回null
      }
      throw error  // 其他错误继续抛出
    }
  },

  async getAllCategories(): Promise<string[]> {
    const response = await axios.get(`${API_BASE_URL}/categories`)
    return response.data.categories || []
  }
} 