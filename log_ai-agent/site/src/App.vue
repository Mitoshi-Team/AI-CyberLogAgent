<template>
  <div id="app" class="min-h-screen bg-dark-950">
    <!-- Фоновые эффекты -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-0 left-1/4 w-96 h-96 bg-primary-500/5 rounded-full blur-3xl"></div>
      <div class="absolute bottom-0 right-1/4 w-96 h-96 bg-primary-600/5 rounded-full blur-3xl"></div>
    </div>

    <div v-if="appStore.isAuthenticated" class="flex relative">
      <Sidebar />
      <main class="flex-1 ml-64">
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
import { onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import NotificationStack from '@/components/NotificationStack.vue'
import websocketService from '@/services/websocket'

const appStore = useAppStore()

onMounted(() => {
  // Попытка восстановления сессии
  if (appStore.token) {
    appStore.isAuthenticated = true
  }

  // Подключение к WebSocket для получения уведомлений
  if (appStore.isAuthenticated) {
    websocketService.connect().catch(console.error)

    websocketService.on('message', (data) => {
      if (data.type === 'incident') {
        appStore.addIncident(data.incident)
      }
    })

    websocketService.on('error', (error) => {
      appStore.addNotification('Ошибка подключения к серверу', 'danger')
    })
  }
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
