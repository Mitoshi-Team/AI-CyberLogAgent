<template>
  <div class="h-screen flex flex-col">
    <div class="flex-1 flex flex-col bg-dark-900/30 overflow-hidden">
      <!-- Окно чата на всю высоту -->
      <div class="flex-1 flex flex-col overflow-hidden relative ml-9">
        <!-- Кнопка "Новый чат" в правом верхнем углу -->
        <button
          @click="showNewChatModal = true"
          :disabled="isLoading"
          class="absolute top-4 right-8 z-20 flex items-center gap-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 disabled:bg-dark-800 disabled:cursor-not-allowed text-dark-300 hover:text-white disabled:text-dark-500 rounded-lg transition-all text-sm font-medium shadow-lg"
          title="Начать новый чат"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
          </svg>
          <span>Новый чат</span>
        </button>
        
        <!-- История чата с фиксированной высотой и скроллом -->
        <div ref="chatContainer" class="flex-1 overflow-y-auto space-y-8 pt-8 pl-8 pr-2 sm:pr-3 md:pr-4 lg:pr-6 xl:pr-8 pb-4 scrollbar-chat">
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
                    Новое сообщение
                  </span>
                </div>
                <div 
                  class="markdown-content text-base leading-relaxed text-dark-200 text-left"
                  v-html="renderMarkdown(msg.text)"
                ></div>
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
            
            <!-- Сообщение об ошибке пустого файла -->
            <div v-if="isEmptyFile" class="absolute bottom-16 right-3 text-xs text-red-500">
              Файл пустой
            </div>
            
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
                :class="[
                  'btn bg-dark-800 hover:bg-dark-700 border transition-all p-2',
                  isEmptyFile 
                    ? 'border-red-500 text-red-400 hover:border-red-400' 
                    : 'border-dark-700 hover:border-primary-500/50 text-dark-300 hover:text-primary-400'
                ]"
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

    <!-- Модальное окно подтверждения нового чата -->
    <div
      v-if="showNewChatModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="showNewChatModal = false"
    >
      <div class="bg-dark-900 rounded-xl max-w-md w-full border border-dark-800">
        <!-- Заголовок модального окна -->
        <div class="bg-dark-900 border-b border-dark-800 px-6 py-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Подтверждение</h2>
          <button
            @click="showNewChatModal = false"
            class="text-dark-400 hover:text-white transition-colors p-1"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Содержимое модального окна -->
        <div class="p-6">
          <p class="text-dark-300 mb-6">
            Вы уверены, что хотите начать новый чат? Все сообщения будут удалены, 
            а контекст GigaChat агента будет полностью очищен.
          </p>
          <div class="flex gap-3 justify-end">
            <button
              @click="showNewChatModal = false"
              class="px-4 py-2 bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-white rounded-lg transition-colors"
            >
              Отмена
            </button>
            <button
              @click="confirmNewChat"
              :disabled="isLoading"
              class="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-dark-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              Удалить и начать новый
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useRoute } from 'vue-router'
import { chat, logs } from '@/services/api'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Настройка marked для безопасного рендеринга
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

// Функция для безопасного преобразования markdown в HTML
const renderMarkdown = (text) => {
  const rawHtml = marked.parse(text)
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'code', 'pre', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class']
  })
}

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
const isEmptyFile = ref(false)
const showNewChatModal = ref(false)
let clearNotificationsTimer = null

// Константы ограничений
const MAX_MESSAGE_LENGTH = 500
const RATE_LIMIT_DELAY = 2000 // 2 секунды
const NOTIFICATION_CLEAR_DELAY = 5000 // 5 секунд до снятия выделения

const messages = ref([])

// Загрузка истории чата при монтировании
onMounted(async () => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  // Очищаем с задержкой при монтировании компонента
  clearNotifications(false)
  adjustTextareaHeight()
  
  // Загружаем историю чата из БД
  await loadChatHistory()
})

// Функция загрузки истории чата
const loadChatHistory = async () => {
  try {
    const userId = appStore.currentUser?.id
    if (!userId) {
      console.error('User not authenticated')
      // Показываем начальное приветствие если пользователь не авторизован
      messages.value = [{
        role: 'ai',
        text: 'Привет! Я CyberLog AI ассистент. Я помогу вам анализировать инциденты безопасности и предоставлять рекомендации. Какой у вас вопрос?',
        isNew: false,
      }]
      return
    }
    
    const response = await chat.getMessages(userId, 50)
    
    if (response.data && response.data.data && response.data.data.length > 0) {
      // Преобразуем сообщения из БД в формат компонента
      messages.value = response.data.data.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'ai',  // 'assistant' или 'agent' -> 'ai'
        text: msg.content,
        isNew: false,
      }))
    } else {
      // Если история пуста, показываем приветствие
      messages.value = [{
        role: 'ai',
        text: 'Привет! Я CyberLog AI ассистент. Я помогу вам анализировать инциденты безопасности и предоставлять рекомендации. Какой у вас вопрос?',
        isNew: false,
      }]
    }
    
    scrollToBottom()
  } catch (error) {
    console.error('Error loading chat history:', error)
    // В случае ошибки показываем приветствие
    messages.value = [{
      role: 'ai',
      text: 'Привет! Я CyberLog AI ассистент. Я помогу вам анализировать инциденты безопасности и предоставлять рекомендации. Какой у вас вопрос?',
      isNew: false,
    }]
  }
}

// Функция сохранения сообщения в БД
const saveChatMessage = async (role, content) => {
  try {
    const userId = appStore.currentUser?.id
    if (!userId) {
      console.error('User not authenticated, cannot save message')
      return
    }
    
    await chat.sendMessage(userId, role, content)
  } catch (error) {
    console.error('Error saving chat message:', error)
    appStore.addNotification('Ошибка сохранения сообщения', 'error')
  }
}

// Функция очистки уведомлений
const clearNotifications = (immediate = false) => {
  // Очищаем предыдущий таймер если он был
  if (clearNotificationsTimer) {
    clearTimeout(clearNotificationsTimer)
    clearNotificationsTimer = null
  }
  
  // Сбрасываем счетчик непрочитанных сразу
  appStore.clearUnreadChatMessages()
  
  if (immediate) {
    // Немедленная очистка (при загрузке истории)
    messages.value = messages.value.map(msg => ({
      ...msg,
      isNew: false
    }))
  } else {
    // Очистка с задержкой (чтобы пользователь увидел выделенные сообщения)
    clearNotificationsTimer = setTimeout(() => {
      messages.value = messages.value.map(msg => ({
        ...msg,
        isNew: false
      }))
    }, NOTIFICATION_CLEAR_DELAY)
  }
}

// Очистка счетчика непрочитанных при открытии/переходе на страницу чата
watch(() => route.path, (newPath) => {
  if (newPath === '/chat') {
    // Очищаем с задержкой, чтобы пользователь увидел выделенные сообщения
    clearNotifications(false)
  }
}, { immediate: true })

// Очистка при возвращении фокуса на вкладку
const handleVisibilityChange = () => {
  if (!document.hidden && route.path === '/chat') {
    clearNotifications()
  }
}

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  // Очищаем при монтировании компонента
  clearNotifications()
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  // Очищаем таймер при размонтировании
  if (clearNotificationsTimer) {
    clearTimeout(clearNotificationsTimer)
  }
})

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

  // Отправляем сообщение AI агенту через API
  try {
    const userId = appStore.currentUser?.id
    if (!userId) {
      throw new Error('User not authenticated')
    }

    // Вызываем новый endpoint для обработки сообщения с AI
    const response = await chat.sendToAI(userId, userMessage)
    
    const isOnChatPage = route.path === '/chat'
    const isTabVisible = document.visibilityState === 'visible'
    const shouldNotify = !isOnChatPage || !isTabVisible
    
    const aiResponse = response.data.agent_response
    
    messages.value.push({
      role: 'ai',
      text: aiResponse,
      isNew: shouldNotify, // Помечаем как новое, если пользователь не видит чат
    })
    
    // Если пользователь не видит чат (другая страница или вкладка), увеличиваем счетчик и отправляем уведомление
    if (shouldNotify) {
      appStore.addUnreadChatMessage()
      appStore.addNotification('Новый ответ от AI агента в чате', 'info', 5000, true) // playSound = true
    }
    
  } catch (error) {
    console.error('Error sending message to AI:', error)
    
    // Показываем сообщение об ошибке пользователю
    messages.value.push({
      role: 'ai',
      text: 'Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз позже.',
      isNew: false,
    })
    
    appStore.addNotification('Ошибка при отправке сообщения AI агенту', 'error')
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

const selectQuickQuestion = (question) => {
  inputMessage.value = question
  sendMessage()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  
  if (!file) return
  
  const userId = appStore.currentUser?.id
  if (!userId) {
    appStore.addNotification('Ошибка: пользователь не авторизован', 'error')
    event.target.value = ''
    return
  }
  
  // Сбрасываем состояние ошибки пустого файла
  isEmptyFile.value = false
  
  // Проверяем расширение файла
  if (!file.name.endsWith('.log')) {
    const errorMsg = '❌ Ошибка: Можно загружать только файлы с расширением .log'
    messages.value.push({
      role: 'user',
      text: errorMsg,
    })
    await saveChatMessage('user', errorMsg)
    scrollToBottom()
    event.target.value = '' // Сбрасываем input
    return
  }
  
  // Показываем сообщение о загрузке
  const uploadMsg = `📤 Загрузка файла "${file.name}" (${(file.size / 1024).toFixed(2)} KB)...`
  messages.value.push({
    role: 'user',
    text: uploadMsg,
  })
  await saveChatMessage('user', uploadMsg)
  scrollToBottom()
  
  // Устанавливаем состояние загрузки
  isLoading.value = true
  
  try {
    // Отправляем файл на сервер для анализа
    const response = await logs.upload(userId, file)
    
    if (response.data.success) {
      // Показываем только анализ от GigaChat
      const analysisMsg = response.data.gigachat_analysis
      
      messages.value.push({
        role: 'ai',
        text: analysisMsg,
        isNew: false,
      })
      
      // Сохраняем ответ в БД
      await saveChatMessage('agent', analysisMsg)
      
      appStore.addNotification(
        `Файл ${file.name} успешно проанализирован`,
        'success'
      )
    } else {
      throw new Error(response.data.message || 'Ошибка при анализе файла')
    }
    
  } catch (error) {
    console.error('Error uploading log file:', error)
    
    const errorMsg = `❌ **Ошибка при анализе файла**

${error.response?.data?.detail || error.message || 'Неизвестная ошибка'}`
    
    messages.value.push({
      role: 'ai',
      text: errorMsg,
      isNew: false,
    })
    
    await saveChatMessage('agent', errorMsg)
    
    appStore.addNotification('Ошибка при анализе файла логов', 'error')
  } finally {
    isLoading.value = false
    scrollToBottom()
    event.target.value = '' // Сбрасываем input
  }
}

const confirmNewChat = async () => {
  try {
    const userId = appStore.currentUser?.id
    if (!userId) {
      appStore.addNotification('Ошибка: пользователь не авторизован', 'error')
      showNewChatModal.value = false
      return
    }

    isLoading.value = true
    showNewChatModal.value = false

    // Очищаем сообщения в БД и контекст GigaChat
    const response = await chat.clearMessages(userId)

    // Очищаем локальный массив сообщений
    messages.value = []

    // Загружаем начальное приветствие и сохраняем его в БД
    const welcomeMessage = 'Привет! Я CyberLog AI ассистент. Я помогу вам анализировать инциденты безопасности и предоставлять рекомендации. Какой у вас вопрос?'
    
    messages.value.push({
      role: 'ai',
      text: welcomeMessage,
      isNew: false,
    })

    // Сохраняем приветствие в БД с ролью 'agent'
    await chat.sendMessage(userId, 'agent', welcomeMessage)

    // Показываем уведомление с информацией об очистке
    const deletedCount = response.data?.deleted_count || 0
    appStore.addNotification(
      `Новый чат начат`, 
      'success'
    )
    
    scrollToBottom()
  } catch (error) {
    console.error('Error starting new chat:', error)
    appStore.addNotification('Ошибка при создании нового чата', 'error')
  } finally {
    isLoading.value = false
  }
}
</script>
<style scoped>
/* Стили для markdown контента */
.markdown-content :deep(p) {
  margin: 0.5em 0;
}

.markdown-content :deep(p:first-child) {
  margin-top: 0;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: #e5e7eb;
}

.markdown-content :deep(em) {
  font-style: italic;
}

.markdown-content :deep(code) {
  background-color: rgba(79, 70, 229, 0.1);
  border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.9em;
  color: #c4b5fd;
}

.markdown-content :deep(pre) {
  background-color: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(79, 70, 229, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin: 12px 0;
  overflow-x: auto;
}

.markdown-content :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
  color: #e5e7eb;
  font-size: 0.875em;
  line-height: 1.5;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin: 4px 0;
}

.markdown-content :deep(ul li) {
  list-style-type: disc;
}

.markdown-content :deep(ol li) {
  list-style-type: decimal;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid rgba(79, 70, 229, 0.5);
  padding-left: 12px;
  margin: 12px 0;
  color: #9ca3af;
  font-style: italic;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-weight: 600;
  margin: 16px 0 8px 0;
  color: #f3f4f6;
}

.markdown-content :deep(h1) {
  font-size: 1.5em;
  border-bottom: 2px solid rgba(79, 70, 229, 0.3);
  padding-bottom: 8px;
}

.markdown-content :deep(h2) {
  font-size: 1.3em;
}

.markdown-content :deep(h3) {
  font-size: 1.15em;
}

.markdown-content :deep(h4) {
  font-size: 1.05em;
}

.markdown-content :deep(a) {
  color: #818cf8;
  text-decoration: underline;
  transition: color 0.2s;
}

.markdown-content :deep(a:hover) {
  color: #a5b4fc;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid rgba(79, 70, 229, 0.3);
  margin: 16px 0;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 0.9em;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid rgba(79, 70, 229, 0.3);
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(th) {
  background-color: rgba(79, 70, 229, 0.2);
  font-weight: 600;
  color: #e5e7eb;
}

.markdown-content :deep(tr:nth-child(even)) {
  background-color: rgba(17, 24, 39, 0.3);
}
</style>