<template>
  <section class="assistant-loading-page" aria-live="polite" aria-busy="true">
    <div class="assistant-loading-card">
      <div class="assistant-loader" aria-hidden="true"></div>
      <h1 class="assistant-loading-title">Пожалуйста, подождите, ассистент загружается</h1>
      <p class="assistant-loading-subtitle">Инициализируем AI-пайплайн и подготавливаем сервис к работе...</p>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { checkBackendReady } from '@/services/backendReadiness'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

let intervalId = null

const resolveRedirectPath = () => {
  const queryRedirect = route.query.redirect
  if (typeof queryRedirect === 'string' && queryRedirect.startsWith('/')) {
    return queryRedirect
  }

  return appStore.isAuthenticated ? '/' : '/login'
}

const tryContinue = async () => {
  const ready = await checkBackendReady({ force: true })
  if (!ready) {
    return
  }

  router.replace(resolveRedirectPath())
}

onMounted(() => {
  tryContinue()
  intervalId = window.setInterval(tryContinue, 2000)
})

onBeforeUnmount(() => {
  if (intervalId) {
    window.clearInterval(intervalId)
  }
})
</script>

<style scoped>
.assistant-loading-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: #202020;
}

.assistant-loading-card {
  width: min(92vw, 620px);
  border: 1px solid #3C3C3C;
  border-radius: 18px;
  padding: 42px 28px;
  background: #252525;
  text-align: center;
}

.assistant-loader {
  width: 54px;
  height: 54px;
  margin: 0 auto 22px;
  border: 4px solid #7C7C7C;
  border-top-color: #8B87F4;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.assistant-loading-title {
  margin: 0;
  color: #eaf4ff;
  font-size: 22px;
  line-height: 1.2;
  font-weight: 600;
}

.assistant-loading-subtitle {
  margin: 14px 0 0;
  color: rgba(217, 233, 248, 0.82);
  font-size: 18px;
  line-height: 1.45;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
