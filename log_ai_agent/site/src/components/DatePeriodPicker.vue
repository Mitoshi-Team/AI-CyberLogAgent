<template>
  <div class="date-period-picker">
    <div class="flex flex-col sm:flex-row gap-2 sm:gap-3">
      <!-- Выбор типа периода -->
      <select 
        v-model="localPeriodType" 
        @change="onPeriodTypeChange"
        class="bg-dark-800 border border-dark-700 text-white rounded-lg px-3 sm:px-4 py-2 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-primary-500 hover:border-dark-600 transition-colors cursor-pointer w-full sm:w-auto"
      >
        <option value="week">Неделя</option>
        <option value="month">Месяц</option>
      </select>

      <!-- Кнопка открытия календаря -->
      <button
        @click="toggleCalendar"
        class="bg-dark-800 border border-dark-700 text-white rounded-lg px-3 sm:px-4 py-2 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-primary-500 hover:border-dark-600 transition-colors cursor-pointer flex items-center justify-center gap-2 w-full sm:w-auto"
      >
        <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
        </svg>
        <span class="truncate">{{ formattedPeriod }}</span>
      </button>
    </div>

    <!-- Календарь или выбор месяца/года -->
    <div 
      v-if="showCalendar" 
      class="absolute z-50 mt-2 bg-dark-800 border border-dark-700 rounded-lg shadow-xl p-3 sm:p-4 left-0 right-0 sm:left-auto sm:right-auto sm:min-w-[320px] max-w-sm sm:max-w-md"
      @click.stop
    >
      <!-- Выбор только месяца и года (для типа "месяц") -->
      <div v-if="localPeriodType === 'month'" class="space-y-4">
        <h3 class="text-white font-semibold text-center mb-4 text-sm sm:text-base">Выберите месяц и год</h3>
        
        <!-- Выбор года -->
        <div class="flex items-center justify-between mb-4">
          <button 
            @click="currentYear--"
            class="p-1.5 sm:p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </button>
          
          <div class="text-white font-semibold text-base sm:text-lg">
            {{ currentYear }}
          </div>
          
          <button 
            @click="currentYear++"
            class="p-1.5 sm:p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>

        <!-- Сетка месяцев -->
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="(month, index) in monthNames"
            :key="index"
            @click="selectMonth(index)"
            :class="currentMonth === index ? 'bg-primary-600 text-white' : 'bg-dark-700 text-dark-300 hover:bg-dark-600'"
            class="py-2 px-2 sm:px-3 rounded-lg transition-colors text-xs sm:text-sm font-medium"
          >
            {{ month }}
          </button>
        </div>

        <!-- Кнопка закрытия -->
        <div class="mt-4 flex justify-end">
          <button
            @click="closeCalendar"
            class="px-3 sm:px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors text-sm sm:text-base"
          >
            Закрыть
          </button>
        </div>
      </div>

      <!-- Календарь по дням (для типа "неделя") -->
      <div v-else>
        <!-- Навигация по месяцам -->
        <div class="flex items-center justify-between mb-4">
          <button 
            @click="previousMonth"
            class="p-1.5 sm:p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </button>
          
          <div class="text-white font-semibold text-sm sm:text-base">
            {{ monthNames[currentMonth] }} {{ currentYear }}
          </div>
          
          <button 
            @click="nextMonth"
            class="p-1.5 sm:p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>

        <!-- Дни недели -->
        <div class="grid grid-cols-7 gap-0.5 sm:gap-1 mb-2">
          <div v-for="day in dayNames" :key="day" class="text-center text-xs text-dark-400 font-semibold py-1">
            {{ day }}
          </div>
        </div>

        <!-- Календарная сетка -->
        <div class="grid grid-cols-7 gap-0.5 sm:gap-1">
          <div 
            v-for="(day, index) in calendarDays" 
            :key="index"
            @click="selectDate(day)"
            @mouseenter="hoverDate(day)"
            @mouseleave="unhoverDate"
            :class="getDayClass(day)"
            class="text-center py-1.5 sm:py-2 px-0.5 sm:px-1 rounded cursor-pointer transition-colors text-xs sm:text-sm"
          >
            {{ day ? day.getDate() : '' }}
          </div>
        </div>

        <!-- Кнопка закрытия -->
        <div class="mt-4 flex justify-end">
          <button
            @click="closeCalendar"
            class="px-3 sm:px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors text-sm sm:text-base"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  periodType: {
    type: String,
    default: 'week',
    validator: (value) => ['week', 'month'].includes(value)
  },
  modelValue: {
    type: Object,
    default: () => ({
      start: new Date(),
      end: new Date()
    })
  }
})

const emit = defineEmits(['update:modelValue', 'update:periodType', 'change'])

const localPeriodType = ref(props.periodType)
const showCalendar = ref(false)
const currentMonth = ref(new Date().getMonth())
const currentYear = ref(new Date().getFullYear())
const hoveredWeek = ref(null)
const selectedDate = ref(props.modelValue.start || new Date())

const monthNames = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]

const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

// Получить все дни для отображения в календаре
const calendarDays = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value, 1)
  const lastDay = new Date(currentYear.value, currentMonth.value + 1, 0)
  
  // Получаем день недели первого дня (0 = воскресенье, преобразуем в 0 = понедельник)
  let firstDayOfWeek = firstDay.getDay()
  firstDayOfWeek = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1
  
  const days = []
  
  // Добавляем пустые ячейки для дней предыдущего месяца
  for (let i = 0; i < firstDayOfWeek; i++) {
    days.push(null)
  }
  
  // Добавляем все дни текущего месяца
  for (let i = 1; i <= lastDay.getDate(); i++) {
    days.push(new Date(currentYear.value, currentMonth.value, i))
  }
  
  return days
})

// Форматированная строка выбранного периода
const formattedPeriod = computed(() => {
  if (!props.modelValue.start || !props.modelValue.end) {
    return 'Выберите период'
  }
  
  const start = props.modelValue.start
  const end = props.modelValue.end
  
  if (localPeriodType.value === 'month') {
    return `${monthNames[start.getMonth()]} ${start.getFullYear()}`
  } else {
    const formatDate = (date) => {
      const day = date.getDate().toString().padStart(2, '0')
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      return `${day}.${month}`
    }
    return `${formatDate(start)} - ${formatDate(end)}`
  }
})

// Получить CSS класс для дня
const getDayClass = (day) => {
  if (!day) return ''
  
  const classes = []
  
  // Проверка на выбранный период
  if (isInSelectedPeriod(day)) {
    classes.push('bg-primary-600 text-white font-semibold')
  } else if (isInHoveredWeek(day)) {
    classes.push('bg-primary-600/30 text-white')
  } else {
    classes.push('text-dark-300 hover:bg-dark-700')
  }
  
  // Текущий день
  if (isToday(day)) {
    classes.push('ring-2 ring-primary-400')
  }
  
  return classes.join(' ')
}

// Проверка, находится ли день в выбранном периоде
const isInSelectedPeriod = (day) => {
  if (!props.modelValue.start || !props.modelValue.end || !day) return false
  return day >= props.modelValue.start && day <= props.modelValue.end
}

// Проверка, находится ли день в наведенной неделе (только для режима недели)
const isInHoveredWeek = (day) => {
  if (localPeriodType.value !== 'week' || !hoveredWeek.value || !day) return false
  return day >= hoveredWeek.value.start && day <= hoveredWeek.value.end
}

// Проверка на сегодняшний день
const isToday = (day) => {
  if (!day) return false
  const today = new Date()
  return day.getDate() === today.getDate() &&
         day.getMonth() === today.getMonth() &&
         day.getFullYear() === today.getFullYear()
}

// Получить неделю для даты (понедельник - воскресенье)
const getWeekRange = (date) => {
  const day = new Date(date)
  const dayOfWeek = day.getDay()
  const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek // Понедельник
  
  const monday = new Date(day)
  monday.setDate(day.getDate() + diff)
  monday.setHours(0, 0, 0, 0)
  
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(23, 59, 59, 999)
  
  return { start: monday, end: sunday }
}

// Получить диапазон месяца
const getMonthRange = (date) => {
  const start = new Date(date.getFullYear(), date.getMonth(), 1)
  start.setHours(0, 0, 0, 0)
  
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 0)
  end.setHours(23, 59, 59, 999)
  
  return { start, end }
}

// Выбрать месяц (для типа "месяц")
const selectMonth = (monthIndex) => {
  currentMonth.value = monthIndex
  const date = new Date(currentYear.value, monthIndex, 1)
  selectedDate.value = date
  const range = getMonthRange(date)
  
  emit('update:modelValue', range)
  emit('change', { periodType: localPeriodType.value, ...range })
  showCalendar.value = false
}

// Выбрать дату
const selectDate = (day) => {
  if (!day) return
  
  selectedDate.value = day
  let range
  
  if (localPeriodType.value === 'week') {
    range = getWeekRange(day)
  } else {
    range = getMonthRange(day)
  }
  
  emit('update:modelValue', range)
  emit('change', { periodType: localPeriodType.value, ...range })
  showCalendar.value = false
}

// Наведение на дату (для недели)
const hoverDate = (day) => {
  if (!day || localPeriodType.value !== 'week') return
  hoveredWeek.value = getWeekRange(day)
}

// Убрать наведение
const unhoverDate = () => {
  hoveredWeek.value = null
}

// Переключение календаря
const toggleCalendar = () => {
  showCalendar.value = !showCalendar.value
}

const closeCalendar = () => {
  showCalendar.value = false
}

// Навигация по месяцам
const previousMonth = () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11
    currentYear.value--
  } else {
    currentMonth.value--
  }
}

const nextMonth = () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0
    currentYear.value++
  } else {
    currentMonth.value++
  }
}

// Смена типа периода
const onPeriodTypeChange = () => {
  emit('update:periodType', localPeriodType.value)
  
  // Автоматически выбираем текущий период
  const now = new Date()
  let range
  
  if (localPeriodType.value === 'week') {
    range = getWeekRange(now)
  } else {
    range = getMonthRange(now)
  }
  
  emit('update:modelValue', range)
  emit('change', { periodType: localPeriodType.value, ...range })
}

// Наблюдение за изменением типа периода извне
watch(() => props.periodType, (newVal) => {
  localPeriodType.value = newVal
})

// Закрытие календаря при клике вне его
const handleClickOutside = (event) => {
  const picker = event.target.closest('.date-period-picker')
  if (!picker && showCalendar.value) {
    showCalendar.value = false
  }
}

// Добавляем слушатель при монтировании
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.date-period-picker {
  position: relative;
}
</style>
