<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import type { TabsPaneContext } from 'element-plus'
import { biliService } from '@/services/biliService'
import type { CookieForm, VideoResult, SearchResult, BatchResult } from '@/types/bili'
import ProcessLog from '@/components/ProcessLog.vue'
import type { Progress } from '@/types/bili'
import ConfigPanel from '@/components/ConfigPanel.vue'

const activeTab = ref('single')
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

const getVideoText = async () => {
  try {
    if (!bvid.value) {
      ElMessage.warning('请输入有效的BV号或视频链接')
      return
    }

    loading.value = true
    processLogs.value = [] // 清空之前的日志
    singleResult.value = null // 清空之前的结果
    
    const result = await biliService.getVideoTextWithProgress(
      bvid.value,
      (progress) => {
        // 每收到一条消息就立即更新日志
        processLogs.value.push({
          status: progress.status,
          message: progress.message,
          progress: progress.progress
        })
        
        // 如果任务完成，更新结果
        if (progress.status === 'completed' && progress.result) {
          singleResult.value = progress.result
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
        <!-- 单个视频查询 -->
        <el-tab-pane label="单个视频查询" name="single">
          <div class="search-box">
            <el-input
              v-model="bvid"
              placeholder="请输入BV号或完整视频链接"
              clearable
              class="input-with-select"
            />
            <el-button type="primary" @click="getVideoText" :loading="loading">
              获取字幕
            </el-button>
          </div>
          
          <!-- 添加进度日志组件 -->
          <ProcessLog :logs="processLogs" v-if="processLogs.length > 0" />
          
          <el-card v-if="singleResult" class="result-card">
            <template #header>
              <div class="card-header">
                <span>{{ singleResult.title || singleResult.bvid }}</span>
              </div>
            </template>
            <div class="text-content">{{ singleResult.text }}</div>
          </el-card>
        </el-tab-pane>

        <!-- 添加配置标签页 -->
        <el-tab-pane label="系统配置" name="config">
          <ConfigPanel />
        </el-tab-pane>
      </el-tabs>

      <el-button @click="resetCookies" class="reset-button">
        重置Cookie
      </el-button>
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
</style>
