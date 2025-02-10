import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import SubtitleView from '@/views/SubtitleView.vue'
import HistoryView from '@/views/HistoryView.vue'
import ConfigPanel from '@/components/ConfigPanel.vue'

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
          path: '/settings',
          name: 'settings',
          component: ConfigPanel
        }
      ]
    }
  ]
})

export default router
