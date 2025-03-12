<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { videoService } from '@/services/videoService'
import ProcessLog from '@/components/ProcessLog.vue'

const loading = ref(false)
const videoUrl = ref('')
const processLogs = ref<any[]>([])
const platform = ref('auto')

const platformOptions = [
  { label: '自动检测', value: 'auto' },
  { label: 'B站', value: 'bilibili' },
  { label: 'YouTube', value: 'youtube' },
  { label: '小宇宙', value: 'xiaoyuzhou' }
]

const handleProcess = async () => {
  if (!videoUrl.value) {
    ElMessage.warning('请填写视频/播客地址')
    return
  }

  try {
    loading.value = true
    processLogs.value = []

    if (platform.value === 'xiaoyuzhou') {
      const { task_id } = await videoService.processPodcast(
        videoUrl.value,
        (progress) => {
          processLogs.value.push(progress)
        }
      )
    } else {
      const { task_id } = await videoService.getVideoTextWithProgress(
        platform.value as any,
        videoUrl.value,
        (progress) => {
          processLogs.value.push(progress)
        }
      )
    }

    ElMessage.success('处理任务已提交')
  } catch (error: any) {
    ElMessage.error(error.message || '处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="single-video-container">
    <div class="content-wrapper">
      <h2 class="page-title">单视频/播客字幕获取</h2>
      
      <el-card class="process-card">
        <el-form label-position="top">
          <el-form-item label="平台">
            <el-select v-model="platform" class="platform-select">
              <el-option
                v-for="option in platformOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="视频/播客地址">
            <el-input
              v-model="videoUrl"
              :placeholder="platform === 'xiaoyuzhou' ? '请输入小宇宙播客地址' : '请输入B站或YouTube视频地址'"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              @click="handleProcess"
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
.single-video-container {
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

:deep(.el-input__wrapper) {
  background-color: var(--el-input-bg-color, var(--el-bg-color-overlay));
}

.platform-select {
  width: 100%;
}
</style>