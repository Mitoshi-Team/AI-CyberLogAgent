import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { checkBackendReady } from '@/services/backendReadiness'

/**
 * Маршруты приложения
 */
const routes = [
  {
    path: '/assistant-loading',
    name: 'AssistantLoading',
    component: () => import('@/pages/AssistantLoadingPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/pages/ChatPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('@/pages/StatisticsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/pages/HistoryPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('@/pages/ConfigPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * Навигационный guard для проверки аутентификации
 */
router.beforeEach(async (to, from, next) => {
  const appStore = useAppStore()
  const backendReady = await checkBackendReady()

  if (!backendReady && to.name !== 'AssistantLoading') {
    next({
      name: 'AssistantLoading',
      query: { redirect: to.fullPath },
    })
    return
  }

  if (backendReady && to.name === 'AssistantLoading') {
    next(appStore.isAuthenticated ? '/' : '/login')
    return
  }

  if (to.meta.requiresAuth && !appStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && appStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
