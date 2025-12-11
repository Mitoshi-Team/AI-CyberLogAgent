import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/stores/app'

/**
 * Маршруты приложения
 */
const routes = [
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
router.beforeEach((to, from, next) => {
  const appStore = useAppStore()

  if (to.meta.requiresAuth && !appStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && appStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
