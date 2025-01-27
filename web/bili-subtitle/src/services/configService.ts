import axios from 'axios'
import type { WhisperConfig, SystemConfig } from '@/types/config'
import { API_CONFIG } from '@/config/api'

const API_BASE_URL = API_CONFIG.CONFIG

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

  async getAllConfigs() {
    const response = await axios.get(`${API_BASE_URL}/all`)
    return response.data
  }
} 