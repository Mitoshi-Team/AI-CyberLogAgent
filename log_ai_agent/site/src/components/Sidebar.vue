<template>
  <aside class="fixed left-0 top-0 w-64 h-screen bg-dark-900/80 backdrop-blur-xl border-r border-dark-800 pt-6 flex flex-col">
    <!-- Логотип -->
    <div class="px-6 mb-8">
      <div class="flex items-center gap-3 text-primary-400 font-bold text-lg">
        <div class="w-7 h-7 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary-500/30">
          <svg
            class="w-4 h-4 text-white"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
        <span class="bg-gradient-to-r from-primary-400 to-primary-500 bg-clip-text text-transparent">CyberLog</span>
      </div>
    </div>

    <!-- Навигация -->
    <nav class="space-y-1 px-3 mb-8">
      <RouterLink
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        class="nav-link"
      >
        <component :is="item.icon" class="w-5 h-5" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- Профиль -->
    <div class="mt-auto px-4 py-3 mx-3 mb-3">
      <div class="mb-3 pb-2.5 border-b border-dark-700/50">
        <p class="text-sm font-medium text-dark-100 truncate text-center">
          {{ appStore.currentUser?.username || 'User' }}
        </p>
      </div>
      <button
        @click="logout"
        class="w-full flex items-center justify-center gap-2 px-3 py-2 bg-dark-800/50 hover:bg-danger-500/10 text-dark-300 hover:text-danger-400 rounded-lg transition-all duration-200 border border-dark-700/50 hover:border-danger-500/50 group"
      >
        <svg class="w-4 h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
        </svg>
        <span class="text-xs font-medium">Выйти из системы</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { useRouter } from 'vue-router'
import IconDashboard from '@/components/icons/IconDashboard.vue'
import IconStats from '@/components/icons/IconStats.vue'
import IconChat from '@/components/icons/IconChat.vue'
import IconHistory from '@/components/icons/IconHistory.vue'

const appStore = useAppStore()
const router = useRouter()

const logout = () => {
  appStore.logout()
  router.push('/login')
}

const menuItems = [
  {
    to: '/',
    label: 'Панель управления',
    icon: IconDashboard,
  },
  {
    to: '/statistics',
    label: 'Статистика',
    icon: IconStats,
  },
  {
    to: '/chat',
    label: 'Чат с AI',
    icon: IconChat,
  },
  {
    to: '/history',
    label: 'История',
    icon: IconHistory,
  },
]
</script>

<style scoped>
.nav-link {
  @apply flex items-center gap-3 px-4 py-3 text-dark-400 rounded-lg transition-all duration-200 hover:bg-dark-800/50 hover:text-dark-200;
}

.nav-link.router-link-active {
  @apply bg-gradient-to-r from-primary-500/10 to-transparent text-primary-400 font-medium border-l-2 border-primary-500;
}
</style>
