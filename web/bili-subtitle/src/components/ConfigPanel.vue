<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { configService } from '@/services/configService'
import type { WhisperConfig, SystemConfig } from '@/types/config'
import { WHISPER_MODELS } from '@/types/config'

const whisperConfig = reactive<WhisperConfig>({
  model_name: 'large-v3',
  language: 'zh',
  prompt: ''
})

const systemConfig = reactive<SystemConfig>({
  max_retries: 3,
  retry_delay: 5,
  default_max_results: 5
})

const loading = ref(false)

const loadConfigs = async () => {
  try {
    loading.value = true
    const configs = await configService.getAllConfigs()
    Object.assign(whisperConfig, configs.whisper)
    Object.assign(systemConfig, configs.system)
  } catch (error: any) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const saveWhisperConfig = async () => {
  try {
    loading.value = true
    await configService.setWhisperConfig(whisperConfig)
    ElMessage.success('Whisper配置保存成功')
  } catch (error: any) {
    ElMessage.error('保存失败')
  } finally {
    loading.value = false
  }
}

const saveSystemConfig = async () => {
  try {
    loading.value = true
    await configService.setSystemConfig(systemConfig)
    ElMessage.success('系统配置保存成功')
  } catch (error: any) {
    ElMessage.error('保存失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<template>
  <el-card class="config-panel">
    <template #header>
      <div class="card-header">
        <span>系统配置</span>
      </div>
    </template>

    <el-form label-width="140px">
      <el-divider>Whisper 配置</el-divider>
      
      <el-form-item label="模型">
        <el-select v-model="whisperConfig.model_name" style="width: 100%">
          <el-option
            v-for="model in WHISPER_MODELS"
            :key="model.value"
            :label="model.label"
            :value="model.value"
          >
            <span>{{ model.label }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px">
              内存要求: {{ model.memory }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="语言">
        <el-select v-model="whisperConfig.language" style="width: 100%">
          <el-option label="中文" value="zh" />
          <el-option label="英文" value="en" />
          <el-option label="自动检测" value="auto" />
        </el-select>
      </el-form-item>

      <el-form-item label="提示词">
        <el-input
          v-model="whisperConfig.prompt"
          type="textarea"
          :rows="3"
          placeholder="输入转录提示词"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="saveWhisperConfig" :loading="loading">
          保存 Whisper 配置
        </el-button>
      </el-form-item>

      <el-divider>系统配置</el-divider>

      <el-form-item label="最大重试次数">
        <el-input-number v-model="systemConfig.max_retries" :min="1" :max="10" />
      </el-form-item>

      <el-form-item label="重试延迟(秒)">
        <el-input-number v-model="systemConfig.retry_delay" :min="1" :max="30" />
      </el-form-item>

      <el-form-item label="默认最大结果数">
        <el-input-number
          v-model="systemConfig.default_max_results"
          :min="1"
          :max="20"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="saveSystemConfig" :loading="loading">
          保存系统配置
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.config-panel {
  margin: 20px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style> 