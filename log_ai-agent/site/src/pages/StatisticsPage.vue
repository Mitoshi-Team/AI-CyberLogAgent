<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">Статистика</h1>
        <p class="text-dark-400">Аналитика и тренды инцидентов</p>
      </div>

      <!-- Основные метрики -->
      <div class="grid grid-cols-2 gap-6 mb-8">
        <div class="card">
          <h2 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
            </svg>
            Распределение по типам
          </h2>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between mb-2">
                <span class="text-dark-400">Критичные</span>
                <span class="font-semibold text-danger-400">{{ appStore.statistics.criticalCount }}</span>
              </div>
              <div class="bg-dark-800/50 rounded-full h-2 overflow-hidden">
                <div
                  class="bg-gradient-to-r from-danger-600 to-danger-500 h-2 rounded-full transition-all duration-500"
                  :style="{ width: widthPercent('critical') + '%' }"
                />
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-2">
                <span class="text-dark-400">Подозрительные</span>
                <span class="font-semibold text-warning-400">{{ appStore.statistics.suspiciousCount }}</span>
              </div>
              <div class="bg-dark-800/50 rounded-full h-2 overflow-hidden">
                <div
                  class="bg-gradient-to-r from-warning-600 to-warning-500 h-2 rounded-full transition-all duration-500"
                  :style="{ width: widthPercent('warning') + '%' }"
                />
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-2">
                <span class="text-dark-400">Нормальные</span>
                <span class="font-semibold text-success-400">{{ appStore.statistics.normalCount }}</span>
              </div>
              <div class="bg-dark-800/50 rounded-full h-2 overflow-hidden">
                <div
                  class="bg-gradient-to-r from-success-600 to-success-500 h-2 rounded-full transition-all duration-500"
                  :style="{ width: widthPercent('normal') + '%' }"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <h2 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
            </svg>
            Основные источники
          </h2>
          <div class="space-y-3">
            <div class="flex justify-between items-center p-3 bg-dark-800/30 rounded-lg border border-dark-800 hover:border-dark-700 transition-colors">
              <span class="text-dark-300">SSH Log</span>
              <span class="badge badge-critical">5 инцидентов</span>
            </div>
            <div class="flex justify-between items-center p-3 bg-dark-800/30 rounded-lg border border-dark-800 hover:border-dark-700 transition-colors">
              <span class="text-dark-300">Database Log</span>
              <span class="badge badge-warning">3 инцидента</span>
            </div>
            <div class="flex justify-between items-center p-3 bg-dark-800/30 rounded-lg border border-dark-800 hover:border-dark-700 transition-colors">
              <span class="text-dark-300">Application Log</span>
              <span class="badge badge-info">2 инцидента</span>
            </div>
            <div class="flex justify-between items-center p-3 bg-dark-800/30 rounded-lg border border-dark-800 hover:border-dark-700 transition-colors">
              <span class="text-dark-300">Network Log</span>
              <span class="badge badge-success">1 инцидент</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Временная шкала -->
      <div class="card">
        <h2 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
          </svg>
          Активность по дням
        </h2>
        <div class="h-64 flex items-end justify-center gap-3">
          <div v-for="(value, index) in dailyActivity" :key="index" class="flex flex-col items-center gap-2 group">
            <div
              class="w-10 bg-gradient-to-t from-primary-600 to-primary-500 rounded-t-lg hover:from-primary-500 hover:to-primary-400 transition-all duration-300 shadow-lg shadow-primary-500/20 group-hover:shadow-primary-500/40 cursor-pointer relative overflow-hidden"
              :style="{ height: value * 20 + 'px' }"
            >
              <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
            <span class="text-xs text-dark-500 group-hover:text-dark-400 transition-colors">{{ getDayName(index) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const dailyActivity = [5, 8, 3, 7, 6, 9, 4]

const widthPercent = (type) => {
  const total = appStore.statistics.totalIncidents
  if (total === 0) return 0

  if (type === 'critical') {
    return (appStore.statistics.criticalCount / total) * 100
  } else if (type === 'warning') {
    return (appStore.statistics.suspiciousCount / total) * 100
  } else {
    return (appStore.statistics.normalCount / total) * 100
  }
}

const getDayName = (index) => {
  const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
  return days[index]
}
</script>
