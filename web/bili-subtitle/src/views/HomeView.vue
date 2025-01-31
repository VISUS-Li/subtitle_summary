<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import type { TabsPaneContext } from 'element-plus'
import { biliService } from '@/services/biliService'
import type { CookieForm, VideoResult, SearchResult, BatchResult } from '@/types/bili'
import ProcessLog from '@/components/ProcessLog.vue'
import type { Progress } from '@/types/bili'
import ConfigPanel from '@/components/ConfigPanel.vue'
import { youtubeService } from '@/services/youtubeService'
import { API_CONFIG } from '@/config/api'

const activeTab = ref('bilibili')
const isCookieSet = ref(false)
const loading = ref(false)

const cookieForm = reactive<CookieForm>({
  sessdata: '',
  bili_jct: '',
  buvid3: ''
})

const bvid = ref('')
const keyword = ref('')
const maxResults = ref(5)
const searchResults = ref<SearchResult[]>([])
const singleResult = ref<VideoResult | null>(null)
const batchResults = ref<BatchResult[]>([])

// 添加进度日志状态
const processLogs = ref<Progress[]>([])
const biliLogs = ref<Progress[]>([])
const youtubeLogs = ref<Progress[]>([])
const biliResult = ref<VideoResult | null>(null)
const youtubeResult = ref<VideoResult | null>(null)

const youtubeId = ref('')

// 添加 YouTube 相关的状态
const youtubeSearchResults = ref<SearchResult[]>([])
const youtubeMaxResults = ref(5)
const youtubeKeyword = ref('')
const youtubeBatchResults = ref<BatchResult[]>([])

const loadServiceConfig = async () => {
  try {
    const cookies = await biliService.getCookies()
    Object.assign(cookieForm, cookies)
    isCookieSet.value = true
  } catch (error) {
    console.log('No stored cookies found')
    isCookieSet.value = false
  }
}

const setCookies = async () => {
  try {
    loading.value = true
    await biliService.setCookies(cookieForm)
    isCookieSet.value = true
    ElMessage.success('Cookie设置成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '设置失败')
  } finally {
    loading.value = false
  }
}

const resetCookies = () => {
  isCookieSet.value = false
  cookieForm.sessdata = ''
  cookieForm.bili_jct = ''
  cookieForm.buvid3 = ''
}

const getVideoText = async (platform: 'bilibili' | 'youtube') => {
  try {
    const videoId = platform === 'bilibili' ? bvid.value : youtubeId.value
    if (!videoId) {
      ElMessage.warning(`请输入有效的${platform === 'bilibili' ? 'BV号' : 'YouTube视频ID'}或视频链接`)
      return
    }

    loading.value = true
    // 清空对应平台的日志和结果
    if (platform === 'bilibili') {
      biliLogs.value = []
      biliResult.value = null
    } else {
      youtubeLogs.value = []
      youtubeResult.value = null
    }
    
    // 根据平台选择服务
    const service = platform === 'bilibili' ? biliService : youtubeService
    const result = await service.getVideoTextWithProgress(
      videoId,
      (progress) => {
        // 更新对应平台的日志
        const logs = platform === 'bilibili' ? biliLogs : youtubeLogs
        logs.value.push({
          status: progress.status,
          message: progress.message,
          progress: progress.progress
        })
        
        // 如果任务完成，更新对应平台的结果
        if (progress.status === 'completed' && progress.result) {
          if (platform === 'bilibili') {
            biliResult.value = progress.result
          } else {
            youtubeResult.value = progress.result
          }
          ElMessage.success('获取成功')
        } else if (progress.status === 'failed') {
          ElMessage.error(progress.message || '处理失败')
        }
      }
    )
  } catch (error: any) {
    ElMessage.error(error.message || '获取视频字幕失败')
  } finally {
    loading.value = false
  }
}

const searchVideos = async () => {
  try {
    loading.value = true
    if (!keyword.value) {
      ElMessage.warning('请输入关键词')
      return
    }
    
    searchResults.value = await biliService.searchVideos(keyword.value)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搜索失败')
  } finally {
    loading.value = false
  }
}

const searchAndTranscribe = async () => {
  try {
    loading.value = true
    if (!keyword.value) {
      ElMessage.warning('请输入关键词')
      return
    }
    
    batchResults.value = await biliService.batchProcess(keyword.value, maxResults.value)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '处理失败')
  } finally {
    loading.value = false
  }
}

// 修改批量处理方法
const searchAndTranscribeYoutube = async () => {
  try {
    loading.value = true
    if (!youtubeKeyword.value) {
      ElMessage.warning('请输入关键词')
      return
    }
    
    const { task_id } = await youtubeService.batchProcess(
      youtubeKeyword.value, 
      youtubeMaxResults.value
    )
    
    // 建立WebSocket连接监听进度
    const ws = new WebSocket(`${API_CONFIG.WS_YOUTUBE}/${task_id}`)
    
    ws.onmessage = (event) => {
      const progress = JSON.parse(event.data)
      youtubeLogs.value.push(progress)
      
      if (progress.result?.videos) {
        youtubeBatchResults.value = progress.result.videos
      }
    }
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '处理失败')
  } finally {
    loading.value = false
  }
}

// 修改搜索方法
const searchYoutubeVideos = async () => {
  try {
    loading.value = true
    if (!youtubeKeyword.value) {
      ElMessage.warning('请输入关键词')
      return
    }
    
    youtubeSearchResults.value = await youtubeService.searchVideos(
      youtubeKeyword.value,
      1,  // page
      20  // pageSize
    )
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搜索失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadServiceConfig()
})
</script>

<template>
  <div class="container">
    <div class="header">
      <h1>Bili2Text</h1>
      <p>B站视频字幕获取工具</p>
    </div>

    <!-- Cookie设置表单 -->
    <el-card class="cookie-form" v-if="!isCookieSet">
      <template #header>
        <div class="card-header">
          <span>设置B站Cookie</span>
        </div>
      </template>
      <el-form :model="cookieForm" label-width="100px">
        <el-form-item label="SESSDATA">
          <el-input v-model="cookieForm.sessdata" />
        </el-form-item>
        <el-form-item label="bili_jct">
          <el-input v-model="cookieForm.bili_jct" />
        </el-form-item>
        <el-form-item label="buvid3">
          <el-input v-model="cookieForm.buvid3" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="setCookies">设置Cookie</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 主要功能区 -->
    <template v-else>
      <el-tabs v-model="activeTab">
        <!-- B站视频查询 -->
        <el-tab-pane label="B站视频查询" name="bilibili">
          <div class="search-box">
            <el-input
              v-model="bvid"
              placeholder="请输入BV号或完整视频链接"
              clearable
              class="input-with-select"
            />
            <el-button type="primary" @click="getVideoText('bilibili')" :loading="loading">
              获取字幕
            </el-button>
          </div>
          
          <!-- B站进度日志 -->
          <ProcessLog :logs="biliLogs" v-if="biliLogs.length > 0" />
          
          <el-card v-if="biliResult" class="result-card">
            <template #header>
              <div class="card-header">
                <span>{{ biliResult.title || biliResult.bvid }}</span>
              </div>
            </template>
            <div class="text-content">{{ biliResult.text }}</div>
          </el-card>
        </el-tab-pane>

        <!-- YouTube视频查询 -->
        <el-tab-pane label="YouTube视频查询" name="youtube">
          <div class="search-box">
            <el-input
              v-model="youtubeId"
              placeholder="请输入YouTube视频ID或完整链接"
              clearable
              class="input-with-select"
            />
            <el-button type="primary" @click="getVideoText('youtube')" :loading="loading">
              获取字幕
            </el-button>
          </div>
          
          <!-- YouTube进度日志 -->
          <ProcessLog :logs="youtubeLogs" v-if="youtubeLogs.length > 0" />
          
          <el-card v-if="youtubeResult" class="result-card">
            <template #header>
              <div class="card-header">
                <span>{{ youtubeResult.title || youtubeResult.id }}</span>
              </div>
            </template>
            <div class="text-content">{{ youtubeResult.text }}</div>
          </el-card>

          <!-- 添加搜索功能 -->
          <el-divider>搜索视频</el-divider>
          <div class="search-box">
            <el-input
              v-model="youtubeKeyword"
              placeholder="请输入搜索关键词"
              clearable
              class="input-with-select"
            />
            <el-button type="primary" @click="searchYoutubeVideos" :loading="loading">
              搜索
            </el-button>
          </div>

          <!-- 搜索结果列表 -->
          <el-table
            v-if="youtubeSearchResults.length > 0"
            :data="youtubeSearchResults"
            style="width: 100%"
          >
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="author" label="作者" width="180" />
            <el-table-column prop="duration" label="时长" width="100" />
            <el-table-column fixed="right" label="操作" width="120">
              <template #default="scope">
                <el-button
                  link
                  type="primary"
                  @click="youtubeId = scope.row.id; getVideoText('youtube')"
                >
                  获取字幕
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 批量处理功能 -->
          <el-divider>批量处理</el-divider>
          <div class="batch-box">
            <el-input
              v-model="youtubeKeyword"
              placeholder="请输入搜索关键词"
              clearable
              class="input-with-select"
            />
            <el-input-number
              v-model="youtubeMaxResults"
              :min="1"
              :max="200"
              placeholder="最大结果数"
            />
            <el-button type="primary" @click="searchAndTranscribeYoutube" :loading="loading">
              批量处理
            </el-button>
          </div>

          <!-- 批量处理结果 -->
          <el-table
            v-if="youtubeBatchResults.length > 0"
            :data="youtubeBatchResults"
            style="width: 100%"
          >
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="text" label="文本内容">
              <template #default="scope">
                <div class="text-preview">{{ scope.row.text }}</div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 系统配置标签页 -->
        <el-tab-pane label="系统配置" name="config">
          <ConfigPanel />
        </el-tab-pane>
      </el-tabs>

    </template>
  </div>
</template>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  margin-bottom: 20px;
  text-align: center;
}

.cookie-form {
  max-width: 600px;
  margin: 0 auto;
}

.search-box {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.input-with-select {
  width: 400px;
}

.result-card {
  margin-bottom: 15px;
}

.text-content {
  white-space: pre-wrap;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-top: 10px;
}

.reset-button {
  margin-top: 20px;
}

.batch-box {
  display: flex;
  gap: 10px;
  margin: 20px 0;
  align-items: center;
}

.text-preview {
  max-height: 100px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.el-input-number {
  width: 150px;
}
</style>
