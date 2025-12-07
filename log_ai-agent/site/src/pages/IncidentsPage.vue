<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">Инциденты</h1>
        <p class="text-dark-400">Полный список обнаруженных инцидентов с фильтрацией</p>
      </div>

      <!-- Поиск -->
      <div class="mb-6">
        <input
          v-model="searchQuery"
          type="text"
          class="input w-full"
          placeholder="Поиск инцидентов по названию..."
        />
      </div>

      <!-- Список инцидентов -->
      <div class="space-y-3">
        <div
          v-for="incident in filteredIncidents"
          :key="incident.id"
          @click="navigateToIncident(incident.id)"
          class="card cursor-pointer hover:border-primary-500/50 hover:shadow-xl hover:shadow-primary-500/10 transition-all duration-300 group"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <h3 class="font-semibold text-white group-hover:text-primary-400 transition-colors">{{ incident.title }}</h3>
                <span :class="['badge', `badge-${incident.severity}`]">
                  {{ severityLabel(incident.severity) }}
                </span>
              </div>
              <p class="text-dark-400 text-sm mb-3">{{ incident.description }}</p>
              <div class="flex items-center gap-6 text-xs text-dark-500">
                <span class="flex items-center gap-1">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 9a1 1 0 112 0v3a1 1 0 11-2 0V9zm1-5a1 1 0 100 2 1 1 0 000-2z" clip-rule="evenodd"/>
                  </svg>
                  Источник: {{ incident.source }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
                  </svg>
                  {{ formatTime(incident.timestamp) }}
                </span>
                <span v-if="incident.details" class="font-medium text-dark-400 flex items-center gap-1">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
                    <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"/>
                  </svg>
                  {{ Object.keys(incident.details).length }} параметров
                </span>
              </div>
            </div>
            <svg class="w-5 h-5 text-dark-600 group-hover:text-primary-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </div>
        </div>

        <div v-if="filteredIncidents.length === 0" class="card text-center py-12">
          <div class="w-16 h-16 bg-dark-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-dark-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clip-rule="evenodd"/>
            </svg>
          </div>
          <p class="text-dark-500">Инциденты не найдены</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

const router = useRouter()
const appStore = useAppStore()

const searchQuery = ref('')

const filteredIncidents = computed(() => {
  return appStore.incidents.filter((incident) => {
    const matchSearch = !searchQuery.value || incident.title.toLowerCase().includes(searchQuery.value.toLowerCase())
    return matchSearch
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

const formatTime = (date) => {
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: ru })
}

const navigateToIncident = (id) => {
  router.push({ name: 'IncidentDetail', params: { id } })
}
</script>
