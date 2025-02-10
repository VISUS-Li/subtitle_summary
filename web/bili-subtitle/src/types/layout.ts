export interface MenuItem {
  key: string
  label: string
  icon?: string
  path: string
}

export const menuItems: MenuItem[] = [
  {
    key: 'subtitle',
    label: '字幕总结',
    icon: 'Document',
    path: '/subtitle'
  },
  {
    key: 'history',
    label: '历史记录',
    icon: 'History',
    path: '/history'
  },
  {
    key: 'settings',
    label: '系统设置',
    icon: 'Setting',
    path: '/settings'
  }
] 