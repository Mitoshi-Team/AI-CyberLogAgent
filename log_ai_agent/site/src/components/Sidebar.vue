<template>
  <aside 
    :class="[
      'fixed left-0 top-0 h-screen bg-[#1d1d1d] backdrop-blur-xl border-r border-[#262830] pt-6 flex flex-col transition-all duration-300 z-40',
      isCollapsed ? 'w-[4.5rem]' : 'w-[4.5rem] sm:w-64'
    ]"
  >
    <!-- Логотип -->
    <div class="px-4 sm:px-5 mb-8 pt-1">
      <div class="flex items-center justify-between">
        <button
          v-if="isCollapsed"
          @mouseenter="isMiniLogoHovered = true"
          @mouseleave="isMiniLogoHovered = false"
          @click="expandSidebar"
          class="w-8 h-8 flex-shrink-0 flex items-center justify-center"
          title="Развернуть панель"
        >
          <img
            :src="isMiniLogoHovered ? '/open_panel_icon.svg' : '/wavescan_panel_mini_logo.svg'"
            alt="wavescan"
            class="w-8 h-8 transition-all duration-200"
          />
        </button>
        <img
          v-else
          src="/wavescan_panel_mini_logo.svg"
          alt="wavescan"
          class="w-8 h-8 flex-shrink-0"
        />
        <img
          v-if="!isCollapsed"
          src="/wavescan_panel_text_logo.svg"
          alt="wavescan"
          class="h-4 ml-2 w-auto whitespace-nowrap hidden sm:inline"
        />
        <button
          v-if="!isCollapsed"
          @click="toggleSidebar"
          class="w-5 h-5 ml-1 opacity-75 hover:opacity-100 transition-opacity flex-shrink-0 flex items-center justify-center"
          title="Свернуть панель"
        >
          <img src="/close_panel_icon.svg" alt="toggle" class="w-4 h-4 rotate-180" />
        </button>
      </div>
    </div>

    <!-- Навигация -->
    <nav class="space-y-2 px-3 mb-8">
      <RouterLink
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        :class="[
          'nav-link',
          isCollapsed ? 'nav-link-collapsed' : 'justify-start'
        ]"
        :title="isCollapsed ? item.label : ''"
      >
        <div class="relative flex-shrink-0">
          <img :src="item.icon" :alt="item.label" class="w-5 h-5" />
          <span 
            v-if="item.to === '/chat' && appStore.unreadChatMessages > 0"
            class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#A19EFF] rounded-full"
          />
        </div>
        <span 
          :class="[
            'transition-all duration-300 whitespace-nowrap',
            isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100 hidden sm:inline'
          ]"
        >
          {{ item.label }}
        </span>
      </RouterLink>
    </nav>

    <!-- Профиль -->
    <div :class="['mt-auto py-4 mb-3', isCollapsed ? 'px-3' : 'px-3 sm:px-4']">
      <div
        v-if="!isCollapsed"
        class="mb-3 pb-3 border-b border-[#2a2d36] hidden sm:block"
      >
        <p class="text-base font-medium text-dark-200 truncate px-2">
          {{ appStore.currentUser?.username || 'User' }}
        </p>
      </div>
      <button
        @click="logout"
        :class="[
          'w-full flex items-center text-[#d1d5de] hover:text-white transition-all duration-300 group overflow-hidden bg-transparent border-0',
          isCollapsed ? 'justify-start px-2 py-2' : 'justify-start gap-2 px-2 py-2'
        ]"
        :title="isCollapsed ? 'Выйти из системы' : ''"
      >
        <img src="/exit_icon.svg" alt="logout" class="w-5 h-5 transition-transform group-hover:translate-x-0.5 flex-shrink-0" />
        <span 
          v-if="!isCollapsed"
          :class="[
            'font-medium whitespace-nowrap hidden sm:inline transition-opacity duration-300 delay-100',
            isCollapsed ? 'opacity-0' : 'opacity-100'
          ]"
        >
          Выйти
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAppStore } from '@/stores/app'
import { useRouter } from 'vue-router'

const appStore = useAppStore()
const router = useRouter()
const isMiniLogoHovered = ref(false)
const isCollapsed = computed({
  get: () => appStore.sidebarCollapsed,
  set: (value) => { appStore.sidebarCollapsed = value }
})

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const expandSidebar = () => {
  isMiniLogoHovered.value = false
  isCollapsed.value = false
}

const logout = async () => {
  await appStore.logout()
  router.push('/login')
}

const menuItems = [
  {
    to: '/chat',
    label: 'Чат',
    icon: '/chat_panel_icon.svg',
  },
  {
    to: '/history',
    label: 'История',
    icon: '/history_panel_icon.svg',
  },
  {
    to: '/statistics',
    label: 'Статистика',
    icon: '/stats_panel_icon.svg',
  },
  {
    to: '/config',
    label: 'Конфиг',
    icon: '/config_panel_icon.svg',
  },
]
</script>

<style scoped>
.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-left: 0.75rem;
  padding-right: 0.75rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
  color: #d2d4dc;
  border-radius: 1rem;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: #2a2d37;
  color: #ffffff;
}

.nav-link.router-link-active {
  background: #2b2e37;
  color: #ffffff;
  font-weight: 500;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
}

.nav-link-collapsed {
  justify-content: flex-start;
  gap: 0;
  width: 100%;
  height: 3rem;
}
</style>
