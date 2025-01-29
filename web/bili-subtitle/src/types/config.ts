export interface WhisperConfig {
  model_name: string
  language: string
  prompt: string
}

export interface SystemConfig {
  max_retries: number
  retry_delay: number
  default_max_results: number
}

export const WHISPER_MODELS = [
  { label: 'Tiny (75MB)', value: 'tiny', memory: '1GB' },
  { label: 'Base (142MB)', value: 'base', memory: '1GB' },
  { label: 'Small (472MB)', value: 'small', memory: '2GB' },
  { label: 'Medium (1.5GB)', value: 'medium', memory: '4GB' },
  { label: 'Large-v3 (3.1GB)', value: 'large-v3', memory: '8GB' }
]

export interface ServiceConfig {
  service_name: string
  config_key: string
  value: any
  description?: string
  is_encrypted: boolean
  created_at: string
  updated_at: string
}

export interface ConfigGroup {
  serviceName: string
  configs: ServiceConfig[]
} 