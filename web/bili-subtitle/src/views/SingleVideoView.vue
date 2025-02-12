<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { videoService } from '@/services/videoService'
import ProcessLog from '@/components/ProcessLog.vue'

const loading = ref(false)
const videoUrl = ref('')
const processLogs = ref<any[]>([])

const handleProcess = async () => {
  if (!videoUrl.value) {
    ElMessage.warning('请填写视频地址')
    return
  }

  try {
    loading.value = true
    processLogs.value = []

    const { task_id } = await videoService.getVideoTextWithProgress(
      'auto',
      videoUrl.value,
      (progress) => {
        processLogs.value.push(progress)
      }
    )

    ElMessage.success('视频处理任务已提交')
  } catch (error: any) {
    ElMessage.error(error.message || '视频处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="single-video-container">
    <div class="content-wrapper">
      <h2 class="page-title">单视频字幕获取</h2>
      
      <el-card class="process-card">
        <el-form label-position="top">
          <el-form-item label="视频地址">
            <el-input
              v-model="videoUrl"
              placeholder="请输入B站或YouTube视频地址"
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
</style> 