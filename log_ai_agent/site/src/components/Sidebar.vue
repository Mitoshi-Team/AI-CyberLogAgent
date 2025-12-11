<template>
  <aside 
    :class="[
      'fixed left-0 top-0 h-screen bg-dark-900/80 backdrop-blur-xl border-r border-dark-800 pt-6 flex flex-col transition-all duration-300',
      isCollapsed ? 'w-20' : 'w-20 sm:w-64'
    ]"
  >
    <!-- Кнопка сворачивания -->
    <button
      @click="isCollapsed = !isCollapsed"
      class="absolute -right-3 top-8 w-6 h-6 bg-dark-800 border border-dark-700 rounded-full flex items-center justify-center hover:bg-dark-700 transition-colors z-10"
    >
      <svg 
        :class="['w-3 h-3 text-dark-300 transition-transform duration-300', isCollapsed ? 'rotate-180' : '']"
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
    </button>

    <!-- Логотип -->
    <div class="px-6 mb-8 overflow-hidden">
      <div class="flex items-center gap-3 text-primary-400 font-bold text-lg">
        <div class="w-7 h-7 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-lg shadow-primary-500/30 flex-shrink-0">
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
        <span 
          :class="[
            'bg-gradient-to-r from-primary-400 to-primary-500 bg-clip-text text-transparent whitespace-nowrap transition-opacity duration-300',
            isCollapsed || 'hidden sm:block',
            isCollapsed ? 'opacity-0 w-0' : 'opacity-100'
          ]"
        >
          CyberLog
        </span>
      </div>
    </div>

    <!-- Навигация -->
    <nav class="space-y-1 px-3 mb-8">
      <RouterLink
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        :class="[
          'nav-link',
          isCollapsed ? 'justify-center' : 'justify-center sm:justify-start'
        ]"
        :title="isCollapsed ? item.label : ''"
      >
        <div class="relative flex-shrink-0">
          <component :is="item.icon" class="w-5 h-5" />
          <span 
            v-if="item.to === '/chat' && appStore.unreadChatMessages > 0"
            class="absolute -top-1 -right-1 w-3 h-3 bg-danger-500 rounded-full flex items-center justify-center text-[8px] font-bold text-white animate-pulse"
          >
            {{ appStore.unreadChatMessages > 9 ? '9+' : appStore.unreadChatMessages }}
          </span>
        </div>
        <span 
          :class="[
            'transition-opacity duration-300 whitespace-nowrap',
            isCollapsed || 'hidden sm:inline',
            isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100'
          ]"
        >
          {{ item.label }}
        </span>
      </RouterLink>
    </nav>

    <!-- Профиль -->
    <div :class="['mt-auto py-3 mb-3', isCollapsed || 'px-2 sm:px-4 sm:mx-3', isCollapsed && 'px-2']">
      <div 
        :class="[
          'mb-3 pb-2.5 border-b border-dark-700/50 transition-all duration-300',
          isCollapsed || 'hidden sm:block',
          isCollapsed ? 'opacity-0 h-0 overflow-hidden' : 'opacity-100'
        ]"
      >
        <p class="text-sm font-medium text-dark-100 truncate text-center">
          {{ appStore.currentUser?.username || 'User' }}
        </p>
      </div>
      <button
        @click="logout"
        :class="[
          'w-full flex items-center justify-center bg-dark-800/50 hover:bg-danger-500/10 text-dark-300 hover:text-danger-400 rounded-lg transition-all duration-300 border border-dark-700/50 hover:border-danger-500/50 group overflow-hidden',
          isCollapsed ? 'p-1.5' : 'p-1.5 sm:gap-2 sm:px-3 sm:py-2'
        ]"
        :title="isCollapsed || 'sm' ? 'Выйти из системы' : ''"
      >
        <svg class="w-5 h-5 transition-transform group-hover:translate-x-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
        </svg>
        <span 
          v-if="!isCollapsed"
          :class="[
            'text-xs font-medium whitespace-nowrap hidden sm:inline transition-opacity duration-300 delay-100',
            isCollapsed ? 'opacity-0' : 'opacity-100'
          ]"
        >
          Выйти из системы
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch, provide, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useRouter } from 'vue-router'
import IconStats from '@/components/icons/IconStats.vue'
import IconChat from '@/components/icons/IconChat.vue'
import IconHistory from '@/components/icons/IconHistory.vue'

const appStore = useAppStore()
const router = useRouter()
const isCollapsed = computed({
  get: () => appStore.sidebarCollapsed,
  set: (value) => { appStore.sidebarCollapsed = value }
})

const logout = () => {
  appStore.logout()
  router.push('/login')
}

const menuItems = [
  {
    to: '/chat',
    label: 'Чат с AI',
    icon: IconChat,
  },
  {
    to: '/statistics',
    label: 'Статистика',
    icon: IconStats,
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
