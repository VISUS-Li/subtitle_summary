<script setup lang="ts">
import { ref, watch, nextTick } from 'vue' // 在这里import nextTick
import type { Progress } from '@/types/bili'

const props = defineProps<{
  logs: Progress[]
}>()

const scrollRef = ref<HTMLDivElement>()

// 监听日志变化，自动滚动到底部
watch(() => props.logs.length, () => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
})

// 格式化进度显示
const formatProgress = (progress: number) => {
  return progress ? `${Math.round(progress)}%` : '0%'
}

// 获取状态标签类型
const getStatusType = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'downloading':
    case 'transcribing':
      return 'warning'
    default:
      return 'info'
  }
}
</script>

<template>
  <div class="process-log" ref="scrollRef">
    <div v-for="(log, index) in logs" :key="index" class="log-item">
      <el-tag 
        :type="getStatusType(log.status)"
        size="small"
      >
        {{ log.status }}
      </el-tag>
      <span class="log-message">{{ log.message }}</span>
      <el-progress
        v-if="log.progress !== undefined && ['downloading', 'transcribing'].includes(log.status)"
        :percentage="Math.round(log.progress)"
        :status="log.status === 'failed' ? 'exception' : undefined"
        :stroke-width="15"
        class="log-progress"
      />
    </div>
  </div>
</template>

<style scoped>
.process-log {
  height: 200px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background: #f5f7fa;
  margin: 10px 0;
}

.log-item {
  margin-bottom: 8px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-message {
  flex: 1;
  color: #606266;
}

.log-progress {
  width: 150px;
}
</style> 