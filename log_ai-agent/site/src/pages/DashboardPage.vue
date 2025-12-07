<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <!-- Заголовок -->
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">Панель управления</h1>
        <p class="text-dark-400">Обзор текущего состояния системы и активных инцидентов</p>
      </div>

      <!-- Статистика -->
      <div class="grid grid-cols-4 gap-4 mb-8">
        <div class="card group hover:border-primary-500/50 transition-all duration-300">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-dark-400 text-sm mb-1">Всего инцидентов</p>
              <p class="text-3xl font-bold text-white">
                {{ appStore.statistics.totalIncidents }}
              </p>
            </div>
            <div class="w-12 h-12 bg-primary-500/10 rounded-xl flex items-center justify-center group-hover:bg-primary-500/20 transition-colors">
              <svg class="w-7 h-7 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v2h8v-2zM2 15a4 4 0 008 0v2H0v-2z" clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="card group border-l-4 border-danger-500 hover:shadow-2xl hover:shadow-danger-500/20 transition-all duration-300">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-dark-400 text-sm mb-1">Критичные</p>
              <p class="text-3xl font-bold text-danger-400">
                {{ appStore.statistics.criticalCount }}
              </p>
            </div>
            <div class="w-12 h-12 bg-danger-500/10 rounded-xl flex items-center justify-center group-hover:bg-danger-500/20 transition-colors">
              <svg class="w-7 h-7 text-danger-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="card group border-l-4 border-warning-500 hover:shadow-2xl hover:shadow-warning-500/20 transition-all duration-300">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-dark-400 text-sm mb-1">Подозрительные</p>
              <p class="text-3xl font-bold text-warning-400">
                {{ appStore.statistics.suspiciousCount }}
              </p>
            </div>
            <div class="w-12 h-12 bg-warning-500/10 rounded-xl flex items-center justify-center group-hover:bg-warning-500/20 transition-colors">
              <svg class="w-7 h-7 text-warning-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="card group border-l-4 border-success-500 hover:shadow-2xl hover:shadow-success-500/20 transition-all duration-300">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-dark-400 text-sm mb-1">Нормально</p>
              <p class="text-3xl font-bold text-success-400">
                {{ appStore.statistics.normalCount }}
              </p>
            </div>
            <div class="w-12 h-12 bg-success-500/10 rounded-xl flex items-center justify-center group-hover:bg-success-500/20 transition-colors">
              <svg class="w-7 h-7 text-success-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Недавние инциденты -->
      <div class="card">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-white">Недавние инциденты</h2>
          <RouterLink to="/incidents" class="text-primary-400 hover:text-primary-300 text-sm font-medium transition-colors">
            Показать все →
          </RouterLink>
        </div>

        <div class="space-y-3">
          <div
            v-for="incident in appStore.incidents.slice(0, 3)"
            :key="incident.id"
            class="border border-dark-800 bg-dark-800/30 rounded-lg p-4 hover:border-dark-700 hover:bg-dark-800/50 transition-all duration-300 cursor-pointer group"
          >
            <div class="flex items-start justify-between mb-2">
              <div class="flex-1">
                <h3 class="font-semibold text-white group-hover:text-primary-400 transition-colors">{{ incident.title }}</h3>
                <p class="text-sm text-dark-400 mt-1">{{ incident.description }}</p>
              </div>
              <span :class="['badge', `badge-${incident.severity}`, 'ml-4 flex-shrink-0']">
                {{ severityLabel(incident.severity) }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs text-dark-500">
              <span class="flex items-center gap-1">
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 9a1 1 0 112 0v3a1 1 0 11-2 0V9zm1-5a1 1 0 100 2 1 1 0 000-2z" clip-rule="evenodd"/>
                </svg>
                {{ incident.source }}
              </span>
              <span class="flex items-center gap-1">
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
                </svg>
                {{ formatTime(incident.timestamp) }}
              </span>
            </div>
          </div>

          <div v-if="appStore.incidents.length === 0" class="text-center py-12">
            <div class="w-16 h-16 bg-dark-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-dark-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
            </div>
            <p class="text-dark-500">Инциденты не обнаружены</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { onMounted } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

const appStore = useAppStore()

onMounted(() => {
  appStore.loadIncidents()
})

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
