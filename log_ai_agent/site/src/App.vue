<template>
  <div id="app" class="min-h-screen bg-[#202020]">

    <div v-if="appStore.isAuthenticated" class="flex relative">
      <Sidebar />
      <main 
        :class="[
          'flex-1 transition-all duration-300',
          appStore.sidebarCollapsed ? 'ml-20' : 'ml-20 sm:ml-64'
        ]"
      >
        <RouterView />
      </main>
    </div>
    <div v-else>
      <RouterView />
    </div>

    <!-- Уведомления -->
    <NotificationStack />
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import NotificationStack from '@/components/NotificationStack.vue'
import websocketService from '@/services/websocket'

const appStore = useAppStore()
const route = useRoute()
const websocketEnabled = import.meta.env.VITE_ENABLE_WEBSOCKET !== 'false'

const handleWebsocketMessage = (data) => {
  if (data.type === 'incident') {
    appStore.addIncident(data.incident)
    return
  }

  if (data.type === 'report_created') {
    appStore.notifyReportsUpdated(data)
    return
  }

  if (data.type === 'chat_response' && data.user_id === appStore.currentUser?.id) {
    const isOnChatPage = route.path === '/chat'
    const isTabVisible = document.visibilityState === 'visible'

    if (!isOnChatPage || !isTabVisible) {
      appStore.addUnreadChatMessage()
      appStore.addNotification('Новое сообщение от ассистента в чате', 'info', 5000, true)
    }
  }
}

const connectWebsocket = () => {
  if (!websocketEnabled || !appStore.isAuthenticated) {
    return
  }

  websocketService.connect().catch((error) => {
    console.warn('WebSocket connection failed:', error)
    // Не показываем уведомление, т.к. WebSocket не критичен для работы
  })
}

onMounted(() => {
  // Попытка восстановления сессии
  if (appStore.token) {
    appStore.isAuthenticated = true
  }

  websocketService.on('message', handleWebsocketMessage)
  connectWebsocket()
})

watch(
  () => appStore.isAuthenticated,
  (isAuthenticated) => {
    if (!websocketEnabled) {
      return
    }

    if (isAuthenticated) {
      connectWebsocket()
      return
    }

    websocketService.disconnect()
  }
)

onUnmounted(() => {
  websocketService.off('message', handleWebsocketMessage)
  websocketService.disconnect()
})
</script>

<style scoped>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
