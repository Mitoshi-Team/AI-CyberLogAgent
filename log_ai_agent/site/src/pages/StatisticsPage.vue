<template>
  <div class="pt-4 sm:pt-6 md:pt-8 pb-4 sm:pb-6 md:pb-8">
    <div class="px-4 sm:px-6 md:px-8">
      <div class="mb-6 md:mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-2">Статистика</h1>
          <p class="text-sm sm:text-base text-[#7f8799]">График и распределение по уровням и типам</p>
        </div>
        
        <DatePeriodPicker 
          v-model="selectedPeriod"
          :period-type="periodType"
          @update:period-type="periodType = $event"
          @change="onPeriodChange"
        />
      </div>

      <!-- Временная шкала с выбором периода -->
      <div class="mb-6 rounded-xl border border-[#2d313d] bg-[#252525] p-6 md:mb-8">
        <h2 class="text-base sm:text-lg font-bold text-white mb-4 sm:mb-6 flex items-center gap-2">
          <svg class="w-5 h-5 text-[#8a83ff]" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
          </svg>
          Активность по {{ periodType === 'week' ? 'дням' : 'дням месяца' }}
        </h2>

        <div v-if="loadingActivity" class="text-center py-8 text-[#7f8799] text-sm sm:text-base">
          Загрузка данных активности...
        </div>
        <div v-else class="h-64 sm:h-64 md:h-64 flex items-end justify-center gap-1 sm:gap-2 overflow-x-auto pt-2">
          <div v-for="(item, index) in activityData" :key="index" class="flex flex-col items-center gap-1 sm:gap-2 group flex-shrink-0 relative">
            <div
              class="bg-gradient-to-t from-[#646ff2] to-[#7c74f5] rounded-t-lg hover:from-[#6f79ff] hover:to-[#8f88ff] transition-all duration-300 shadow-lg shadow-[#6d74f0]/20 group-hover:shadow-[#6d74f0]/40 cursor-pointer relative overflow-visible"
              :class="periodType === 'week' ? 'w-8 sm:w-10' : 'w-4 sm:w-6'"
              :style="{ height: Math.max(item.count * 20, 4) + 'px' }"
            >
              <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
            <!-- Подсказка справа для высоких столбиков, сверху для низких -->
            <div 
              v-if="item.count * 20 > 150"
              class="absolute left-full ml-2 top-0 bg-[#252525] text-[#d9dfec] text-xs px-3 py-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-[#2d313d]"
            >
              {{ item.count }} {{ pluralize(item.count, 'инцидент', 'инцидента', 'инцидентов') }}
            </div>
            <div 
              v-else
              class="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-[#252525] text-[#d9dfec] text-xs px-3 py-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-[#2d313d]"
            >
              {{ item.count }} {{ pluralize(item.count, 'инцидент', 'инцидента', 'инцидентов') }}
            </div>
            <span class="text-xs text-[#6d7588] group-hover:text-[#8f97ab] transition-colors">{{ getLabel(index, item.date) }}</span>
          </div>
        </div>
      </div>

      <!-- Блок статистики по уровням серьезности (из БД) -->
      <div class="mb-6 md:mb-8">
        <div class="rounded-xl border border-[#2d313d] bg-[#252525] p-6">
          <h2 class="text-base sm:text-lg font-bold text-white mb-4 sm:mb-6 flex items-center gap-2">
            <svg class="w-5 h-5 text-[#8a83ff]" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
            </svg>
            Уровень серьезности
          </h2>
          <div v-if="loading" class="text-center py-8 text-[#7f8799]">
            Загрузка данных...
          </div>
          <div v-else-if="severityStats.length > 0" class="space-y-3 sm:space-y-4">
            <div v-for="severity in severityStats" :key="severity.id" class="group relative">
              <div class="flex justify-between mb-2">
                <span class="text-sm sm:text-base text-[#919aac]">{{ severity.name }}</span>
                <span class="text-sm sm:text-base font-semibold" :class="getSeverityColor(severity.name)">
                  {{ severity.count }}
                </span>
              </div>
              <div class="bg-[#373737] rounded-full h-2 overflow-hidden relative">
                <div
                  class="h-2 rounded-full transition-all duration-500"
                  :class="getSeverityGradient(severity.name)"
                  :style="{ width: widthPercent(severity.count, totalSeverityCount) + '%' }"
                />
                <!-- Всплывающая подсказка -->
                <div class="absolute -top-10 left-1/2 transform -translate-x-1/2 bg-[#252525] text-[#d9dfec] text-xs px-3 py-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 border border-[#2d313d]">
                  {{ severity.count }} {{ pluralize(severity.count, 'инцидент', 'инцидента', 'инцидентов') }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-8 text-[#7f8799]">
            Нет данных
          </div>
        </div>
      </div>

      <!-- Блок статистики по типам угроз (из БД) -->
      <div class="mb-6 md:mb-8">
        <div class="rounded-xl border border-[#2d313d] bg-[#252525] p-6">
          <h2 class="text-base sm:text-lg font-bold text-white mb-4 sm:mb-6 flex items-center gap-2">
            <svg class="w-5 h-5 text-[#8a83ff]" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
            </svg>
            Тип угрозы
          </h2>
          <div v-if="loading" class="text-center py-8 text-[#7f8799]">
            Загрузка данных...
          </div>
          <div v-else-if="threatStats.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            <div 
              v-for="threat in threatStats" 
              :key="threat.id"
              class="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 bg-[#252525]/65 rounded-lg border border-[#2d313d] hover:border-[#3b4150] transition-colors gap-2"
            >
              <span class="text-sm sm:text-base text-[#c7cedf] break-words">{{ threat.name }}</span>
              <span class="inline-flex items-center px-3 py-1 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap" :class="getThreatBadgeClass(threat.count)">
                {{ threat.count }} {{ pluralize(threat.count, 'инцидент', 'инцидента', 'инцидентов') }}
              </span>
            </div>
          </div>
          <div v-else class="text-center py-8 text-[#7f8799]">
            Нет данных
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statistics } from '@/services/api'
import DatePeriodPicker from '@/components/DatePeriodPicker.vue'

// Состояние загрузки
const loading = ref(true)
const loadingActivity = ref(false)

// Данные из БД
const severityStats = ref([])
const threatStats = ref([])
const activityData = ref([])

// Вычисляемые значения
const totalSeverityCount = ref(0)

// Тип периода и выбранный период
const periodType = ref('week')
const selectedPeriod = ref({
  start: getWeekRange(new Date()).start,
  end: getWeekRange(new Date()).end
})

// Получить диапазон недели
function getWeekRange(date) {
  const day = new Date(date)
  const dayOfWeek = day.getDay()
  const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  
  const monday = new Date(day)
  monday.setDate(day.getDate() + diff)
  monday.setHours(0, 0, 0, 0)
  
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(23, 59, 59, 999)
  
  return { start: monday, end: sunday }
}

// Загрузка данных по уровням серьезности
async function loadSeverityStats() {
  try {
    const response = await statistics.severity(
      formatDateTime(selectedPeriod.value.start),
      formatDateTime(selectedPeriod.value.end)
    )
    severityStats.value = response.data.data
    totalSeverityCount.value = severityStats.value.reduce((sum, item) => sum + item.count, 0)
  } catch (error) {
    console.error('Ошибка загрузки статистики по серьезности:', error)
  }
}

// Загрузка данных по типам угроз
async function loadThreatStats() {
  try {
    const response = await statistics.threats(
      formatDateTime(selectedPeriod.value.start),
      formatDateTime(selectedPeriod.value.end)
    )
    // Сортируем так, чтобы "Другое" было в конце
    threatStats.value = response.data.data.sort((a, b) => {
      if (a.name === 'Другое') return 1
      if (b.name === 'Другое') return -1
      return 0
    })
  } catch (error) {
    console.error('Ошибка загрузки статистики по угрозам:', error)
  }
}

// Форматирование даты в строку YYYY-MM-DD HH:mm:ss
function formatDateTime(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

// Загрузка данных активности
async function loadActivityStats() {
  loadingActivity.value = true
  try {
    const response = await statistics.activity(
      periodType.value,
      formatDateTime(selectedPeriod.value.start),
      formatDateTime(selectedPeriod.value.end)
    )
    activityData.value = response.data.data
  } catch (error) {
    console.error('Ошибка загрузки статистики активности:', error)
  } finally {
    loadingActivity.value = false
  }
}

// Обработка изменения периода
function onPeriodChange(event) {
  selectedPeriod.value = { start: event.start, end: event.end }
  periodType.value = event.periodType
  // Обновляем все данные при изменении периода
  loadActivityStats()
  loadSeverityStats()
  loadThreatStats()
}

// Вычисление процента для прогресс-бара
function widthPercent(count, total) {
  if (total === 0) return 0
  return (count / total) * 100
}

// Получить цвет для уровня серьезности
function getSeverityColor(name) {
  const colors = {
    'Критический': 'text-[#ff7a80]',
    'Высокий': 'text-[#ffbe76]',
    'Средний': 'text-[#9088ff]',
    'Низкий': 'text-[#64d1b4]'
  }
  return colors[name] || 'text-[#9ea6b9]'
}

// Получить градиент для уровня серьезности
function getSeverityGradient(name) {
  const gradients = {
    'Критический': 'bg-gradient-to-r from-[#d74f59] to-[#ff7a80]',
    'Высокий': 'bg-gradient-to-r from-[#ce8c3d] to-[#ffbe76]',
    'Средний': 'bg-gradient-to-r from-[#5e68e7] to-[#8f88ff]',
    'Низкий': 'bg-gradient-to-r from-[#3ea88d] to-[#64d1b4]'
  }
  return gradients[name] || 'bg-gradient-to-r from-[#495064] to-[#656d82]'
}

// Получить класс badge для угрозы
function getThreatBadgeClass(count) {
  if (count === 0) return 'bg-[#5f66ff]/15 text-[#a8b0ff] border border-[#5f66ff]/25'
  if (count >= 10) return 'bg-[#ff7a80]/12 text-[#ff9ca2] border border-[#ff7a80]/30'
  if (count >= 5) return 'bg-[#ffbe76]/12 text-[#ffd09c] border border-[#ffbe76]/30'
  return 'bg-[#5f66ff]/15 text-[#a8b0ff] border border-[#5f66ff]/25'
}

// Склонение слов
function pluralize(count, one, few, many) {
  const mod10 = count % 10
  const mod100 = count % 100
  
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}

// Получить метку для оси X
function getLabel(index, dateStr) {
  if (periodType.value === 'week') {
    const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    return days[index] || ''
  } else {
    // Для месяца - день из даты (парсим как локальную дату без смещения часовых поясов)
    if (!dateStr) return ''
    // Парсим дату в формате YYYY-MM-DD как локальную
    const parts = dateStr.split('-')
    if (parts.length === 3) {
      return parseInt(parts[2], 10)
    }
    return ''
  }
}

// Загрузка всех данных при монтировании
onMounted(async () => {
  loading.value = true
  await Promise.all([
    loadSeverityStats(),
    loadThreatStats(),
    loadActivityStats()
  ])
  loading.value = false
})
</script>
