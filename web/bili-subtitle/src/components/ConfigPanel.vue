<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElUpload } from 'element-plus'
import { configService } from '@/services/configService'
import type { WhisperConfig, SystemConfig } from '@/types/config'
import { WHISPER_MODELS } from '@/types/config'
import type { UploadProps } from 'element-plus'

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

// 添加 cookies 配置
const biliCookies = reactive({
  sessdata: '',
  bili_jct: '',
  buvid3: ''
})

// 修改 YouTube cookies 的响应式对象，使用 Map 来存储所有 cookie
const youtubeCookies = reactive(new Map<string, string>())

// 移除 showPasswords，因为我们默认显示所有值
const showValues = ref(true)

const loadConfigs = async () => {
  try {
    loading.value = true
    const configs = await configService.getAllConfigs('system')
    if (configs && configs.length > 0) {
      Object.assign(systemConfig, configs.reduce((acc: any, curr: any) => {
        acc[curr.config_key] = curr.value
        return acc
      }, {} as SystemConfig))
    } else {
      // 使用默认配置
      Object.assign(systemConfig, {
        max_retries: 3,
        retry_delay: 5,
        default_max_results: 5
      })
    }
  } catch (error: any) {
    ElMessage.error('加载系统配置失败，将使用默认配置')
    // 使用默认配置
    Object.assign(systemConfig, {
      max_retries: 3,
      retry_delay: 5,
      default_max_results: 5
    })
  } finally {
    loading.value = false
  }
}

const loadWhisperConfigs = async () => {
  try {
    loading.value = true
    const configs = await configService.getAllConfigs('whisper')
    if (configs && configs.length > 0) {
      Object.assign(whisperConfig, configs.reduce((acc: any, curr: any) => {
        acc[curr.config_key] = curr.value
        return acc
      }, {} as WhisperConfig))
    } else {
      // 使用默认配置
      Object.assign(whisperConfig, {
        model_name: 'large-v3',
        language: 'zh',
        prompt: ''
      })
    }
  } catch (error: any) {
    ElMessage.error('加载Whisper配置失败，将使用默认配置')
    // 使用默认配置
    Object.assign(whisperConfig, {
      model_name: 'large-v3',
      language: 'zh',
      prompt: ''
    })
  } finally {
    loading.value = false
  }
}

const loadCookiesConfig = async () => {
  try {
    loading.value = true
    
    // 加载 Bilibili cookies
    const biliConfigs = await configService.getAllConfigs('bilibili')
    if (biliConfigs && biliConfigs.length > 0) {
      biliConfigs.forEach((config: any) => {
        if (config.config_key in biliCookies) {
          biliCookies[config.config_key as keyof typeof biliCookies] = config.value || ''
        }
      })
    }
    
    // 加载 YouTube cookies
    const youtubeConfig = await configService.getServiceConfig('youtube', 'cookie_data')
    if (youtubeConfig?.value) {
      const cookies = parseCookieFile(youtubeConfig.value)
      youtubeCookies.clear()
      cookies.forEach((value, key) => {
        youtubeCookies.set(key, value)
      })
    }
  } catch (error: any) {
    ElMessage.error('加载Cookies配置失败')
  } finally {
    loading.value = false
  }
}

const saveConfig = async (type: 'system' | 'whisper') => {
  try {
    loading.value = true
    const config = type === 'system' ? systemConfig : whisperConfig
    const promises = Object.entries(config).map(([key, value]) =>
      configService.setServiceConfig(type, key, value)
    )
    
    await Promise.all(promises)
    ElMessage.success(`${type.charAt(0).toUpperCase() + type.slice(1)}配置保存成功`)
  } catch (error: any) {
    console.error(`${type.charAt(0).toUpperCase() + type.slice(1)}配置保存失败:`, error)
    ElMessage.error(`${type.charAt(0).toUpperCase() + type.slice(1)}配置保存失败`)
  } finally {
    loading.value = false
  }
}

const saveCookiesConfig = async (platform: 'bilibili' | 'youtube') => {
  try {
    loading.value = true
    if (platform === 'bilibili') {
      const promises = Object.entries(biliCookies).map(([key, value]) =>
        configService.setServiceConfig(platform, key, value, undefined, true)
      )
      await Promise.all(promises)
    } else {
      // YouTube cookies现在通过文件上传处理，这里可以保留为空
      // 或者添加其他YouTube相关的配置保存
    }
    
    ElMessage.success(`${platform === 'bilibili' ? 'Bilibili' : 'YouTube'} Cookies保存成功`)
  } catch (error: any) {
    ElMessage.error(`${platform === 'bilibili' ? 'Bilibili' : 'YouTube'} Cookies保存失败`)
  } finally {
    loading.value = false
  }
}

// 修改解析 cookie 文件的方法
const parseCookieFile = (content: string) => {
  const cookies = new Map<string, string>()
  const lines = content.split('\n')
  
  lines.forEach(line => {
    // 跳过注释和空行
    if (line.startsWith('#') || !line.trim()) return
    
    const parts = line.split('\t')
    if (parts.length >= 7) {
      const [domain, , , , , name, value] = parts
      // 只处理 youtube.com 域名的 cookies
      if (domain.includes('youtube.com')) {
        cookies.set(name, value)
      }
    }
  })
  
  return cookies
}

// 修改处理文件上传的方法
const handleFileUpload = async (uploadFile: any) => {
  const file = uploadFile.raw
  if (!file) {
    ElMessage.error('文件上传失败')
    return false
  }

  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const content = e.target?.result as string
      
      // 直接保存完整的cookie文件内容
      await configService.setServiceConfig(
        'youtube',
        'cookie_data',
        content,
        'YouTube cookies configuration file',
        true
      )
      
      // 解析cookie内容用于显示
      const cookies = parseCookieFile(content)
      youtubeCookies.clear()
      cookies.forEach((value, key) => {
        youtubeCookies.set(key, value)
      })
      
      ElMessage.success('Cookie 文件保存成功')
    } catch (error) {
      console.error('Cookie 文件保存失败:', error)
      ElMessage.error('Cookie 文件保存失败')
    }
  }
  reader.readAsText(file)
  return false
}

// 更新单个 cookie 值
const updateYoutubeCookie = (key: string, value: string) => {
  youtubeCookies.set(key, value)
}

onMounted(() => {
  loadConfigs()
  loadWhisperConfigs()
  loadCookiesConfig()
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
        <el-button type="primary" @click="saveConfig('whisper')" :loading="loading">
          保存 Whisper 配置
        </el-button>
      </el-form-item>

      <el-divider>Cookies 配置</el-divider>
      
      <!-- Bilibili Cookies -->
      <el-collapse>
        <el-collapse-item title="Bilibili Cookies 配置" name="bili-cookies">
          <el-form-item label="SESSDATA">
            <el-input 
              v-model="biliCookies.sessdata" 
              type="password" 
              show-password 
              placeholder="输入 SESSDATA"
            />
          </el-form-item>
          <el-form-item label="bili_jct">
            <el-input 
              v-model="biliCookies.bili_jct" 
              type="password" 
              show-password 
              placeholder="输入 bili_jct"
            />
          </el-form-item>
          <el-form-item label="buvid3">
            <el-input 
              v-model="biliCookies.buvid3" 
              type="password" 
              show-password 
              placeholder="输入 buvid3"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveCookiesConfig('bilibili')" :loading="loading">
              保存 Bilibili Cookies
            </el-button>
          </el-form-item>
        </el-collapse-item>

        <!-- YouTube Cookies -->
        <el-collapse-item title="YouTube Cookies 配置" name="youtube-cookies">
          <el-alert
            title="您可以选择直接上传 Netscape 格式的 cookies.txt 文件，系统会自动解析所有 YouTube cookie 项"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          />
          
          <el-upload
            class="upload-demo"
            action="#"
            :auto-upload="false"
            :show-file-list="false"
            accept=".txt"
            :on-change="handleFileUpload"
          >
            <el-button type="primary">上传 cookies.txt</el-button>
            <template #tip>
              <div class="el-upload__tip">
                仅支持 Netscape 格式的 cookie 文件
              </div>
            </template>
          </el-upload>

          <el-divider>Cookie 列表</el-divider>
          
          <div class="cookies-list">
            <el-form-item 
              v-for="[key, value] in youtubeCookies" 
              :key="key" 
              :label="key"
            >
              <el-input 
                :value="value"
                @input="(val) => updateYoutubeCookie(key, val)"
                :placeholder="`输入 ${key}`"
              />
            </el-form-item>
          </div>
          
          <el-form-item>
            <el-button type="primary" @click="saveCookiesConfig('youtube')" :loading="loading">
              保存 YouTube Cookies
            </el-button>
          </el-form-item>
        </el-collapse-item>
      </el-collapse>

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
        <el-button type="primary" @click="saveConfig('system')" :loading="loading">
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

.el-collapse {
  margin: 20px 0;
}

:deep(.el-collapse-item__header) {
  font-size: 16px;
  font-weight: bold;
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}

.upload-demo {
  margin-bottom: 20px;
}

.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}

:deep(.el-input-group__append) {
  padding: 0;
}

:deep(.el-input-group__append .el-button) {
  margin: 0;
  border: none;
}

.cookies-list {
  max-height: 500px;
  overflow-y: auto;
  padding-right: 10px;
}

.cookies-list :deep(.el-form-item) {
  margin-bottom: 15px;
}

.cookies-list :deep(.el-form-item__label) {
  word-break: break-all;
  white-space: normal;
  line-height: 1.2;
  padding-bottom: 4px;
}
</style> 