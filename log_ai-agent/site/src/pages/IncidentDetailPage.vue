<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <!-- Навигация назад -->
      <button
        @click="goBack"
        class="flex items-center gap-2 text-primary-400 hover:text-primary-300 mb-6 transition-colors group"
      >
        <svg class="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        Назад
      </button>

      <div v-if="incident" class="space-y-6">
        <!-- Заголовок -->
        <div class="card">
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <h1 class="text-3xl font-bold text-white mb-2">{{ incident.title }}</h1>
              <p class="text-dark-400">{{ incident.description }}</p>
            </div>
            <span :class="['badge text-lg px-4 py-2 flex-shrink-0 ml-4', `badge-${incident.severity}`]">
              {{ severityLabel(incident.severity) }}
            </span>
          </div>
          <div class="flex items-center gap-6 text-sm text-dark-400">
            <span class="flex items-center gap-1">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 9a1 1 0 112 0v3a1 1 0 11-2 0V9zm1-5a1 1 0 100 2 1 1 0 000-2z" clip-rule="evenodd"/>
              </svg>
              Источник: <strong class="text-dark-300">{{ incident.source }}</strong>
            </span>
            <span class="flex items-center gap-1">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
              </svg>
              {{ formatTime(incident.timestamp) }}
            </span>
          </div>
        </div>

        <!-- Детали -->
        <div class="grid grid-cols-2 gap-6">
          <div class="card">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
                <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"/>
              </svg>
              Детали инцидента
            </h2>
            <div class="space-y-3">
              <div
                v-for="(value, key) in incident.details"
                :key="key"
                class="flex justify-between items-center border-b border-dark-800 pb-3"
              >
                <span class="text-dark-400 capitalize">{{ key }}</span>
                <span class="font-semibold text-dark-200">{{ value }}</span>
              </div>
            </div>
          </div>

          <!-- AI Анализ -->
          <div class="card">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"/>
                <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"/>
              </svg>
              AI Анализ
            </h2>
            <div class="bg-dark-800/50 border border-dark-700 rounded-lg p-4 text-sm space-y-3">
              <p class="text-dark-300 flex items-start gap-2">
                <span class="text-primary-400 text-lg flex-shrink-0">🔍</span>
                <span><strong class="text-white">Анализ:</strong> Детектор обнаружил повторяющийся паттерн несанкционированного доступа.</span>
              </p>
              <p class="text-dark-300 flex items-start gap-2">
                <span class="text-warning-400 text-lg flex-shrink-0">⚠️</span>
                <span><strong class="text-white">Риск:</strong> Средний - требуется расследование и блокировка источника.</span>
              </p>
              <p class="text-dark-300 flex items-start gap-2">
                <span class="text-success-400 text-lg flex-shrink-0">✅</span>
                <span><strong class="text-white">Рекомендация:</strong> Активировать двухфакторную аутентификацию и мониторить IP.</span>
              </p>
            </div>
          </div>
        </div>

        <!-- Действия -->
        <div class="card">
          <div class="flex gap-3">
            <button class="btn btn-primary">
              Принять меры
            </button>
            <button class="btn btn-secondary">
              Пометить как решенное
            </button>
            <button class="btn btn-secondary">
              Экспортировать отчет
            </button>
          </div>
        </div>
      </div>

      <div v-else class="card text-center py-12">
        <div class="w-16 h-16 bg-dark-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-dark-600" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
        </div>
        <p class="text-dark-500">Инцидент не найден</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const incident = computed(() => {
  return appStore.incidents.find((i) => i.id === parseInt(route.params.id))
})

const goBack = () => {
  router.back()
}

const severityLabel = (severity) => {
  const labels = {
    critical: 'Критичный',
    warning: 'Предупреждение',
    normal: 'Нормально',
  }
  return labels[severity] || severity
}

const formatTime = (date) => {
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: ru })
}
</script>
