import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'cmdb/servers',
          name: 'ServerList',
          component: () => import('@/views/cmdb/ServerListView.vue'),
        },
        {
          path: 'cicd/pipelines',
          name: 'PipelineList',
          component: () => import('@/views/cicd/PipelineListView.vue'),
        },
        {
          path: 'cicd/builds/:buildId/log',
          name: 'BuildLog',
          component: () => import('@/views/cicd/BuildLogView.vue'),
        },
        {
          path: 'release/apps',
          name: 'AppList',
          component: () => import('@/views/release/AppListView.vue'),
        },
        {
          path: 'release/releases',
          name: 'ReleaseList',
          component: () => import('@/views/release/ReleaseListView.vue'),
        },
        {
          path: 'monitor/alert-rules',
          name: 'AlertRules',
          component: () => import('@/views/monitor/AlertRulesView.vue'),
        },
        {
          path: 'monitor/alert-events',
          name: 'AlertEvents',
          component: () => import('@/views/monitor/AlertEventsView.vue'),
        },
        {
          path: 'log-analysis/watchers',
          name: 'WatcherList',
          component: () => import('@/views/log-analysis/WatcherListView.vue'),
        },
        {
          path: 'log-analysis/watchers/:watcherId/templates',
          name: 'TemplateList',
          component: () => import('@/views/log-analysis/TemplatesView.vue'),
        },
        {
          path: 'terminal/:serverId',
          name: 'Terminal',
          component: () => import('@/views/terminal/TerminalView.vue'),
        },
        {
          path: 'notification/channels',
          name: 'NotificationChannels',
          component: () => import('@/views/notification/ChannelsView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.token) {
    next('/login')
  } else if (to.path === '/login' && authStore.token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
