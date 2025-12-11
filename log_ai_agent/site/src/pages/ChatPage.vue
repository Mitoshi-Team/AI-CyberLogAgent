<template>
  <div class="h-screen flex flex-col">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Окно чата на всю высоту -->
      <div class="flex-1 flex flex-col bg-dark-900/30 border-l border-dark-800 overflow-hidden">
        <!-- История чата с фиксированной высотой и скроллом -->
        <div ref="chatContainer" class="flex-1 overflow-y-auto space-y-8 pt-8 px-2 sm:px-3 md:px-4 lg:px-6 xl:px-8 pb-4 scrollbar-chat">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex justify-center"
          >
            <div class="max-w-full sm:max-w-4xl md:max-w-3xl lg:max-w-2xl w-full">
              <!-- Сообщение пользователя - облачко справа от области агента -->
              <div
                v-if="msg.role === 'user'"
                class="flex justify-end"
              >
                <div class="max-w-full sm:max-w-md px-4 py-3 rounded-xl shadow-lg bg-gradient-to-br from-primary-600 to-primary-500 text-white rounded-br-none">
                  <p class="text-sm leading-relaxed">{{ msg.text }}</p>
                </div>
              </div>
              
              <!-- Сообщение агента - сплошной текст с подписью -->
              <div 
                v-else
                :class="[
                  'p-4 rounded-lg transition-all duration-500',
                  msg.isNew ? 'bg-primary-500/10 border-l-4 border-primary-500 shadow-lg shadow-primary-500/20' : ''
                ]"
              >
                <div v-if="msg.isNew" class="flex items-center gap-2 mb-2">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-500/20 text-primary-400 text-xs font-medium rounded-full animate-pulse">
                    <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
                    </svg>
                    Новый отчёт
                  </span>
                </div>
                <p class="text-base leading-relaxed text-dark-200 text-left">{{ msg.text }}</p>
                <p class="text-xs text-dark-500 mt-2 text-left">AI Cyber Log</p>
              </div>
            </div>
          </div>
          <div v-if="isLoading" class="flex justify-center">
            <div class="flex gap-1">
              <div class="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 0ms"/>
              <div class="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 150ms"/>
              <div class="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 300ms"/>
            </div>
          </div>
        </div>

        <!-- Быстрые вопросы (компактные плашки над полем ввода) -->
        <div class="flex flex-wrap gap-2 px-4 sm:px-8 md:px-16 lg:px-24 xl:px-48 pt-2 pb-1 mt-4">
          <button
            @click="selectQuickQuestion('Сколько критичных инцидентов за последнее время?')"
            class="px-3 py-1.5 bg-dark-800/50 hover:bg-dark-800 border border-dark-700 hover:border-primary-500/50 rounded-lg text-xs text-dark-300 hover:text-primary-400 transition-all flex items-center gap-1.5"
          >
            <span>📊</span>
            <span>Статистика</span>
          </button>
          <button
            @click="selectQuickQuestion('Какие рекомендации для предотвращения атак?')"
            class="px-3 py-1.5 bg-dark-800/50 hover:bg-dark-800 border border-dark-700 hover:border-primary-500/50 rounded-lg text-xs text-dark-300 hover:text-primary-400 transition-all flex items-center gap-1.5"
          >
            <span>🛡️</span>
            <span>Рекомендации</span>
          </button>
          <button
            @click="selectQuickQuestion('Анализируй последний инцидент')"
            class="px-3 py-1.5 bg-dark-800/50 hover:bg-dark-800 border border-dark-700 hover:border-primary-500/50 rounded-lg text-xs text-dark-300 hover:text-primary-400 transition-all flex items-center gap-1.5"
          >
            <span>🔍</span>
            <span>Анализ инцидента</span>
          </button>
          <button
            @click="selectQuickQuestion('Какие тренды в безопасности?')"
            class="px-3 py-1.5 bg-dark-800/50 hover:bg-dark-800 border border-dark-700 hover:border-primary-500/50 rounded-lg text-xs text-dark-300 hover:text-primary-400 transition-all flex items-center gap-1.5"
          >
            <span>📈</span>
            <span>Тренды</span>
          </button>
        </div>

        <!-- Ввод сообщения -->
        <div class="flex gap-3 px-4 sm:px-8 md:px-16 lg:px-24 xl:px-48 py-4 items-start min-h-[116px]">
          <div class="flex-1 relative">
            <textarea
              v-model="inputMessage"
              @keydown.enter.exact.prevent="sendMessage"
              ref="messageInput"
              maxlength="500"
              rows="1"
              class="input w-full resize-none overflow-y-auto pr-32 pb-10 block"
              placeholder="Напишите вопрос об инцидентах..."
              :disabled="isLoading || isRateLimited"
              @input="adjustTextareaHeight"
              style="min-height: 84px; max-height: 400px; height: auto;"
            ></textarea>
            
            <!-- Счетчик и кнопки внизу справа -->
            <div class="absolute bottom-2 right-3 flex items-center gap-2">
              <div class="text-xs px-2 py-1 rounded bg-dark-800/80 text-dark-400">
                {{ inputMessage.length }}/500
              </div>
              
              <!-- Кнопка загрузки файла логов -->
              <input
                ref="fileInput"
                type="file"
                accept=".log"
                @change="handleFileUpload"
                class="hidden"
              />
              <button
                @click="$refs.fileInput.click()"
                class="btn bg-dark-800 hover:bg-dark-700 border border-dark-700 hover:border-primary-500/50 text-dark-300 hover:text-primary-400 transition-all p-2"
                title="Загрузить .log файл"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
                </svg>
              </button>
              
              <button
                @click="sendMessage"
                :disabled="!canSendMessage"
                class="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed p-2"
                :title="getRateLimitMessage"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M11.5003 12H5.41872M5.24634 12.7972L4.24158 15.7986C3.69128 17.4424 3.41613 18.2643 3.61359 18.7704C3.78506 19.21 4.15335 19.5432 4.6078 19.6701C5.13111 19.8161 5.92151 19.4604 7.50231 18.7491L17.6367 14.1886C19.1797 13.4942 19.9512 13.1471 20.1896 12.6648C20.3968 12.2458 20.3968 11.7541 20.1896 11.3351C19.9512 10.8529 19.1797 10.5057 17.6367 9.81135L7.48483 5.24303C5.90879 4.53382 5.12078 4.17921 4.59799 4.32468C4.14397 4.45101 3.77572 4.78336 3.60365 5.22209C3.40551 5.72728 3.67772 6.54741 4.22215 8.18767L5.24829 11.2793C5.34179 11.561 5.38855 11.7019 5.407 11.8459C5.42338 11.9738 5.42321 12.1032 5.40651 12.231C5.38768 12.375 5.34057 12.5157 5.24634 12.7972Z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useRoute } from 'vue-router'

const appStore = useAppStore()
const route = useRoute()
const chatContainer = ref(null)
const fileInput = ref(null)
const messageInput = ref(null)
const inputMessage = ref('')
const isLoading = ref(false)
const uploadedLogFile = ref(null)
const lastMessageTime = ref(0)
const isRateLimited = ref(false)

// Константы ограничений
const MAX_MESSAGE_LENGTH = 500
const RATE_LIMIT_DELAY = 2000 // 2 секунды

const messages = ref([
  {
    role: 'ai',
    text: 'Привет! Я CyberLog AI ассистент. Я помогу вам анализировать инциденты безопасности и предоставлять рекомендации. Какой у вас вопрос?',
    isNew: false,
  },
])

// Очистка счетчика непрочитанных при открытии/переходе на страницу чата
watch(() => route.path, (newPath) => {
  if (newPath === '/chat') {
    appStore.clearUnreadChatMessages()
    // Убираем подсветку "новое" со всех сообщений
    messages.value.forEach(msg => {
      msg.isNew = false
    })
  }
}, { immediate: true })

// Проверка возможности отправки сообщения
const canSendMessage = computed(() => {
  return (
    inputMessage.value.trim().length > 0 &&
    inputMessage.value.length <= MAX_MESSAGE_LENGTH &&
    !isLoading.value &&
    !isRateLimited.value
  )
})

// Сообщение о причине блокировки
const getRateLimitMessage = computed(() => {
  if (isLoading.value) return 'Ожидание ответа агента...'
  if (isRateLimited.value) return 'Подождите 2 секунды перед следующим сообщением'
  if (inputMessage.value.length > MAX_MESSAGE_LENGTH) return 'Сообщение слишком длинное'
  if (!inputMessage.value.trim()) return 'Введите сообщение'
  return 'Отправить сообщение'
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const adjustTextareaHeight = () => {
  nextTick(() => {
    const textarea = messageInput.value
    if (!textarea) return
    
    // Сбрасываем высоту для правильного расчета scrollHeight
    textarea.style.height = 'auto'
    
    // Устанавливаем новую высоту на основе содержимого
    const newHeight = Math.min(textarea.scrollHeight, 400) // Максимум 400px
    textarea.style.height = `${newHeight}px`
  })
}

onMounted(() => {
  // Устанавливаем начальную высоту
  adjustTextareaHeight()
})

const sendMessage = async () => {
  // Проверка возможности отправки
  if (!canSendMessage.value) return
  
  // Проверка частоты отправки (rate limiting)
  const now = Date.now()
  const timeSinceLastMessage = now - lastMessageTime.value
  
  if (timeSinceLastMessage < RATE_LIMIT_DELAY) {
    appStore.addNotification(
      `Подождите ${Math.ceil((RATE_LIMIT_DELAY - timeSinceLastMessage) / 1000)} сек. перед следующим сообщением`,
      'warning'
    )
    return
  }
  
  // Обновляем время последнего сообщения
  lastMessageTime.value = now
  
  // Устанавливаем rate limit на 2 секунды
  isRateLimited.value = true
  setTimeout(() => {
    isRateLimited.value = false
  }, RATE_LIMIT_DELAY)

  // Добавить сообщение пользователя
  messages.value.push({
    role: 'user',
    text: inputMessage.value,
  })

  const userMessage = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true
  
  // Сбрасываем высоту textarea после очистки
  adjustTextareaHeight()
  
  scrollToBottom()

  // Имитация ответа AI
  setTimeout(() => {
    const isOnChatPage = route.path === '/chat'
    const isTabVisible = document.visibilityState === 'visible'
    const shouldNotify = !isOnChatPage || !isTabVisible
    
    messages.value.push({
      role: 'ai',
      text: generateAIResponse(userMessage),
      isNew: shouldNotify, // Помечаем как новое, если пользователь не видит чат
    })
    
    // Если пользователь не видит чат (другая страница или вкладка), увеличиваем счетчик и отправляем уведомление
    if (shouldNotify) {
      appStore.addUnreadChatMessage()
      appStore.addNotification('Новый ответ от AI агента в чате', 'info', 5000, true) // playSound = true
    }
    
    isLoading.value = false
    scrollToBottom()
  }, 1500)
}

const selectQuickQuestion = (question) => {
  inputMessage.value = question
  sendMessage()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  
  if (!file) return
  
  // Проверяем расширение файла
  if (!file.name.endsWith('.log')) {
    messages.value.push({
      role: 'ai',
      text: '❌ Ошибка: Можно загружать только файлы с расширением .log',
    })
    scrollToBottom()
    event.target.value = '' // Сбрасываем input
    return
  }
  
  // Читаем содержимое файла
  const reader = new FileReader()
  
  reader.onload = (e) => {
    const fileContent = e.target.result
    
    // Сохраняем файл в переменную
    uploadedLogFile.value = {
      name: file.name,
      size: file.size,
      content: fileContent,
      uploadedAt: new Date().toISOString(),
    }
    
    // Уведомляем пользователя об успешной загрузке
    messages.value.push({
      role: 'ai',
      text: `✅ Файл "${file.name}" успешно загружен (${(file.size / 1024).toFixed(2)} KB)`,
    })
    
    scrollToBottom()
    
    console.log('Загруженный файл:', uploadedLogFile.value)
  }
  
  reader.onerror = () => {
    messages.value.push({
      role: 'ai',
      text: '❌ Ошибка при чтении файла. Попробуйте снова.',
    })
    scrollToBottom()
  }
  
  reader.readAsText(file)
  
  // Сбрасываем input для возможности повторной загрузки того же файла
  event.target.value = ''
}

const generateAIResponse = (question) => {
  const responses = {
    'статистика': 'На данный момент обнаружено 10 инцидентов, из них 2 критичных и 3 подозрительных.',
    'рекомендации': 'Рекомендую активировать двухфакторную аутентификацию, обновить список блокируемых IP и увеличить мониторинг.',
    'анализ': 'Последний инцидент был связан с попыткой несанкционированного доступа. Предполагаемый источник заблокирован.',
    'тренды': 'В последнюю неделю наблюдается рост попыток атак на SSH. Рекомендую усилить контроль доступа.',
  }

  for (const [key, response] of Object.entries(responses)) {
    if (question.toLowerCase().includes(key)) {
      return response
    }
  }

  return 'Спасибо за вопрос. Я анализирую данные и выполняю необходимые проверки. Результаты будут готовы вскоре.'
}
</script>
