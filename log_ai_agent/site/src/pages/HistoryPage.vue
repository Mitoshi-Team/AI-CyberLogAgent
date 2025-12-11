<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">История инцидентов</h1>
        <p class="text-dark-400">Архив всех обнаруженных инцидентов с фильтрацией по датам</p>
      </div>

      <!-- Фильтры -->
      <div class="card mb-6">
        <div class="flex gap-4 items-start">
          <div class="grid grid-cols-4 gap-4 flex-1">
            <div>
              <label class="block text-sm font-medium text-dark-300 mb-2">С даты</label>
              <input v-model="dateFrom" type="date" class="input" @change="loadHistory" />
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-300 mb-2">По дату</label>
              <input v-model="dateTo" type="date" class="input" @change="loadHistory" />
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-300 mb-2">Уровень серьезности</label>
              <select v-model="filterSeverityId" class="input" @change="loadHistory">
                <option value="">Все уровни</option>
                <option v-for="level in severityLevels" :key="level.id" :value="level.id">
                  {{ level.name }}
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-300 mb-2">Тип угрозы</label>
              <select v-model="filterThreatId" class="input" @change="loadHistory">
                <option value="">Все типы</option>
                <option v-for="threat in threatTypes" :key="threat.id" :value="threat.id">
                  {{ threat.name }}
                </option>
              </select>
            </div>
          </div>
          <div class="pt-7">
            <button
              @click="resetFilters"
              class="p-2.5 bg-dark-800 hover:bg-dark-700 text-dark-400 hover:text-white rounded-lg transition-colors group"
              title="Сбросить фильтры"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Таблица истории -->
      <div class="card overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-dark-800">
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Дата и время</th>
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Тип угрозы</th>
              <th class="text-left py-3 px-4 font-semibold text-dark-300">Уровень серьезности</th>
              <th class="text-right py-3 px-4 font-semibold text-dark-300">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="report in historyData"
              :key="report.id"
              class="border-b border-dark-800 hover:bg-dark-800/30 transition-colors"
            >
              <td class="py-3 px-4 text-sm text-dark-400">{{ formatDateTime(report.created_at) }}</td>
              <td class="py-3 px-4 text-sm text-dark-400">{{ report.threat_name }}</td>
              <td class="py-3 px-4">
                <span :class="['badge', getSeverityBadgeClass(report.severity_name)]">
                  {{ report.severity_name }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <button
                  @click="viewDetails(report.id)"
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

        <div v-if="loading" class="text-center py-12">
          <p class="text-dark-500">Загрузка данных...</p>
        </div>

        <div v-else-if="historyData.length === 0" class="text-center py-12">
          <div class="w-16 h-16 bg-dark-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-dark-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clip-rule="evenodd"/>
            </svg>
          </div>
          <p class="text-dark-500">Инциденты не найдены</p>
        </div>
      </div>

      <!-- Пагинация -->
      <div v-if="totalPages > 0" class="flex items-center justify-between mt-6">
        <p class="text-sm text-dark-400">
          Страница <span class="text-white font-semibold">{{ currentPage }}</span> из <span class="text-white font-semibold">{{ totalPages }}</span>
        </p>
        <div class="flex items-center gap-2">
          <button
            @click="previousPage"
            :disabled="currentPage === 1"
            class="p-2 rounded-lg transition-colors"
            :class="currentPage === 1 ? 'bg-dark-800 text-dark-600 cursor-not-allowed' : 'bg-dark-800 hover:bg-dark-700 text-white'"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
          </button>
          <button
            @click="nextPage"
            :disabled="currentPage === totalPages"
            class="p-2 rounded-lg transition-colors"
            :class="currentPage === totalPages ? 'bg-dark-800 text-dark-600 cursor-not-allowed' : 'bg-dark-800 hover:bg-dark-700 text-white'"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно деталей отчета -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-dark-900 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-dark-800">
        <!-- Заголовок модального окна -->
        <div class="sticky top-0 bg-dark-900 border-b border-dark-800 px-6 py-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Детали инцидента</h2>
          <button
            @click="closeModal"
            class="text-dark-400 hover:text-white transition-colors p-1"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Содержимое модального окна -->
        <div v-if="loadingModal" class="p-8 text-center text-dark-400">
          Загрузка данных...
        </div>
        <div v-else-if="selectedReport" class="p-6 space-y-6">
          <!-- Дата и время -->
          <div>
            <h3 class="text-sm font-semibold text-dark-400 mb-2">Дата и время</h3>
            <p class="text-white">{{ formatDateTime(selectedReport.created_at) }}</p>
          </div>

          <!-- Уровень серьезности -->
          <div>
            <h3 class="text-sm font-semibold text-dark-400 mb-2">Уровень серьезности</h3>
            <p class="text-white">{{ selectedReport.severity_name }}</p>
          </div>

          <!-- Тип угрозы -->
          <div>
            <h3 class="text-sm font-semibold text-dark-400 mb-2">Тип угрозы</h3>
            <p class="text-white">{{ selectedReport.threat_name }}</p>
          </div>

          <!-- Описание -->
          <div>
            <h3 class="text-sm font-semibold text-dark-400 mb-2">Описание</h3>
            <div class="text-white markdown-content" v-html="renderMarkdown(selectedReport.description)"></div>
          </div>

          <!-- Логи -->
          <div>
            <h3 class="text-sm font-semibold text-dark-400 mb-2">Логи</h3>
            <div class="bg-dark-800/50 rounded-lg p-4 overflow-x-auto">
              <pre class="text-sm text-dark-300 font-mono whitespace-pre-wrap">{{ selectedReport.file_content }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { reports } from '../services/api'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const router = useRouter()

const dateFrom = ref('')
const dateTo = ref('')
const filterSeverityId = ref('')
const filterThreatId = ref('')

const loading = ref(false)
const historyData = ref([])
const severityLevels = ref([])
const threatTypes = ref([])

// Пагинация
const currentPage = ref(1)
const pageSize = ref(10)
const totalRecords = ref(0)
const totalPages = ref(0)

// Модальное окно
const showModal = ref(false)
const loadingModal = ref(false)
const selectedReport = ref(null)

// Рендер markdown с санитизацией
const renderMarkdown = (text) => {
  if (!text) return ''
  const rawHtml = marked.parse(text)
  return DOMPurify.sanitize(rawHtml)
}

// Загрузка фильтров
async function loadFilters() {
  try {
    const response = await reports.filters()
    severityLevels.value = response.data.severity_levels
    threatTypes.value = response.data.threat_types
  } catch (error) {
    console.error('Ошибка загрузки фильтров:', error)
  }
}

// Загрузка истории отчетов
async function loadHistory() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    
    if (dateFrom.value) {
      const date = new Date(dateFrom.value)
      date.setHours(0, 0, 0, 0)
      params.date_from = date.toISOString()
    }
    
    if (dateTo.value) {
      const date = new Date(dateTo.value)
      date.setHours(23, 59, 59, 999)
      params.date_to = date.toISOString()
    }
    
    if (filterSeverityId.value) {
      params.severity_level_id = filterSeverityId.value
    }
    
    if (filterThreatId.value) {
      params.threat_type_id = filterThreatId.value
    }

    const response = await reports.history(params)
    historyData.value = response.data.data
    totalRecords.value = response.data.total
    totalPages.value = response.data.total_pages
  } catch (error) {
    console.error('Ошибка загрузки истории:', error)
  } finally {
    loading.value = false
  }
}

// Переход на предыдущую страницу
const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    loadHistory()
  }
}

// Переход на следующую страницу
const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    loadHistory()
  }
}

// Форматирование даты и времени
const formatDateTime = (dateStr) => {
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${day}.${month}.${year} ${hours}:${minutes}`
}

// Обрезка описания до 50 символов
const truncateDescription = (text) => {
  if (!text) return ''
  return text.length > 50 ? text.substring(0, 50) + '...' : text
}

// Получение класса для badge уровня серьезности
const getSeverityBadgeClass = (severityName) => {
  const classes = {
    'Критический': 'badge-danger',
    'Высокий': 'badge-warning',
    'Средний': 'badge-primary',
    'Низкий': 'badge-success',
  }
  return classes[severityName] || 'badge-secondary'
}

// Сброс всех фильтров
const resetFilters = () => {
  dateFrom.value = ''
  dateTo.value = ''
  filterSeverityId.value = ''
  filterThreatId.value = ''
  currentPage.value = 1
  loadHistory()
}

// Открытие модального окна с деталями отчета
const viewDetails = async (id) => {
  showModal.value = true
  loadingModal.value = true
  selectedReport.value = null

  try {
    const response = await reports.details(id)
    selectedReport.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки деталей отчета:', error)
  } finally {
    loadingModal.value = false
  }
}

// Закрытие модального окна
const closeModal = () => {
  showModal.value = false
  selectedReport.value = null
}

onMounted(async () => {
  await loadFilters()
  await loadHistory()
})
</script>
