<template>
  <div class="h-screen flex flex-col relative overflow-hidden">
    <button
      @click="showNewChatModal = true"
      :disabled="isLoading"
      class="absolute top-6 right-6 z-20 inline-flex items-center gap-2 px-4 py-2 bg-[#2b2d33] hover:bg-[#353842] disabled:bg-[#22242b] disabled:cursor-not-allowed text-[#e6e8ee] hover:text-white disabled:text-dark-500 rounded-xl transition-all text-sm font-medium border border-[#3a3d46]"
      title="Начать новый чат"
    >
      <img src="/pencil_icon.svg" alt="new chat" class="w-4 h-4" />
      <span>Новый чат</span>
    </button>

    <div class="relative z-10 flex-1 min-h-0 flex flex-col px-4 sm:px-8">
      <div
        v-if="messages.length > 0 || isLoading"
        class="relative flex-1 min-h-0 flex"
      >
        <div
          ref="chatContainer"
          :class="[
            'chat-scroll-container h-full w-full min-h-0 overflow-y-auto pt-8 pr-3',
            messages.length ? 'chat-scroll-fade-bottom' : ''
          ]"
          :style="{ paddingBottom: `${topAlignSpacerHeight}px` }"
          @scroll="handleChatScroll"
        >
          <div class="mx-auto w-full max-w-3xl space-y-7">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="chat-message-item"
          >
            <div
              v-if="msg.role === 'user'"
              :class="[
                'flex justify-end',
                isLoading && index === messages.length - 1 ? 'mt-[48px]' : ''
              ]"
            >
              <div class="max-w-full sm:max-w-xl px-4 py-3 rounded-2xl rounded-br-md bg-[#2B2B2B] text-white">
                <p class="leading-relaxed break-words whitespace-pre-wrap">{{ msg.text }}</p>
              </div>
            </div>

            <div
              v-else-if="msg.role === 'notice'"
              :class="[
                'px-1 py-1',
                index === messages.length - 1 ? 'mb-12' : 'mb-4'
              ]"
            >
              <p class="text-sm leading-relaxed break-words whitespace-pre-wrap text-[#7f8291]">
                {{ msg.text }}
              </p>
            </div>

            <div
              v-else
              :class="[
                'p-4 rounded-xl transition-all duration-500',
                msg.isNew ? 'bg-[#303a6c]/30 border-l-4 border-[#6b81ff] shadow-[0_10px_35px_rgba(86,112,255,0.25)]' : ''
              ]"
            >
              <div v-if="msg.isNew" class="flex items-center gap-2 mb-2">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 bg-[#5366ff]/20 text-[#9badff] text-xs font-medium rounded-full animate-pulse">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
                  </svg>
                  Новое сообщение
                </span>
              </div>
              <div
                class="markdown-content text-base leading-relaxed text-dark-200 text-left break-words"
                v-html="renderMarkdown(msg.text)"
              ></div>
              <div class="mt-2 inline-flex items-center gap-2 mb-7">
                <p class="text-xs text-[#ABABBF] text-left">Wavescan assistant</p>
                <button
                  type="button"
                  class="copy-message-btn"
                  :title="copiedMessageIndex === index ? 'Скопировано' : 'Копировать сообщение'"
                  :aria-label="copiedMessageIndex === index ? 'Сообщение скопировано' : 'Копировать сообщение ассистента'"
                  @click="copyMessageText(msg.text, index)"
                >
                  <svg
                    v-if="copiedMessageIndex === index"
                    class="w-4 h-4"
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    aria-hidden="true"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 10.5l4 4 8-8" />
                  </svg>
                  <img v-else src="/copy_icon.svg" alt="copy" class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <div v-if="isLoading" class="flex justify-center pb-2">
            <div class="flex gap-1.5 px-3 py-2 rounded-full">
              <div class="w-2 h-2 bg-[#7C7C7C] rounded-full animate-bounce" style="animation-delay: 0ms"/>
              <div class="w-2 h-2 bg-[#7C7C7C] rounded-full animate-bounce" style="animation-delay: 150ms"/>
              <div class="w-2 h-2 bg-[#7C7C7C] rounded-full animate-bounce" style="animation-delay: 300ms"/>
            </div>
          </div>
        </div>
        </div>

        <div
          v-if="showCustomScrollbar"
          class="chat-scrollbar-track"
          @mousedown="handleScrollbarTrackMouseDown"
        >
          <button
            type="button"
            class="chat-scrollbar-thumb"
            :style="{ height: `${scrollbarThumbHeight}px`, transform: `translateY(${scrollbarThumbTop}px)` }"
            aria-label="Прокрутка чата"
            @mousedown.stop.prevent="startScrollbarDrag"
          ></button>
        </div>
      </div>

      <div v-else class="flex-1"></div>

      <div
        :class="[
          'mx-auto w-full max-w-3xl pb-6 shrink-0 transform',
          (messages.length > 0 || isLoading) ? 'translate-y-0 pt-2' : '-translate-y-[24vh]'
        ]"
      >
        <div v-if="isHistoryLoaded && messages.length === 0 && !isLoading" class="mb-1 text-center select-none">
          <img
            src="/wavescan_chat_logo.svg"
            alt="wavescan agent"
            class="w-full max-w-[520px] sm:max-w-[620px] mx-auto wave-logo"
          />
        </div>

        <div
          v-if="messages.length > 0"
          class="flex flex-wrap justify-start gap-3 mb-4"
        >
          <button
            @click="selectQuickQuestion('Какие рекомендации для предотвращения атак?')"
            :disabled="isQuickQuestionBlocked"
            class="quick-pill"
          >
            Рекомендации
          </button>
          <button
            @click="selectQuickQuestion('Какие тренды в безопасности?')"
            :disabled="isQuickQuestionBlocked"
            class="quick-pill"
          >
            Тренды
          </button>
          <button
            @click="selectQuickQuestion('Покажи релевантные техники MITRE ATT&CK для этих инцидентов')"
            :disabled="isQuickQuestionBlocked"
            class="quick-pill"
          >
            MITRE
          </button>
        </div>

        <div class="chat-composer rounded-3xl px-4 py-3 sm:px-5 sm:py-4">
          <div class="flex flex-col gap-3">
            <textarea
              v-model="inputMessage"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.enter.shift.exact="handleShiftEnter"
              ref="messageInput"
              maxlength="500"
              rows="1"
              :class="[
                'w-full resize-none overflow-y-auto bg-transparent text-[#f0f2f9] outline-none px-1 py-1 block',
                isInputBlocked ? 'placeholder-[#616776]' : 'placeholder-[#8c91a1]'
              ]"
              placeholder="Введите текст..."
              :disabled="isLoading || isRateLimited"
              @input="handleMessageInput"
              style="min-height: 40px; max-height: 200px; height: auto;"
            ></textarea>

            <input
              ref="fileInput"
              type="file"
              accept=".log"
              @change="handleFileUpload"
              class="hidden"
            />

            <div v-if="isEmptyFile" class="text-xs text-red-500 text-right pr-1">
              Файл пустой
            </div>

            <div class="flex items-center justify-between gap-3">
              <button
                @click="$refs.fileInput.click()"
                :disabled="isSecondaryControlsBlocked"
                :class="[
                  'w-9 h-9 rounded-xl flex items-center justify-center border transition-all flex-shrink-0',
                  isEmptyFile
                    ? 'border-red-500 text-red-400 bg-red-500/10'
                    : 'border-[#363a46] bg-[#2a2d36] text-[#b7bccb] hover:border-[#6c7dff] hover:text-[#dbe1ff] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:border-[#363a46] disabled:hover:text-[#b7bccb]'
                ]"
                title="Загрузить .log файл"
              >
                <img src="/attachment_icon.svg" alt="attach" class="w-3.5 h-4 attachment-icon attachment-ico" />
              </button>

              <div class="flex items-center gap-2">
                <div class="text-xs px-2 py-1 rounded-lg bg-[#2a2d36] text-[#9095a5] border border-[#343945]">
                  {{ inputMessage.length }}/500
                </div>

                <button
                  :disabled="!canUseVoiceControl"
                  class="w-9 h-9 rounded-xl bg-[#2a2d36] border border-[#363a46] text-[#bcc1cf] hover:text-white hover:border-[#5566ff] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-[#bcc1cf] disabled:hover:border-[#363a46] transition-colors"
                  type="button"
                  :title="voiceControlTitle"
                  @click="handleVoiceControlClick"
                >
                  <svg
                    v-if="isVoiceRecording"
                    class="w-4 h-4 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                  <img v-else src="/micro_icon.svg" alt="voice" class="w-4 h-4 mx-auto" />
                </button>

                <button
                  @click="handleSendControlClick"
                  :disabled="!canUseSendControl"
                  class="w-9 h-9 rounded-xl bg-[#6675ff] hover:bg-[#7383ff] disabled:opacity-40 disabled:cursor-not-allowed text-white transition-all"
                  :title="getRateLimitMessage"
                >
                  <svg
                    v-if="isLogAnalysisInProgress"
                    class="w-4 h-4 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                  <svg
                    v-else-if="isVoiceRecording"
                    class="w-4 h-4 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                  </svg>
                  <img v-else src="/send_icon.svg" alt="send" class="w-4 h-4 mx-auto" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="messages.length === 0 && (!isHistoryLoaded || !isLoading)" class="flex flex-wrap justify-center gap-3 mt-5">
          <button
            @click="selectQuickQuestion('Какие рекомендации для предотвращения атак?')"
            :disabled="isQuickQuestionBlocked"
            class="quick-pill"
          >
            Рекомендации
          </button>
          <button
            @click="selectQuickQuestion('Какие тренды в безопасности?')"
            :disabled="isQuickQuestionBlocked"
            class="quick-pill"
          >
            Тренды
          </button>
          <button
            @click="selectQuickQuestion('Покажи релевантные техники MITRE ATT&CK для этих инцидентов')"
            :disabled="isQuickQuestionBlocked"
            class="quick-pill"
          >
            MITRE
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно подтверждения нового чата -->
    <div
      v-if="showNewChatModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="showNewChatModal = false"
    >
      <div class="bg-[#252525] rounded-xl max-w-md w-full border border-[#3C3C3C]">
        <!-- Заголовок модального окна -->
        <div class="bg-[#252525] rounded-xl px-6 py-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Подтверждение</h2>
          <button
            @click="showNewChatModal = false"
            class="hover:text-white transition-colors p-1"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Содержимое модального окна -->
        <div class="p-6">
          <p class="mb-6">
            Вы уверены, что хотите начать новый чат? Все сообщения будут удалены, 
            а контекст ассистента будет полностью очищен.
          </p>
          <div class="flex gap-3 justify-end">
            <button
              @click="showNewChatModal = false"
              class="px-4 py-2 bg-[#343434] hover:bg-[#444444] rounded-lg transition-colors"
            >
              Отмена
            </button>
            <button
              @click="confirmNewChat"
              :disabled="isLoading"
              class="px-4 py-2 bg-[#9F2727] hover:bg-[#C22D2D] disabled:bg-dark-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
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
import { chat, logs, speech } from '@/services/api'
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
const messageInput = ref(null)
const inputMessage = ref('')
const isLoading = computed({
  get: () => appStore.chatIsLoading,
  set: (value) => { appStore.chatIsLoading = value },
})
const isLogAnalysisInProgress = computed({
  get: () => appStore.chatIsLogAnalysisInProgress,
  set: (value) => { appStore.chatIsLogAnalysisInProgress = value },
})
const lastMessageTime = ref(0)
const isRateLimited = ref(false)
const isEmptyFile = ref(false)
const showNewChatModal = ref(false)
const isHistoryLoaded = ref(false)
const topAlignSpacerHeight = ref(0)
const showCustomScrollbar = ref(false)
const scrollbarThumbHeight = ref(0)
const scrollbarThumbTop = ref(0)
const isDraggingScrollbar = ref(false)
const scrollbarDragStartOffset = ref(0)
const copiedMessageIndex = ref(null)
let clearNotificationsTimer = null
let copyResetTimer = null

// Константы ограничений
const MAX_MESSAGE_LENGTH = 500
const RATE_LIMIT_DELAY = 2000 // 2 секунды
const NOTIFICATION_CLEAR_DELAY = 5000 // 5 секунд до снятия выделения
const USER_MESSAGE_TOP_OFFSET = 16 // Отступ от верхней границы контейнера при автопрокрутке
const MIN_SCROLLBAR_THUMB_HEIGHT = 32
const MAX_SCROLLBAR_THUMB_HEIGHT = 160
const SCROLLBAR_EDGE_GAP = 96

const messages = ref([])
const shouldSyncAfterBackgroundCompletion = ref(false)

const validateSberSpeechKey = async () => {
  isVoiceKeyCheckInProgress.value = true
  try {
    const response = await speech.validate()
    const isValid = Boolean(response?.data?.success)

    isVoiceKeyValid.value = isValid
    voiceKeyError.value = response?.data?.reason || ''
    if (!isValid) {
      console.warn('SaluteSpeech key validation failed:', response?.data)
    }
  } catch (error) {
    console.warn('SaluteSpeech key validation error:', error)
    isVoiceKeyValid.value = false
    voiceKeyError.value = 'request_failed'
  } finally {
    isVoiceKeyCheckInProgress.value = false
  }
}

// Загрузка истории чата при монтировании
onMounted(async () => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('resize', updateCustomScrollbar)
  // Очищаем с задержкой при монтировании компонента
  clearNotifications(false)
  adjustTextareaHeight()

  await validateSberSpeechKey()

  if (isLoading.value) {
    shouldSyncAfterBackgroundCompletion.value = true
  }
  
  // Загружаем историю чата из БД
  await loadChatHistory()
  isHistoryLoaded.value = true
})

// Функция загрузки истории чата
const loadChatHistory = async () => {
  try {
    const userId = appStore.currentUser?.id
    if (!userId) {
      console.error('User not authenticated')
      // Для нового/неавторизованного состояния чат остается пустым
      messages.value = []
      return
    }
    
    const response = await chat.getMessages(userId, 50)
    
    if (response.data && response.data.data && response.data.data.length > 0) {
      // Преобразуем сообщения из БД в формат компонента
      messages.value = response.data.data.map(msg => ({
        role: msg.role === 'user' ? 'user' : (msg.role === 'notice' ? 'notice' : 'ai'),
        text: msg.content,
        isNew: false,
      }))

      // При открытии чата прокручиваем к последнему сообщению пользователя,
      // используя ту же логику top-align, что и при отправке сообщения.
      const lastUserMessageIndex = [...messages.value]
        .map(msg => msg.role)
        .lastIndexOf('user')

      if (lastUserMessageIndex >= 0) {
        await scrollMessageToTop(lastUserMessageIndex)
        topAlignSpacerHeight.value = Math.max(topAlignSpacerHeight.value - 32, 0)
        return
      }
    } else {
      // Если история пуста, оставляем чат пустым
      messages.value = []
    }
    
    scrollToBottom()
  } catch (error) {
    console.error('Error loading chat history:', error)
    // В случае ошибки также оставляем чат пустым
    messages.value = []
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
    // Перезагружаем историю чата при возврате на страницу
    isHistoryLoaded.value = false
    loadChatHistory().then(() => {
      isHistoryLoaded.value = true
      clearNotifications(false)
      nextTick(() => updateCustomScrollbar())
    }).catch((error) => {
      console.error('Error reloading chat history:', error)
      isHistoryLoaded.value = true
    })
  }
}, { immediate: true })

watch([messages, isLoading, topAlignSpacerHeight], () => {
  nextTick(() => updateCustomScrollbar())
}, { deep: true })

const syncChatHistoryIfVisible = async () => {
  if (route.path !== '/chat' || document.visibilityState !== 'visible') return

  await loadChatHistory()
  clearNotifications(false)
  nextTick(() => updateCustomScrollbar())
}

watch(
  [
    () => appStore.chatUpdateVersion,
    () => appStore.reportsUpdateVersion,
  ],
  async ([chatVersion, reportVersion], [prevChatVersion, prevReportVersion]) => {
    if (chatVersion === prevChatVersion && reportVersion === prevReportVersion) return
    await syncChatHistoryIfVisible()
  }
)

watch(
  () => isLoading.value,
  async (loadingNow, loadingPrev) => {
    if (loadingPrev && !loadingNow && shouldSyncAfterBackgroundCompletion.value) {
      await loadChatHistory()
      shouldSyncAfterBackgroundCompletion.value = false
    }
  }
)

// Очистка при возвращении фокуса на вкладку
const handleVisibilityChange = () => {
  if (!document.hidden && route.path === '/chat') {
    clearNotifications()
  }
}

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('resize', updateCustomScrollbar)
  stopScrollbarDrag()
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
  if (isVoiceRecording.value) return 'Остановить запись и распознать'
  if (isLogAnalysisInProgress.value) return 'Отменить анализ лога'
  if (isLoading.value) return 'Ожидание ответа агента...'
  if (isRateLimited.value) return 'Подождите 2 секунды перед следующим сообщением'
  if (inputMessage.value.length > MAX_MESSAGE_LENGTH) return 'Сообщение слишком длинное'
  if (!inputMessage.value.trim()) return 'Введите сообщение'
  return 'Отправить сообщение'
})

const canUseSendControl = computed(() => {
  if (isLogAnalysisInProgress.value) return true
  if (isVoiceRecording.value) return true
  return canSendMessage.value
})

const isSecondaryControlsBlocked = computed(() => {
  return isLoading.value || isRateLimited.value || isLogAnalysisInProgress.value
})

const isVoiceKeyValid = ref(false)
const isVoiceKeyCheckInProgress = ref(false)
const voiceKeyError = ref('')
const isVoiceInputEnabled = typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)
const isVoiceRecording = ref(false)
const isVoiceTranscribing = ref(false)
const shouldTranscribeOnStop = ref(false)
let voiceMediaRecorder = null
let voiceStream = null
let voiceChunks = []
let voiceStopTimer = null

const isQuickQuestionBlocked = computed(() => {
  return isLoading.value || isRateLimited.value || isLogAnalysisInProgress.value
})

const isInputBlocked = computed(() => {
  return isLoading.value || isRateLimited.value
})

const canUseVoiceControl = computed(() => {
  if (isVoiceRecording.value) return true
  return !isSecondaryControlsBlocked.value
    && isVoiceInputEnabled
    && isVoiceKeyValid.value
    && !isVoiceKeyCheckInProgress.value
    && !isVoiceTranscribing.value
})

const voiceControlTitle = computed(() => {
  if (!isVoiceInputEnabled) return 'Голосовой ввод недоступен'
  if (isVoiceKeyCheckInProgress.value) return 'Проверка ключа...'
  if (!isVoiceKeyValid.value) {
    if (voiceKeyError.value === 'missing_key') return 'Ключ SaluteSpeech API не настроен'
    return 'Ключ недействителен'
  }
  if (isVoiceRecording.value) return 'Остановить запись'
  if (isVoiceTranscribing.value) return 'Распознавание речи...'
  return 'Голосовой ввод'
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      updateCustomScrollbar()
    }
  })
}

const updateCustomScrollbar = () => {
  const container = chatContainer.value
  if (!container) return

  const { clientHeight, scrollHeight, scrollTop } = container
  const hasOverflow = scrollHeight > clientHeight + 1

  showCustomScrollbar.value = hasOverflow
  if (!hasOverflow) {
    scrollbarThumbHeight.value = 0
    scrollbarThumbTop.value = 0
    return
  }

  const rawThumbHeight = Math.floor((clientHeight / scrollHeight) * clientHeight)
  const thumbHeight = Math.min(
    MAX_SCROLLBAR_THUMB_HEIGHT,
    Math.max(rawThumbHeight, MIN_SCROLLBAR_THUMB_HEIGHT)
  )
  const cappedThumbHeight = Math.min(thumbHeight, clientHeight)
  const maxThumbTravel = Math.max(clientHeight - (SCROLLBAR_EDGE_GAP * 2) - cappedThumbHeight, 0)
  const maxScrollTop = Math.max(scrollHeight - clientHeight, 0)
  const thumbTop = maxScrollTop > 0
    ? SCROLLBAR_EDGE_GAP + (scrollTop / maxScrollTop) * maxThumbTravel
    : SCROLLBAR_EDGE_GAP

  scrollbarThumbHeight.value = cappedThumbHeight
  scrollbarThumbTop.value = thumbTop
}

const handleChatScroll = () => {
  updateCustomScrollbar()
}

const startScrollbarDrag = (event) => {
  if (!showCustomScrollbar.value) return

  isDraggingScrollbar.value = true
  scrollbarDragStartOffset.value = event.clientY - scrollbarThumbTop.value

  window.addEventListener('mousemove', onScrollbarDrag)
  window.addEventListener('mouseup', stopScrollbarDrag)
}

const onScrollbarDrag = (event) => {
  if (!isDraggingScrollbar.value || !chatContainer.value) return

  const container = chatContainer.value
  const maxThumbTravel = Math.max(
    container.clientHeight - (SCROLLBAR_EDGE_GAP * 2) - scrollbarThumbHeight.value,
    0
  )
  const minThumbTop = SCROLLBAR_EDGE_GAP
  const maxThumbTop = SCROLLBAR_EDGE_GAP + maxThumbTravel
  const maxScrollTop = Math.max(container.scrollHeight - container.clientHeight, 0)

  if (maxThumbTravel <= 0 || maxScrollTop <= 0) return

  const nextThumbTop = Math.min(
    Math.max(event.clientY - scrollbarDragStartOffset.value, minThumbTop),
    maxThumbTop
  )

  container.scrollTop = ((nextThumbTop - SCROLLBAR_EDGE_GAP) / maxThumbTravel) * maxScrollTop
}

const stopScrollbarDrag = () => {
  if (!isDraggingScrollbar.value) return

  isDraggingScrollbar.value = false
  window.removeEventListener('mousemove', onScrollbarDrag)
  window.removeEventListener('mouseup', stopScrollbarDrag)
}

const handleScrollbarTrackMouseDown = (event) => {
  if (!chatContainer.value || !showCustomScrollbar.value) return

  const trackRect = event.currentTarget.getBoundingClientRect()
  const relativeY = event.clientY - trackRect.top
  const maxThumbTravel = Math.max(
    chatContainer.value.clientHeight - (SCROLLBAR_EDGE_GAP * 2) - scrollbarThumbHeight.value,
    0
  )
  const minThumbTop = SCROLLBAR_EDGE_GAP
  const maxThumbTop = SCROLLBAR_EDGE_GAP + maxThumbTravel
  const maxScrollTop = Math.max(chatContainer.value.scrollHeight - chatContainer.value.clientHeight, 0)

  if (maxThumbTravel <= 0 || maxScrollTop <= 0) return

  const targetThumbTop = Math.min(
    Math.max(relativeY - scrollbarThumbHeight.value / 2, minThumbTop),
    maxThumbTop
  )

  chatContainer.value.scrollTop = ((targetThumbTop - SCROLLBAR_EDGE_GAP) / maxThumbTravel) * maxScrollTop
}

const scrollMessageToTop = async (messageIndex) => {
  // Сбрасываем спейсер перед расчетом, чтобы измерения были корректными
  topAlignSpacerHeight.value = 0
  await nextTick()

  const container = chatContainer.value
  if (!container) return

  const messageElements = container.querySelectorAll('.chat-message-item')
  const targetMessage = messageElements[messageIndex]
  if (!targetMessage) return

  const targetOffsetTop = Math.max(targetMessage.offsetTop, 0)
  const desiredScrollTop = Math.max(targetOffsetTop - USER_MESSAGE_TOP_OFFSET, 0)
  const maxScrollableTop = Math.max(container.scrollHeight - container.clientHeight, 0)
  const missingSpace = Math.max(desiredScrollTop - maxScrollableTop, 0)

  // Добавляем нижнее пространство, если без него нельзя поднять сообщение в самый верх
  if (missingSpace > 0) {
    topAlignSpacerHeight.value = missingSpace + USER_MESSAGE_TOP_OFFSET
    await nextTick()
  }

  container.scrollTop = desiredScrollTop
  updateCustomScrollbar()
}

const reduceTopAlignSpacerByLastAssistantMessage = async () => {
  if (topAlignSpacerHeight.value <= 0) return

  await nextTick()

  const container = chatContainer.value
  if (!container) return

  const messageElements = container.querySelectorAll('.chat-message-item')
  const lastMessage = messageElements[messageElements.length - 1]
  if (!lastMessage) return

  const assistantMessageHeight = Math.max(lastMessage.offsetHeight, 0)
  if (assistantMessageHeight <= 0) return

  const spacerReduction = assistantMessageHeight + 8

  // По мере появления ответов ассистента уменьшаем добавленное псевдопространство
  topAlignSpacerHeight.value = Math.max(topAlignSpacerHeight.value - spacerReduction, 0)
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

const getRecorderMimeType = () => {
  if (typeof MediaRecorder === 'undefined') return ''

  const candidates = [
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/webm;codecs=opus',
    'audio/webm',
  ]

  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ''
}

const stopVoiceRecording = (reason = 'manual', transcribe = false) => {
  if (voiceStopTimer) {
    clearTimeout(voiceStopTimer)
    voiceStopTimer = null
  }

  shouldTranscribeOnStop.value = transcribe

  if (voiceMediaRecorder && voiceMediaRecorder.state !== 'inactive') {
    voiceMediaRecorder.stop()
  }

  if (voiceStream) {
    voiceStream.getTracks().forEach((track) => track.stop())
    voiceStream = null
  }

  if (reason === 'timeout') {
    appStore.addNotification('Запись остановлена: лимит 30 секунд', 'info')
  }
}

const applyTranscriptionToInput = (text) => {
  const normalized = trimBoundaryEmptyLines(text || '')
  if (!normalized) return

  const current = inputMessage.value || ''
  const availableSpace = MAX_MESSAGE_LENGTH - current.length

  if (availableSpace <= 0) {
    appStore.addNotification('Достигнут лимит 500 символов', 'warning')
    return
  }

  const snippet = normalized.slice(0, availableSpace)
  const nextValue = current ? `${current} ${snippet}` : snippet

  if (normalized.length > snippet.length) {
    appStore.addNotification('Текст сокращен до 500 символов', 'warning')
  }

  inputMessage.value = nextValue
  adjustTextareaHeight()
}

const extractTranscript = (payload) => {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (payload.result) return payload.result
  if (payload.text) return payload.text
  if (payload.transcript) return payload.transcript
  const alt = payload.results?.[0]?.alternatives?.[0]?.transcript
  return alt || ''
}

const transcribeVoiceBlob = async (audioBlob) => {
  if (!audioBlob) return

  isVoiceTranscribing.value = true
  try {
    const response = await speech.transcribe(audioBlob)
    const data = response?.data
    const transcript = extractTranscript(data)

    if (!transcript) {
      throw new Error('Ответ распознавания пустой')
    }

    applyTranscriptionToInput(transcript)
  } catch (error) {
    console.error('Voice transcription failed:', error)
    appStore.addNotification('Не удалось распознать речь', 'error')
  } finally {
    isVoiceTranscribing.value = false
  }
}

const startVoiceRecording = async () => {
  if (!isVoiceInputEnabled || isVoiceRecording.value) return

  if (!isVoiceKeyValid.value) {
    appStore.addNotification('Ключ SaluteSpeech API недействителен', 'error')
    return
  }

  try {
    if (typeof MediaRecorder === 'undefined') {
      appStore.addNotification('Браузер не поддерживает запись аудио', 'error')
      return
    }

    voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = getRecorderMimeType()
    if (!mimeType) {
      appStore.addNotification('Браузер не поддерживает формат аудио для SaluteSpeech', 'error')
      stopVoiceRecording('manual', false)
      return
    }
    voiceChunks = []
    voiceMediaRecorder = new MediaRecorder(voiceStream, mimeType ? { mimeType } : undefined)

    voiceMediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        voiceChunks.push(event.data)
      }
    }

    voiceMediaRecorder.onstop = async () => {
      isVoiceRecording.value = false

      const blobType = voiceMediaRecorder?.mimeType || mimeType || 'audio/ogg;codecs=opus'
      const audioBlob = new Blob(voiceChunks, { type: blobType })
      voiceChunks = []

      if (!shouldTranscribeOnStop.value) {
        shouldTranscribeOnStop.value = false
        return
      }

      if (audioBlob.size === 0) {
        appStore.addNotification('Запись пуста', 'warning')
        shouldTranscribeOnStop.value = false
        return
      }

      await transcribeVoiceBlob(audioBlob)
      shouldTranscribeOnStop.value = false
    }

    voiceMediaRecorder.start()
    isVoiceRecording.value = true
    shouldTranscribeOnStop.value = false

    voiceStopTimer = setTimeout(() => {
      stopVoiceRecording('timeout', true)
    }, 30000)
  } catch (error) {
    console.error('Failed to start voice recording:', error)
    appStore.addNotification('Не удалось получить доступ к микрофону', 'error')
    stopVoiceRecording()
  }
}

const handleVoiceControlClick = async () => {
  if (isVoiceRecording.value) {
    stopVoiceRecording('manual', false)
    return
  }

  await startVoiceRecording()
}

const normalizeMessageText = (value) => {
  if (value === null || value === undefined) return ''

  const rawValue = typeof value === 'string' ? value : String(value)

  // Нормализуем переносы и удаляем ведущие переносы, если нет текста перед ними
  let normalized = rawValue.replace(/\r\n/g, '\n').replace(/^\n+/, '')

  // Между текстовыми фрагментами разрешаем максимум два переноса строки
  normalized = normalized.replace(/\n{3,}/g, '\n\n')

  return normalized
}

const trimBoundaryEmptyLines = (value) => {
  if (value === null || value === undefined) return ''

  const rawValue = typeof value === 'string' ? value : String(value)

  return rawValue
    .replace(/\r\n/g, '\n')
    .replace(/^(?:[\t ]*\n)+/, '')
    .replace(/(?:\n[\t ]*)+$/, '')
}

const pushNoticeMessage = (text) => {
  messages.value.push({
    role: 'notice',
    text,
    isNew: false,
  })
}

const handleMessageInput = () => {
  const normalized = normalizeMessageText(inputMessage.value)
  if (normalized !== inputMessage.value) {
    inputMessage.value = normalized
  }
  adjustTextareaHeight()
}

const copyMessageText = async (text, index) => {
  if (!text) {
    return
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }

    copiedMessageIndex.value = index
    if (copyResetTimer) {
      clearTimeout(copyResetTimer)
    }
    copyResetTimer = setTimeout(() => {
      copiedMessageIndex.value = null
      copyResetTimer = null
    }, 1800)
  } catch (error) {
    console.error('Failed to copy message text:', error)
    appStore.addNotification('Не удалось скопировать сообщение', 'error')
  }
}

const handleShiftEnter = (event) => {
  const currentValue = inputMessage.value || ''

  // Если текста нет, не добавляем перенос
  if (!currentValue.trim()) {
    event.preventDefault()
    return
  }

  const textarea = event.target
  const caretPos = textarea?.selectionStart ?? currentValue.length
  const beforeCaret = currentValue.slice(0, caretPos)

  // Разрешаем максимум два переноса подряд
  if (beforeCaret.endsWith('\n\n')) {
    event.preventDefault()
  }
}

const sendMessage = async () => {
  // Проверка возможности отправки
  if (!canSendMessage.value) return

  const userMessage = trimBoundaryEmptyLines(inputMessage.value)
  if (!userMessage.trim()) return
  
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
    text: userMessage,
  })
  const newUserMessageIndex = messages.value.length - 1

  // Сохраняем сообщение пользователя сразу, чтобы оно было видно при возврате в чат,
  // даже если ответ ассистента еще не пришел.
  await saveChatMessage('user', userMessage)

  inputMessage.value = ''
  isLoading.value = true
  
  // Сбрасываем высоту textarea после очистки
  adjustTextareaHeight()

  // Прокручиваем чат так, чтобы новое сообщение пользователя оказалось вверху
  scrollMessageToTop(newUserMessageIndex)

  // Отправляем сообщение AI агенту через API
  try {
    const userId = appStore.currentUser?.id
    if (!userId) {
      throw new Error('User not authenticated')
    }

    // Вызываем новый endpoint для обработки сообщения с AI
    const response = await chat.sendToAI(userId, userMessage)
    
    console.log('📦 Full API Response:', response.data)
    
    const aiResponse = response.data.agent_response
    const responseMode = response.data.mode || 'UNKNOWN'
    
    // Выводим режим работы в консоль браузера
    console.log(`🤖 AI Mode: ${responseMode}`)
    console.log(`📝 Response length: ${aiResponse.length} characters`)
    console.log(`💬 Message: "${userMessage}"`)
    console.log('---')
    
    messages.value.push({
      role: 'ai',
      text: aiResponse,
      isNew: false,
    })
    await reduceTopAlignSpacerByLastAssistantMessage()
    
  } catch (error) {
    console.error('Error sending message to AI:', error)
    
    // Показываем сообщение об ошибке пользователю
    messages.value.push({
      role: 'ai',
      text: 'Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз позже.',
      isNew: false,
    })
    await reduceTopAlignSpacerByLastAssistantMessage()
    
    appStore.addNotification('Ошибка при отправке сообщения AI агенту', 'error')
  } finally {
    isLoading.value = false
    nextTick(updateCustomScrollbar)
  }
}

const cancelLogAnalysis = async () => {
  if (!isLogAnalysisInProgress.value || !appStore.chatLogUploadAbortController) return

  const userId = appStore.currentUser?.id
  if (userId) {
    try {
      await logs.cancelUpload(userId)
    } catch (error) {
      console.warn('Cancel upload request failed:', error)
    }
  }

  appStore.chatLogUploadAbortController.abort()
}

const handleSendControlClick = async () => {
  if (isLogAnalysisInProgress.value) {
    await cancelLogAnalysis()
    return
  }

  if (isVoiceRecording.value) {
    stopVoiceRecording('confirm', true)
    return
  }

  await sendMessage()
}

const selectQuickQuestion = (question) => {
  if (isQuickQuestionBlocked.value) return

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
    pushNoticeMessage(errorMsg)
    await saveChatMessage('notice', errorMsg)
    scrollToBottom()
    event.target.value = '' // Сбрасываем input
    return
  }
  
  // Показываем сообщение о загрузке
  const uploadMsg = `Загрузка файла "${file.name}" (${(file.size / 1024).toFixed(2)} KB)`
  messages.value.push({
    role: 'user',
    text: uploadMsg,
  })
  const newUserMessageIndex = messages.value.length - 1
  await saveChatMessage('user', uploadMsg)

  // Прокручиваем чат к сообщению о загрузке файла
  scrollMessageToTop(newUserMessageIndex)
  
  // Устанавливаем состояние загрузки
  isLoading.value = true
  isLogAnalysisInProgress.value = true
  appStore.chatLogUploadAbortController = new AbortController()
  
  try {
    // Отправляем файл на сервер для анализа
    const response = await logs.upload(userId, file, {
      signal: appStore.chatLogUploadAbortController.signal,
    })
    
    if (response.data.success) {
      // Показываем только AI-анализ
      const analysisMsg = response.data.ai_analysis
      
      messages.value.push({
        role: 'ai',
        text: analysisMsg,
        isNew: false,
      })
      await reduceTopAlignSpacerByLastAssistantMessage()
      
      // Сохраняем ответ в БД
      await saveChatMessage('agent', analysisMsg)
      
      // Явно обновляем историю отчетов, чтобы новый отчет появился в вкладке "История"
      appStore.notifyReportsUpdated()
      
      // Также явно обновляем чат, чтобы убедиться что сообщение отображается
      // (это гарантирует что сообщение синхронизировано после сохранения в БД)
      await syncChatHistoryIfVisible()
    } else {
      throw new Error(response.data.message || 'Ошибка при анализе файла')
    }
    
  } catch (error) {
    if (error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
      const canceledMsg = 'Анализ лога отменен пользователем.'

      pushNoticeMessage(canceledMsg)

      await reduceTopAlignSpacerByLastAssistantMessage()
      await saveChatMessage('notice', canceledMsg)

      appStore.addNotification('Анализ лога отменен', 'info')
      return
    }

    const responseStatus = error?.response?.status
    const responseDetail = String(error?.response?.data?.detail || '')
    if (responseStatus === 499 || responseDetail.toLowerCase().includes('отменен')) {
      const canceledMsg = 'Анализ лога отменен пользователем.'

      pushNoticeMessage(canceledMsg)

      await reduceTopAlignSpacerByLastAssistantMessage()
      await saveChatMessage('notice', canceledMsg)

      appStore.addNotification('Анализ лога отменен', 'info')
      return
    }

    console.error('Error uploading log file:', error)
    
    const errorMsg = `❌ Ошибка при анализе файла

${error.response?.data?.detail || error.message || 'Неизвестная ошибка'}`

    pushNoticeMessage(errorMsg)

    await reduceTopAlignSpacerByLastAssistantMessage()
    await saveChatMessage('notice', errorMsg)

    appStore.addNotification('Ошибка при анализе файла логов', 'error')
  } finally {
    appStore.chatLogUploadAbortController = null
    isLogAnalysisInProgress.value = false
    isLoading.value = false
    event.target.value = '' // Сбрасываем input
    nextTick(updateCustomScrollbar)
  }
}

onUnmounted(() => {
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
    copyResetTimer = null
  }

  if (isVoiceRecording.value) {
    stopVoiceRecording('manual')
  }
})

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

    // Очищаем сообщения в БД и контекст AI
    await chat.clearMessages(userId)

    // Очищаем локальный массив сообщений
    messages.value = []
    topAlignSpacerHeight.value = 0

    // Показываем уведомление с информацией об очистке
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
    nextTick(updateCustomScrollbar)
  }
}
</script>
<style scoped>
.chat-scroll-container {
  height: 100%;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.chat-scroll-container::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.chat-scroll-fade-bottom {
  -webkit-mask-image: linear-gradient(
    to bottom,
    #000 0%,
    #000 calc(100% - 104px),
    rgba(0, 0, 0, 0.82) calc(100% - 76px),
    rgba(0, 0, 0, 0.38) calc(100% - 40px),
    transparent 100%
  );
  mask-image: linear-gradient(
    to bottom,
    #000 0%,
    #000 calc(100% - 104px),
    rgba(0, 0, 0, 0.82) calc(100% - 76px),
    rgba(0, 0, 0, 0.38) calc(100% - 40px),
    transparent 100%
  );
}

.chat-scrollbar-track {
  position: absolute;
  top: 4px;
  right: 0;
  bottom: 4px;
  width: 5px;
  border-radius: 9999px;
  background: transparent;
  z-index: 10;
}

.chat-scrollbar-thumb {
  width: 100%;
  border: none;
  border-radius: 9999px;
  background: rgba(149, 149, 149, 0.7);
  cursor: grab;
  transition: background-color 0.15s ease;
}

.chat-scrollbar-thumb:hover,
.chat-scrollbar-thumb:active {
  background: rgba(149, 149, 149, 0.7);
}

.chat-scrollbar-thumb:active {
  cursor: grabbing;
}

.wave-glow {
  text-shadow: 0 0 24px rgba(103, 124, 255, 0.95), 0 0 58px rgba(93, 118, 255, 0.65);
}

.chat-composer {
  background: #252525;
  border: 1px solid #3C3C3C;
  box-shadow: none;
}

.chat-composer:focus-within {
  border-color: #515151;
}

.quick-pill {
  background: #242424;
  border: 1px solid #3C3C3C;
  color: #c2c2c2;
  border-radius: 14px;
  padding: 9px 22px;
  font-size: 0.85rem;
  line-height: 1;
  transition: all 0.2s ease;
}

.quick-pill:hover {
  border-color: rgba(103, 124, 255, 0.8);
  color: #f3f5ff;
  transform: translateY(-1px);
}

.quick-pill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: #3c3c3c;
  color: #8f94a3;
  transform: none;
}

.attachment-icon,
.attachment-ico {
  filter: brightness(0.66);
  transition: filter 0.2s ease;
}

button:hover .attachment-icon,
button:hover .attachment-ico {
  filter: brightness(0.80);
}

.copy-message-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border-radius: 6px;
  color: #b5bac7;
  transition: all 0.2s ease;
}

.copy-message-btn:hover {
  border-color: #6878ff;
  color: #e6e9ff;
  background: #2c3140;
}

.copy-message-btn:active {
  transform: translateY(1px);
}

/* Стили для markdown контента */
.markdown-content {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown-content :deep(p) {
  margin: 0.5em 0;
  overflow-wrap: anywhere;
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
  background-color: rgba(91, 117, 255, 0.12);
  border: 1px solid rgba(91, 117, 255, 0.28);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.9em;
  color: #c7d2ff;
}

.markdown-content :deep(pre) {
  background-color: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(91, 117, 255, 0.34);
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
  overflow-wrap: anywhere;
}

.markdown-content :deep(ul li) {
  list-style-type: disc;
}

.markdown-content :deep(ol li) {
  list-style-type: decimal;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid rgba(91, 117, 255, 0.6);
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
  border-bottom: 2px solid rgba(91, 117, 255, 0.34);
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
  color: #90a2ff;
  text-decoration: underline;
  transition: color 0.2s;
}

.markdown-content :deep(a:hover) {
  color: #b5c2ff;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid rgba(91, 117, 255, 0.34);
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
  border: 1px solid rgba(91, 117, 255, 0.34);
  padding: 8px 12px;
  text-align: left;
  overflow-wrap: anywhere;
}

.markdown-content :deep(th) {
  background-color: rgba(91, 117, 255, 0.2);
  font-weight: 600;
  color: #e5e7eb;
}

.markdown-content :deep(tr:nth-child(even)) {
  background-color: rgba(17, 24, 39, 0.3);
}
</style>
