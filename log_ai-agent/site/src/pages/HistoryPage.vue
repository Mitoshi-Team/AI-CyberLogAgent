<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">История инцидентов</h1>
        <p class="text-dark-400">Архив всех обнаруженных инцидентов с фильтрацией по датам</p>
      </div>

      <!-- Фильтры -->
      <div class="card mb-6">
        <div class="grid grid-cols-4 gap-4">
          <div>
            <label class="block text-sm font-medium text-dark-300 mb-2">С даты</label>
            <input v-model="dateFrom" type="date" class="input" />
          </div>
          <div>
            <label class="block text-sm font-medium text-dark-300 mb-2">По дату</label>
            <input v-model="dateTo" type="date" class="input" />
          </div>
          <div>
            <label class="block text-sm font-medium text-dark-300 mb-2">Тип</label>
            <select v-model="filterSeverity" class="input">
              <option value="">Все типы</option>
              <option value="critical">Критичные</option>
              <option value="warning">Предупреждения</option>
              <option value="normal">Нормальные</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-dark-300 mb-2">Источник</label>
            <select v-model="filterSource" class="input">
              <option value="">Все источники</option>
              <option value="SSH Log">SSH Log</option>
              <option value="Database Log">Database Log</option>
              <option value="Application Log">Application Log</option>
              <option value="Network Log">Network Log</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Таблица истории -->
      <div class="card overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-dark-800">
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Дата и время</th>
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Название</th>
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Источник</th>
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Тип</th>
              <th class="text-right py-3 px-4 font-semibold text-dark-300">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="incident in filteredHistory"
              :key="incident.id"
              class="border-b border-dark-800 hover:bg-dark-800/30 transition-colors"
            >
              <td class="py-3 px-4 text-sm text-dark-400">{{ formatDateTime(incident.timestamp) }}</td>
              <td class="py-3 px-4 text-sm font-medium text-white">{{ incident.title }}</td>
              <td class="py-3 px-4 text-sm text-dark-400">{{ incident.source }}</td>
              <td class="py-3 px-4">
                <span :class="['badge', `badge-${incident.severity}`]">
                  {{ severityLabel(incident.severity) }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <button
                  @click="viewDetails(incident.id)"
                  class="text-primary-400 hover:text-primary-300 font-medium text-sm transition-colors group"
                >
                  <span>Просмотр</span>
                  <svg class="w-4 h-4 inline-block ml-1 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filteredHistory.length === 0" class="text-center py-12">
          <div class="w-16 h-16 bg-dark-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-dark-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clip-rule="evenodd"/>
            </svg>
          </div>
          <p class="text-dark-500">Инциденты не найдены</p>
        </div>
      </div>

      <!-- Пагинация -->
      <div v-if="filteredHistory.length > 0" class="flex items-center justify-between mt-6">
        <p class="text-sm text-dark-400">
          Показано <span class="text-white font-semibold">{{ filteredHistory.length }}</span> из <span class="text-white font-semibold">{{ historyData.length }}</span> инцидентов
        </p>
        <div class="flex gap-2">
          <button class="btn btn-secondary btn-sm hover:border-primary-500/50 transition-all">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            Предыдущая
          </button>
          <button class="btn btn-secondary btn-sm hover:border-primary-500/50 transition-all">
            Следующая
            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { format } from 'date-fns'

const router = useRouter()

const dateFrom = ref('')
const dateTo = ref('')
const filterSeverity = ref('')
const filterSource = ref('')

// Имитация исторических данных
const historyData = ref([
  {
    id: 1,
    title: 'Попытка несанкционированного доступа',
    description: 'Обнаружено 15 неудачных попыток входа',
    severity: 'critical',
    status: 'resolved',
    timestamp: new Date(Date.now() - 5 * 60000),
    source: 'SSH Log',
  },
  {
    id: 2,
    title: 'Аномальная активность базы данных',
    description: 'Высокий объём запросов к БД',
    severity: 'warning',
    status: 'open',
    timestamp: new Date(Date.now() - 15 * 60000),
    source: 'Database Log',
  },
  {
    id: 3,
    title: 'Необычный паттерн сетевого трафика',
    description: 'Обнаружена аномалия в сетевом трафике',
    severity: 'warning',
    status: 'resolved',
    timestamp: new Date(Date.now() - 24 * 60 * 60000),
    source: 'Network Log',
  },
  {
    id: 4,
    title: 'Ошибка приложения',
    description: 'Множественные ошибки в логах приложения',
    severity: 'normal',
    status: 'resolved',
    timestamp: new Date(Date.now() - 48 * 60 * 60000),
    source: 'Application Log',
  },
])

const filteredHistory = computed(() => {
  return historyData.value.filter((incident) => {
    const matchSeverity = !filterSeverity.value || incident.severity === filterSeverity.value
    const matchSource = !filterSource.value || incident.source === filterSource.value
    const matchDateFrom = !dateFrom.value || new Date(incident.timestamp) >= new Date(dateFrom.value)
    const matchDateTo = !dateTo.value || new Date(incident.timestamp) <= new Date(dateTo.value)

    return matchSeverity && matchSource && matchDateFrom && matchDateTo
  })
})

const severityLabel = (severity) => {
  const labels = {
    critical: 'Критичный',
    warning: 'Предупреждение',
    normal: 'Нормально',
  }
  return labels[severity] || severity
}

const statusLabel = (status) => {
  const labels = {
    open: 'Открытый',
    resolved: 'Решенный',
  }
  return labels[status] || status
}

const formatDateTime = (date) => {
  return format(new Date(date), 'dd.MM.yyyy HH:mm')
}

const viewDetails = (id) => {
  router.push({ name: 'IncidentDetail', params: { id } })
}
</script>
