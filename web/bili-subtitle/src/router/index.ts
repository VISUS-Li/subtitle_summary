import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import SubtitleView from '@/views/SubtitleView.vue'
import HistoryView from '@/views/HistoryView.vue'
import ConfigManager from '@/components/ConfigManager.vue'
import SingleVideoView from '@/views/SingleVideoView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          redirect: '/subtitle'
        },
        {
          path: '/subtitle',
          name: 'subtitle',
          component: SubtitleView
        },
        {
          path: '/history',
          name: 'history',
          component: HistoryView
        },
        {
          path: '/config',
          name: 'config',
          component: ConfigManager,
          meta: {
            title: '配置管理'
          }
        },
        {
          path: '/single',
          name: 'single',
          component: SingleVideoView
        }
      ]
    }
  ]
})

export default router
