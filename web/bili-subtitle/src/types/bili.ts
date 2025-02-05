export interface CookieForm {
  sessdata: string
  bili_jct: string
  buvid3: string
}

export interface VideoResult {
  title?: string
  bvid?: string
  id?: string
  platform: string
  subtitle?: string
  summary?: string
  text?: string
}

export interface SearchResult {
  title: string
  author: string
  duration: string
  play_count?: number
  bvid?: string
  id?: string
}

export interface BatchResult {
  title: string
  type: string
  text: string
  bvid?: string
  id?: string
}

export interface Progress {
  status: string
  progress: number
  message: string
  result?: any
  error?: string
}