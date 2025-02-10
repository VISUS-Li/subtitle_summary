import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Theme } from '@/types/theme'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>('light')

  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    document.documentElement.setAttribute('data-theme', theme.value)
  }

  return {
    theme,
    toggleTheme
  }
}) 