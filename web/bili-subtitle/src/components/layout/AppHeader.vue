<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import { menuItems } from '@/types/layout'
import * as Icons from '@element-plus/icons-vue'

const router = useRouter()
const themeStore = useThemeStore()
const activeMenu = ref(router.currentRoute.value.path)

const handleMenuSelect = (path: string) => {
  router.push(path)
}

const isDark = computed(() => themeStore.theme === 'dark')
</script>

<template>
  <el-header class="app-header">
    <div class="header-content">
      <div class="logo">
        <img src="@/assets/logo.svg" alt="Logo" />
        <span class="title">Bili2Text</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        mode="horizontal"
        :ellipsis="false"
        class="nav-menu"
      >
        <el-menu-item 
          v-for="item in menuItems"
          :key="item.key"
          :index="item.path"
          @click="handleMenuSelect(item.path)"
        >
          <el-icon v-if="item.icon">
            <component :is="Icons[item.icon as keyof typeof Icons]" />
          </el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>

        <div class="flex-grow" />
        
        <el-menu-item @click="themeStore.toggleTheme">
          <el-icon>
            <component :is="isDark ? 'Sunny' : 'Moon'" />
          </el-icon>
        </el-menu-item>
      </el-menu>
    </div>
  </el-header>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  z-index: 1000;
  padding: 0;
  width: 100%;
}

.header-content {
  max-width: 1200px;
  height: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
  margin-right: 40px;
}

.logo img {
  height: 32px;
  margin-right: 10px;
}

.title {
  font-size: 20px;
  font-weight: bold;
  color: var(--el-color-primary);
}

.nav-menu {
  flex: 1;
  border-bottom: none;
  background: transparent;
  display: flex;
}

.flex-grow {
  flex-grow: 1;
}

:deep(.el-menu-item) {
  display: flex;
  align-items: center;
}

:deep(.el-icon) {
  margin-right: 4px;
}

:deep(.el-menu--horizontal) {
  border-bottom: none;
}
</style> 