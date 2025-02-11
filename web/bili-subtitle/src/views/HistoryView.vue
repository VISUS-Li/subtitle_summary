<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { historyApi, type HistoryParams } from '@/services/history'
import type { TabsPaneContext } from 'element-plus'

// 搜索参数
const searchParams = ref<HistoryParams>({
  page: 1,
  pageSize: 10,
  sortOrder: 'desc',
  sortField: 'create_time'
})

// 数据加载状态
const loading = ref(false)

// 历史数据
const videoHistory = ref<any[]>([])
const subtitleHistory = ref<any[]>([])
const summaryHistory = ref<any[]>([])
const scriptHistory = ref<any[]>([])

// 分页信息
const pagination = ref({
  total: 0,
  currentPage: 1,
  pageSize: 10
})

// 活动的标签页
const activeTab = ref('videos')

// 关键词列表
const searchKeywords = ref<string[]>([])
const topics = ref<string[]>([])

// 平台选项
const platformOptions = [
  { label: '全部', value: '' },
  { label: 'B站', value: 'bilibili' },
  { label: 'YouTube', value: 'youtube' }
]

// 计算属性：当前显示的数据
const currentData = computed(() => {
  switch (activeTab.value) {
    case 'videos':
      return videoHistory.value
    case 'subtitles':
      return subtitleHistory.value
    case 'summaries':
      return summaryHistory.value
    case 'scripts':
      return scriptHistory.value
    default:
      return []
  }
})

// 加载历史数据
const loadHistory = async (type: string) => {
  loading.value = true
  try {
    let response
    switch (type) {
      case 'videos':
        response = await historyApi.getVideoHistory(searchParams.value)
        videoHistory.value = response.data.items
        break
      case 'subtitles':
        response = await historyApi.getSubtitleHistory(searchParams.value)
        subtitleHistory.value = response.data.items
        break
      case 'summaries':
        response = await historyApi.getSummaryHistory(searchParams.value)
        summaryHistory.value = response.data.items
        break
      case 'scripts':
        response = await historyApi.getScriptHistory(searchParams.value)
        scriptHistory.value = response.data.items
        break
    }
    if (response) {
      pagination.value.total = response.data.total
    }
  } catch (error) {
    ElMessage.error('加载数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 当前选中的主题和关键词
const selectedTopic = ref('')
const selectedKeyword = ref('')

// 处理主题选择
const handleTopicSelect = (topic: string) => {
  selectedTopic.value = topic
  selectedKeyword.value = ''
  searchParams.value = {
    ...searchParams.value,
    topic,
    keyword: ''
  }
  handleSearch()
}

// 处理关键词选择
const handleKeywordSelect = (keyword: string) => {
  selectedKeyword.value = keyword
  selectedTopic.value = ''
  searchParams.value = {
    ...searchParams.value,
    keyword,
    topic: ''
  }
  handleSearch()
}

// 清除筛选条件
const clearFilters = () => {
  selectedTopic.value = ''
  selectedKeyword.value = ''
  searchParams.value = {
    page: 1,
    pageSize: 10,
    sortOrder: 'desc',
    sortField: 'create_time'
  }
  handleSearch()
}

// 处理标签页切换
const handleTabChange = (tab: string) => {
  activeTab.value = tab
  searchParams.value.page = 1 // 重置页码
  handleSearch()
}

// 获取当前标签页的总数
const getCurrentTotal = computed(() => {
  switch (activeTab.value) {
    case 'videos':
      return videoHistory.value.length
    case 'subtitles':
      return subtitleHistory.value.length
    case 'summaries':
      return summaryHistory.value.length
    case 'scripts':
      return scriptHistory.value.length
    default:
      return 0
  }
})

// 搜索处理
const handleSearch = () => {
  searchParams.value.page = 1
  loadHistory(activeTab.value)
}

// 重置搜索
const handleReset = () => {
  searchParams.value = {
    page: 1,
    pageSize: 10,
    sortOrder: 'desc',
    sortField: 'create_time'
  }
  handleSearch()
}

// 分页变化处理
const handlePageChange = (page: number) => {
  searchParams.value.page = page
  loadHistory(activeTab.value)
}

// 查看详情
const handleViewDetail = (item: any) => {
  // 根据不同类型显示不同的详情弹窗
  if (activeTab.value === 'videos') {
    showDetail(item)
  } else if (activeTab.value === 'subtitles') {
    showSubtitleDetail(item)
  } else if (activeTab.value === 'summaries') {
    showSummaryDetail(item)
  } else if (activeTab.value === 'scripts') {
    showScriptDetail(item)
  }
}

// 详情弹窗控制
const detailDialogVisible = ref(false)
const currentDetail = ref<any>(null)

// 显示视频详情
const showVideoDetail = (video: any) => {
  currentDetail.value = video
  detailDialogVisible.value = true
}

// 显示字幕详情
const showSubtitleDetail = (subtitle: any) => {
  currentDetail.value = subtitle
  detailDialogVisible.value = true
}

// 显示总结详情
const showSummaryDetail = (summary: any) => {
  currentDetail.value = summary
  detailDialogVisible.value = true
}

// 显示脚本详情
const showScriptDetail = (script: any) => {
  currentDetail.value = script
  detailDialogVisible.value = true
}

// 加载关键词列表
const loadKeywords = async () => {
  try {
    const response = await historyApi.getKeywords()
    searchKeywords.value = response.data.search_keywords
    topics.value = response.data.topics
  } catch (error) {
    ElMessage.error('加载关键词列表失败')
    console.error(error)
  }
}

// 在组件挂载时加载关键词
onMounted(() => {
  loadHistory('videos')
  loadKeywords()
})

// 字幕和总结对话框状态
const subtitleDialogVisible = ref(false)
const summaryDialogVisible = ref(false)
const selectedSubtitleContent = ref('')
const selectedSummaryContent = ref('')

// 显示字幕内容
const showSubtitleContent = (subtitle: any) => {
  selectedSubtitleContent.value = subtitle.content
  subtitleDialogVisible.value = true
}

// 显示总结内容
const showSummaryContent = (summary: any) => {
  selectedSummaryContent.value = summary.content
  summaryDialogVisible.value = true
}

// 查看视频详情时，需要先获取完整信息
const showDetail = async (row: any) => {
  try {
    const response = await historyApi.getVideoDetail(row.id)
    currentDetail.value = response.data
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
    console.error(error)
  }
}

const getVideoUrl = (platform: string, videoId: string) => {
  if (platform === 'bilibili') {
    return `https://www.bilibili.com/video/${videoId}`
  } else if (platform === 'youtube') {
    return `https://www.youtube.com/watch?v=${videoId}`
  }
  return '#'
}
</script>

<template>
  <div class="history-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>历史记录</h2>
        </div>
      </template>

      <!-- 搜索表单 -->
      <div class="search-form">
        <el-form :inline="true" :model="searchParams">
          <!-- 当前筛选条件显示 -->
          <div class="current-filters" v-if="selectedTopic || selectedKeyword">
            <span class="filter-label">当前筛选：</span>
            <el-tag 
              v-if="selectedTopic" 
              closable 
              type="success"
              @close="clearFilters"
            >
              主题：{{ selectedTopic }}
            </el-tag>
            <el-tag 
              v-if="selectedKeyword" 
              closable 
              @close="clearFilters"
            >
              关键词：{{ selectedKeyword }}
            </el-tag>
          </div>

          <!-- 搜索框 -->
          <el-form-item>
            <el-autocomplete
              v-model="searchParams.keyword"
              :fetch-suggestions="(query, cb) => {
                const results = []
                if (searchKeywords.length) {
                  results.push({
                    header: '搜索关键词'
                  })
                  results.push(...searchKeywords
                    .filter(kw => kw.toLowerCase().includes(query.toLowerCase()))
                    .map(value => ({ value, category: 'search' }))
                  )
                }
                if (topics.length) {
                  results.push({
                    header: '主题'
                  })
                  results.push(...topics
                    .filter(topic => topic.toLowerCase().includes(query.toLowerCase()))
                    .map(value => ({ value, category: 'topic' }))
                  )
                }
                cb(results)
              }"
              :placeholder="selectedTopic ? `在主题 '${selectedTopic}' 中搜索` : '输入关键词搜索'"
              :trigger-on-focus="true"
              @select="({ value, category }) => category === 'topic' ? handleTopicSelect(value) : handleKeywordSelect(value)"
            >
              <template #default="{ item }">
                <div v-if="item.header" class="suggestion-header">
                  {{ item.header }}
                </div>
                <div v-else class="suggestion-item">
                  <el-tag size="small" :type="item.category === 'search' ? '' : 'success'" class="mx-1">
                    {{ item.category === 'search' ? '搜索' : '主题' }}
                  </el-tag>
                  {{ item.value }}
                </div>
              </template>
            </el-autocomplete>
          </el-form-item>

          <!-- 其他搜索条件 -->
          <el-form-item label="平台">
            <el-select v-model="searchParams.platform" placeholder="选择平台" clearable>
              <el-option
                v-for="option in platformOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="时间范围">
            <el-date-picker
              v-model="searchParams.startTime"
              type="datetime"
              placeholder="开始时间"
            />
            <span class="mx-2">-</span>
            <el-date-picker
              v-model="searchParams.endTime"
              type="datetime"
              placeholder="结束时间"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>

        <!-- 关键词标签展示 -->
        <div class="keyword-tags mt-4">
          <div class="tag-section">
            <h4>热门搜索关键词：</h4>
            <div class="tag-list">
              <el-tag
                v-for="keyword in searchKeywords.slice(0, 10)"
                :key="keyword"
                class="mx-1 clickable"
                @click="handleKeywordSelect(keyword)"
              >
                {{ keyword }}
              </el-tag>
            </div>
          </div>
          <div class="tag-section">
            <h4>热门主题：</h4>
            <div class="tag-list">
              <el-tag
                v-for="topic in topics.slice(0, 10)"
                :key="topic"
                class="mx-1 clickable"
                type="success"
                @click="handleTopicSelect(topic)"
              >
                {{ topic }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 内容标签页 -->
      <el-tabs v-model="activeTab" @tab-click="handleTabChange">
        <el-tab-pane name="videos" :label="`视频列表 (${pagination.total})`">
          <el-table
            v-loading="loading"
            :data="videoHistory"
            style="width: 100%"
          >
            <el-table-column prop="title" label="标题" min-width="200">
              <template #default="{ row }">
                <a 
                  :href="getVideoUrl(row.platform, row.platform_vid)" 
                  target="_blank" 
                  class="video-link"
                >
                  {{ row.title }}
                </a>
              </template>
            </el-table-column>
            <el-table-column prop="platform" label="平台" width="100" />
            <el-table-column prop="author" label="作者" width="120" />
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="{ row }">
                {{ new Date(row.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="subtitles" :label="`字幕列表 (${pagination.total})`">
          <el-table
            v-loading="loading"
            :data="subtitleHistory"
            style="width: 100%"
          >
            <el-table-column prop="video.title" label="视频标题" min-width="200">
              <template #default="{ row }">
                <a 
                  :href="getVideoUrl(row.video.platform, row.video.platform_vid)" 
                  target="_blank" 
                  class="video-link"
                >
                  {{ row.video.title }}
                </a>
              </template>
            </el-table-column>
            <el-table-column prop="language" label="语言" width="100" />
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="{ row }">
                {{ new Date(row.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="summaries" :label="`总结列表 (${pagination.total})`">
          <el-table
            v-loading="loading"
            :data="summaryHistory"
            style="width: 100%"
          >
            <el-table-column prop="video.title" label="视频标题" min-width="200">
              <template #default="{ row }">
                <a 
                  :href="getVideoUrl(row.video.platform, row.video.platform_vid)" 
                  target="_blank" 
                  class="video-link"
                >
                  {{ row.video.title }}
                </a>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="score" label="分数" width="100" />
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="{ row }">
                {{ new Date(row.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="scripts" :label="`脚本列表 (${pagination.total})`">
          <el-table
            v-loading="loading"
            :data="scriptHistory"
            style="width: 100%"
          >
            <el-table-column prop="topic" label="主题" min-width="150" />
            <el-table-column prop="platform" label="平台" width="100" />
            <el-table-column prop="video_count" label="视频数量" width="100" />
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="{ row }">
                {{ new Date(row.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="(size) => { searchParams.pageSize = size; handleSearch() }"
          @current-change="handlePageChange"
        />
      </div>

      <!-- 详情弹窗 -->
      <el-dialog
        v-model="detailDialogVisible"
        :title="activeTab === 'videos' ? '视频详情' : 
                activeTab === 'subtitles' ? '字幕详情' : 
                activeTab === 'summaries' ? '总结详情' : '脚本详情'"
        width="80%"
      >
        <template v-if="currentDetail">
          <!-- 视频详情 -->
          <template v-if="activeTab === 'videos'">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="标题">
                <a 
                  :href="getVideoUrl(currentDetail.platform, currentDetail.platform_vid)" 
                  target="_blank"
                  class="video-link"
                >
                  {{ currentDetail.title }}
                </a>
              </el-descriptions-item>
              <el-descriptions-item label="作者">{{ currentDetail.author }}</el-descriptions-item>
              <el-descriptions-item label="平台">{{ currentDetail.platform }}</el-descriptions-item>
              <el-descriptions-item label="观看次数">{{ currentDetail.view_count }}</el-descriptions-item>
              <el-descriptions-item label="标签" :span="2">{{ currentDetail.tags?.join(', ') }}</el-descriptions-item>
              <el-descriptions-item label="关键词" :span="2">{{ currentDetail.keywords?.join(', ') }}</el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ currentDetail.description }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ new Date(currentDetail.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
              </el-descriptions-item>
            </el-descriptions>

            <!-- 添加字幕和总结标签页 -->
            <el-tabs class="mt-4">
              <el-tab-pane label="字幕列表">
                <el-table
                  v-if="currentDetail.subtitles?.length"
                  :data="currentDetail.subtitles"
                  style="width: 100%"
                >
                  <el-table-column prop="language" label="语言" width="100" />
                  <el-table-column prop="create_time" label="创建时间" width="180">
                    <template #default="{ row }">
                      {{ new Date(row.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120">
                    <template #default="{ row }">
                      <el-button
                        type="primary"
                        link
                        @click="showSubtitleContent(row)"
                      >
                        查看内容
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-else description="暂无字幕" />
              </el-tab-pane>

              <el-tab-pane label="总结列表">
                <el-table
                  v-if="currentDetail.summaries?.length"
                  :data="currentDetail.summaries"
                  style="width: 100%"
                >
                  <el-table-column prop="status" label="状态" width="100" />
                  <el-table-column prop="score" label="分数" width="100" />
                  <el-table-column prop="create_time" label="创建时间" width="180">
                    <template #default="{ row }">
                      {{ new Date(row.create_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120">
                    <template #default="{ row }">
                      <el-button
                        type="primary"
                        link
                        @click="showSummaryContent(row)"
                      >
                        查看内容
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-else description="暂无总结" />
              </el-tab-pane>
            </el-tabs>

            <!-- 字幕内容对话框 -->
            <el-dialog
              v-model="subtitleDialogVisible"
              title="字幕内容"
              width="60%"
            >
              <el-input
                v-model="selectedSubtitleContent"
                type="textarea"
                :rows="15"
                readonly
              />
            </el-dialog>

            <!-- 总结内容对话框 -->
            <el-dialog
              v-model="summaryDialogVisible"
              title="总结内容"
              width="60%"
            >
              <el-input
                v-model="selectedSummaryContent"
                type="textarea"
                :rows="15"
                readonly
              />
            </el-dialog>
          </template>

          <!-- 字幕详情 -->
          <template v-if="activeTab === 'subtitles'">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="视频标题">
                <a 
                  :href="getVideoUrl(currentDetail.video.platform, currentDetail.video.platform_vid)" 
                  target="_blank"
                  class="video-link"
                >
                  {{ currentDetail.video.title }}
                </a>
              </el-descriptions-item>
              <el-descriptions-item label="语言">{{ currentDetail.language }}</el-descriptions-item>
            </el-descriptions>
            <div class="mt-4">
              <h4>字幕内容：</h4>
              <el-input
                v-model="currentDetail.content"
                type="textarea"
                :rows="10"
                readonly
              />
            </div>
          </template>

          <!-- 总结详情 -->
          <template v-if="activeTab === 'summaries'">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="视频标题">
                <a 
                  :href="getVideoUrl(currentDetail.video.platform, currentDetail.video.platform_vid)" 
                  target="_blank"
                  class="video-link"
                >
                  {{ currentDetail.video.title }}
                </a>
              </el-descriptions-item>
              <el-descriptions-item label="状态">{{ currentDetail.status }}</el-descriptions-item>
              <el-descriptions-item label="分数">{{ currentDetail.score }}</el-descriptions-item>
            </el-descriptions>
            <div class="mt-4">
              <h4>总结内容：</h4>
              <el-input
                v-model="currentDetail.content"
                type="textarea"
                :rows="10"
                readonly
              />
            </div>
          </template>

          <!-- 脚本详情 -->
          <template v-if="activeTab === 'scripts'">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="主题">{{ currentDetail.topic }}</el-descriptions-item>
              <el-descriptions-item label="平台">{{ currentDetail.platform }}</el-descriptions-item>
              <el-descriptions-item label="视频数量">{{ currentDetail.video_count }}</el-descriptions-item>
            </el-descriptions>
            <div class="mt-4">
              <h4>脚本内容：</h4>
              <el-input
                v-model="currentDetail.content"
                type="textarea"
                :rows="10"
                readonly
              />
            </div>
          </template>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<style scoped>
.history-container {
  min-height: calc(100vh - 100px);
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table) {
  margin-top: 20px;
}

.mx-2 {
  margin: 0 8px;
}

.mt-4 {
  margin-top: 16px;
}

.keyword-tags {
  margin-top: 16px;
}

.tag-section {
  margin-bottom: 16px;
}

.tag-section h4 {
  margin-bottom: 8px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.clickable {
  cursor: pointer;
}

.suggestion-header {
  font-size: 12px;
  color: #909399;
  padding: 8px 12px;
  background-color: #f5f7fa;
}

.suggestion-item {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-autocomplete-suggestion__wrap) {
  padding: 0;
}

.el-tabs {
  margin-top: 20px;
}

.el-table {
  margin-top: 10px;
}

.video-link {
  color: #409EFF;
  text-decoration: none;
}

.video-link:hover {
  text-decoration: underline;
}

.current-filters {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #909399;
  font-size: 14px;
}

.el-tag {
  margin-right: 8px;
}

/* 标签页样式优化 */
:deep(.el-tabs__item) {
  font-size: 14px;
  padding: 0 20px;
}

:deep(.el-tabs__item.is-active) {
  font-weight: bold;
}
</style> 