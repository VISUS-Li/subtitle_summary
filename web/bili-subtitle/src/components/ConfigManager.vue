<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { configService } from '@/services/configService'
import { ElMessage } from 'element-plus'

interface ConfigItem {
  service_name: string
  config_key: string
  value: any
  description?: string
  category?: string
  parent_key?: string
}

const configs = ref<Record<string, ConfigItem[]>>({})
const loading = ref(false)

// 预定义的服务列表
const DEFAULT_SERVICES = [
  'system',
  'whisper',
  'youtube_download',
  'bilibili_download'
]

// 在 script setup 部分添加 whisper 模型选项常量
const WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large']

// 添加新的类型判断函数
const isJsonFormConfig = (value: any): boolean => {
  try {
    // 如果是字符串，尝试解析
    const parsedValue = typeof value === 'string' ? JSON.parse(value) : value
    // 检查是否为对象（不是数组）且包含多个键值对
    return typeof parsedValue === 'object' && 
           parsedValue !== null && 
           !Array.isArray(parsedValue) && 
           Object.keys(parsedValue).length > 0
  } catch {
    return false
  }
}

// 递归处理嵌套的配置对象
const flattenConfigs = (
  serviceName: string,
  configObj: Record<string, any>
): ConfigItem[] => {
  const result: ConfigItem[] = []

  for (const [key, detail] of Object.entries(configObj)) {
    if (typeof detail === 'object' && detail !== null && 'value' in detail) {
      // 处理新的配置详情格式
      result.push({
        service_name: serviceName,
        config_key: key,
        value: detail.value,
        description: detail.description || '',
        category: detail.category || serviceName,
        parent_key: ''
      })
    } else if (detail !== null && typeof detail === 'object' && !Array.isArray(detail)) {
      // 处理嵌套对象
      const nestedConfigs = flattenConfigs(serviceName, detail)
      result.push(...nestedConfigs)
    } else {
      // 处理简单值（向后兼容）
      result.push({
        service_name: serviceName,
        config_key: key,
        value: detail,
        description: '',
        category: serviceName,
        parent_key: ''
      })
    }
  }

  return result
}

const loadServiceConfigs = async (serviceName: string) => {
  try {
    loading.value = true
    const response = await configService.getServiceConfigs(serviceName)
    console.log(`${serviceName} response:`, response)
    
    if (response) {
      const flattenedConfigs = flattenConfigs(serviceName, response)
      console.log(`${serviceName} flattened:`, flattenedConfigs)
      configs.value[serviceName] = flattenedConfigs
    }
  } catch (error) {
    console.error(`加载${serviceName}配置失败:`, error)
    ElMessage.error(`加载${serviceName}配置失败`)
  } finally {
    loading.value = false
  }
}

const updateConfig = async (config: ConfigItem) => {
  try {
    loading.value = true
    
    // 构建完整的配置路径和值
    const pathParts = config.config_key.split('.')
    const originalConfigs = configs.value[config.service_name]
    
    if (pathParts.length > 1) {
      const rootConfig = originalConfigs.find(c => !c.parent_key)?.value || {}
      let current = rootConfig
      
      for (let i = 0; i < pathParts.length - 1; i++) {
        if (!current[pathParts[i]]) {
          current[pathParts[i]] = {}
        }
        current = current[pathParts[i]]
      }
      
      current[pathParts[pathParts.length - 1]] = config.value
      
      await configService.setServiceConfig(
        config.service_name,
        pathParts[0],
        rootConfig,
        config.description
      )
    } else {
      await configService.setServiceConfig(
        config.service_name,
        config.config_key,
        config.value,
        config.description
      )
    }
    
    ElMessage.success('配置更新成功')
  } catch (error) {
    console.error('配置更新失败:', error)
    ElMessage.error('配置更新失败')
  } finally {
    loading.value = false
  }
}

// 格式化显示值
const formatValue = (value: any): string => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

// 修改 getValueType 函数
const getValueType = (value: any, configKey: string): string => {
  if (configKey === 'model_name') return 'model_select'
  if (isJsonFormConfig(value)) return 'json_form'
  if (value === null || value === undefined) return 'string'
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? 'integer' : 'float'
  }
  if (typeof value === 'object') return 'json'
  return 'string'
}

// 修改 handleJsonFieldUpdate 函数，添加类型转换
const handleJsonFieldUpdate = (row: ConfigItem, field: string, value: any) => {
  const currentValue = typeof row.value === 'string' ? JSON.parse(row.value) : row.value
  // 根据原始值的类型进行转换
  const originalType = typeof currentValue[field]
  let convertedValue = value
  
  switch (originalType) {
    case 'number':
      convertedValue = Number(value)
      break
    case 'boolean':
      convertedValue = Boolean(value)
      break
    case 'string':
      convertedValue = String(value)
      break
    // 对象和数组保持原样
    case 'object':
      convertedValue = value
      break
  }
  
  currentValue[field] = convertedValue
  handleValueUpdate(row, currentValue)
}

// 修改 handleValueUpdate 函数，优化类型转换逻辑
const handleValueUpdate = (row: ConfigItem, newValue: any) => {
  try {
    const valueType = getValueType(row.value, row.config_key)
    let parsedValue: any

    switch (valueType) {
      case 'json_form':
      case 'json':
        // 如果是字符串则解析，否则保持对象格式
        parsedValue = typeof newValue === 'string' ? JSON.parse(newValue) : newValue
        break
      case 'integer':
        parsedValue = Number.parseInt(String(newValue))
        if (isNaN(parsedValue)) {
          throw new Error('无效的整数值')
        }
        break
      case 'float':
        parsedValue = Number.parseFloat(String(newValue))
        if (isNaN(parsedValue)) {
          throw new Error('无效的浮点数值')
        }
        break
      case 'boolean':
        // 确保布尔值的正确转换
        parsedValue = Boolean(newValue)
        if (typeof newValue === 'string') {
          parsedValue = newValue.toLowerCase() === 'true'
        }
        break
      case 'model_select':
        // 确保模型选择保持为字符串
        parsedValue = String(newValue)
        break
      default:
        // 保持原始类型
        parsedValue = newValue
    }

    row.value = parsedValue
    updateConfig(row)
  } catch (error) {
    console.error('值格式无效:', error)
    ElMessage.error(`值格式无效: ${error.message}`)
  }
}

// 添加监听器来查看配置数据的变化
watch(configs, (newConfigs) => {
  console.log('configs changed:', newConfigs)
}, { deep: true })

onMounted(async () => {
  console.log('Component mounted, loading configs...')
  await Promise.all(DEFAULT_SERVICES.map(loadServiceConfigs))
  console.log('All configs loaded:', configs.value)
})
</script>

<template>
  <div class="config-manager">
    <el-tabs type="border-card">
      <el-tab-pane
        v-for="serviceName in DEFAULT_SERVICES"
        :key="serviceName"
        :label="serviceName.replace('_', ' ').toUpperCase()"
      >
        <div v-if="configs[serviceName]">
          配置数量: {{ configs[serviceName].length }}
        </div>
        
        <el-table
          :data="configs[serviceName] || []"
          v-loading="loading"
          style="width: 100%"
          row-key="config_key"
        >
          <el-table-column prop="config_key" label="配置项" width="300">
            <template #default="{ row }">
              <el-tooltip
                :content="row.description || '无描述'"
                placement="top"
                effect="light"
              >
                <span>{{ row.config_key }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          
          <el-table-column label="值" min-width="300">
            <template #default="scope">              
              <template v-if="scope.row">
                <!-- 添加 JSON 表单编辑器 -->
                <template v-if="getValueType(scope.row.value, scope.row.config_key) === 'json_form'">
                  <div class="json-form-editor">
                    <template v-for="(value, key) in (typeof scope.row.value === 'string' ? 
                      JSON.parse(scope.row.value) : scope.row.value)" :key="key">
                      <div class="json-form-item">
                        <span class="json-key">{{ key }}:</span>
                        <template v-if="typeof value === 'boolean'">
                          <el-switch
                            v-model="scope.row.value[key]"
                            @change="(val) => handleJsonFieldUpdate(scope.row, key, val)"
                          />
                        </template>
                        <template v-else-if="typeof value === 'number'">
                          <el-input-number
                            v-model="scope.row.value[key]"
                            :controls="true"
                            @change="(val) => handleJsonFieldUpdate(scope.row, key, val)"
                          />
                        </template>
                        <template v-else>
                          <el-input
                            v-model="scope.row.value[key]"
                            @change="(val) => handleJsonFieldUpdate(scope.row, key, val)"
                          />
                        </template>
                      </div>
                    </template>
                  </div>
                </template>

                <!-- 其他现有的输入类型 -->
                <el-select
                  v-else-if="getValueType(scope.row.value, scope.row.config_key) === 'model_select'"
                  v-model="scope.row.value"
                  @change="(val) => handleValueUpdate(scope.row, val)"
                >
                  <el-option
                    v-for="model in WHISPER_MODELS"
                    :key="model"
                    :label="model"
                    :value="model"
                  />
                </el-select>

                <el-switch
                  v-else-if="getValueType(scope.row.value, scope.row.config_key) === 'boolean'"
                  v-model="scope.row.value"
                  @change="() => handleValueUpdate(scope.row, scope.row.value)"
                />
                
                <el-input-number
                  v-else-if="getValueType(scope.row.value, scope.row.config_key) === 'integer'"
                  v-model="scope.row.value"
                  :controls="true"
                  @change="(val) => handleValueUpdate(scope.row, val)"
                />
                
                <el-input-number
                  v-else-if="getValueType(scope.row.value, scope.row.config_key) === 'float'"
                  v-model="scope.row.value"
                  :precision="2"
                  :controls="true"
                  @change="(val) => handleValueUpdate(scope.row, val)"
                />
                
                <el-input
                  v-else-if="getValueType(scope.row.value, scope.row.config_key) === 'json'"
                  type="textarea"
                  :rows="4"
                  :value="formatValue(scope.row.value)"
                  @change="(val) => handleValueUpdate(scope.row, val)"
                />
                
                <el-input
                  v-else
                  v-model="scope.row.value"
                  @change="(val) => handleValueUpdate(scope.row, val)"
                />
              </template>
            </template>
          </el-table-column>

          <el-table-column prop="category" label="分类" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.category }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="描述" min-width="200">
            <template #default="{ row }">
              <el-input
                v-model="row.description"
                type="textarea"
                :rows="2"
                :placeholder="row.description || '无描述'"
                @change="() => updateConfig(row)"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.config-manager {
  padding: 20px;
}

.json-form-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.json-form-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.json-key {
  min-width: 150px;
  font-weight: bold;
}

:deep(.el-table) {
  margin-top: 20px;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-textarea__inner) {
  font-family: monospace;
}
</style> 