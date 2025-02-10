<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import AppHeader from './AppHeader.vue'

const themeStore = useThemeStore()
</script>

<template>
  <div class="app-container" :class="themeStore.theme">
    <AppHeader />
    <div class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style>
:root {
  --app-background: var(--el-bg-color-page);
  --app-text-color: var(--el-text-color-primary);
}

:root[data-theme='dark'] {
  --el-bg-color: #242424;
  --el-bg-color-page: #1a1a1a;
  --el-text-color-primary: #e5eaf3;
  --el-border-color-light: #4c4d4f;
}
</style>

<style scoped>
.app-container {
  min-height: 100vh;
  width: 100%;
  background: var(--app-background);
  color: var(--app-text-color);
}

.main-content {
  width: 100%;
  min-height: calc(100vh - 60px);
  padding-top: 60px; /* 为固定的header留出空间 */
  padding: 80px 20px 20px; /* 调整上下左右的内边距 */
  max-width: 1200px; /* 设置最大宽度 */
  margin: 0 auto; /* 居中显示 */
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style> 