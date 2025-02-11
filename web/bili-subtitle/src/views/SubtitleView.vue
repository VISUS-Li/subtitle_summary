<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { BatchProcessRequest } from '@/types/bili'
import { PlatformChoice } from '@/types/bili'
import ProcessLog from '@/components/ProcessLog.vue'
import { videoService } from '@/services/videoService'

const loading = ref(false)
const topic = ref('')
const keyword = ref('')
const maxResults = ref(20)
const selectedPlatform = ref<PlatformChoice>(PlatformChoice.ALL)
const processLogs = ref<any[]>([])

const handleBatchProcess = async () => {
  if (!topic.value || !keyword.value) {
    ElMessage.warning('请填写完整的主题和关键词')
    return
  }

  try {
    loading.value = true
    processLogs.value = []

    const request: BatchProcessRequest = {
      topic: topic.value,
      keyword: keyword.value,
      max_results: maxResults.value,
      platform_choice: selectedPlatform.value
    }

    const { task_id } = await videoService.batchProcess(
      selectedPlatform.value === PlatformChoice.BILIBILI ? 'bilibili' : 'youtube',
      request
    )
    
    // 可以根据需要处理返回的 task_id
    ElMessage.success('批量处理任务已提交')
  } catch (error: any) {
    ElMessage.error(error.message || '批量处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="subtitle-container">
    <div class="content-wrapper">
      <h2 class="page-title">批量字幕总结</h2>
      
      <el-card class="process-card">
        <el-form label-position="top">
          <el-form-item label="主题描述">
            <el-input
              v-model="topic"
              placeholder="请输入主题描述，例如：游戏解说、美食制作等"
            />
          </el-form-item>

          <el-form-item label="关键词">
            <el-input
              v-model="keyword"
              placeholder="请输入搜索关键词"
            />
          </el-form-item>

          <el-form-item label="处理平台">
            <el-select v-model="selectedPlatform" placeholder="选择平台" class="platform-select">
              <el-option
                v-for="platform in Object.values(PlatformChoice)"
                :key="platform"
                :label="platform"
                :value="platform"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="最大结果数">
            <el-input-number
              v-model="maxResults"
              :min="1"
              :max="200"
              :step="10"
              class="max-results-input"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              @click="handleBatchProcess"
              :loading="loading"
              class="submit-button"
            >
              开始处理
            </el-button>
          </el-form-item>
        </el-form>

        <ProcessLog
          v-if="processLogs.length > 0"
          :logs="processLogs"
          class="process-log"
        />
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.subtitle-container {
  width: 100%;
  min-height: calc(100vh - 60px);
  padding: 20px;
  display: flex;
  justify-content: center;
}

.content-wrapper {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  margin-bottom: 24px;
  color: var(--el-text-color-primary);
}

.process-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
}

.platform-select {
  width: 100%;
}

.max-results-input {
  width: 180px;
}

.submit-button {
  width: 100%;
  margin-top: 16px;
}

.process-log {
  margin-top: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  background-color: var(--el-input-bg-color, var(--el-bg-color-overlay));
}
</style> 