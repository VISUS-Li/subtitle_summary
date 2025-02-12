<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElTag } from 'element-plus'

const props = defineProps<{
  taskId: string
  wsUrl: string
}>()

const logs = ref<Array<{time: string, level: string, message: string}>>([])
const status = ref<string>('pending')
const ws = ref<WebSocket | null>(null)

const connectWebSocket = () => {
  ws.value = new WebSocket(props.wsUrl)
  
  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'task_update') {
      status.value = data.data.status
    } else if (data.type === 'log') {
      logs.value.push(data.data)
      // 自动滚动到底部
      nextTick(() => {
        const container = document.querySelector('.log-container')
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    }
  }

  ws.value.onerror = (error) => {
    console.error('WebSocket错误:', error)
  }

  ws.value.onclose = () => {
    console.log('WebSocket连接已关闭')
  }
}

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})

const getStatusType = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'processing':
      return 'warning'
    default:
      return 'info'
  }
}

const getLogType = (level: string) => {
  switch (level.toLowerCase()) {
    case 'error':
      return 'danger'
    case 'warning':
      return 'warning'
    case 'info':
    default:
      return 'info'
  }
}
</script>

<template>
  <div class="task-log">
    <div class="status-bar">
      <span class="status-label">任务状态:</span>
      <el-tag :type="getStatusType(status)" size="small">{{ status }}</el-tag>
    </div>
    
    <div class="log-container">
      <div v-for="(log, index) in logs" :key="index" class="log-item">
        <span class="log-time">{{ new Date(log.time).toLocaleTimeString() }}</span>
        <el-tag :type="getLogType(log.level)" size="small" class="log-level">
          {{ log.level }}
        </el-tag>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.task-log {
  margin-top: 20px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
}

.status-bar {
  padding: 10px;
  border-bottom: 1px solid var(--el-border-color-light);
  background-color: var(--el-bg-color-page);
}

.status-label {
  margin-right: 10px;
  color: var(--el-text-color-secondary);
}

.log-container {
  height: 400px;
  overflow-y: auto;
  padding: 10px;
  background-color: var(--el-bg-color);
}

.log-item {
  margin-bottom: 8px;
  font-family: monospace;
  line-height: 1.5;
}

.log-time {
  color: var(--el-text-color-secondary);
  margin-right: 8px;
}

.log-level {
  margin-right: 8px;
}

.log-message {
  white-space: pre-wrap;
  word-break: break-all;
}
</style> 