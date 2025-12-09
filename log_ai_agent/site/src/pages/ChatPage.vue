<template>
  <div class="h-screen flex flex-col">
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Окно чата на всю высоту -->
      <div class="flex-1 flex flex-col bg-dark-900/30 border-l border-dark-800 overflow-hidden">
        <!-- История чата с фиксированной высотой и скроллом -->
        <div ref="chatContainer" class="flex-1 overflow-y-auto space-y-4 p-4 scrollbar-chat">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
          >
            <div
              :class="[
                'max-w-xs px-4 py-3 rounded-xl shadow-lg',
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-primary-600 to-primary-500 text-white rounded-br-none'
                  : 'bg-dark-800/80 backdrop-blur-xl border border-dark-700 text-dark-200 rounded-bl-none',
              ]"
            >
              <p class="text-sm leading-relaxed">{{ msg.text }}</p>
            </div>
          </div>
          <div v-if="isLoading" class="flex justify-start">
            <div class="bg-dark-800/80 backdrop-blur-xl border border-dark-700 px-4 py-3 rounded-xl rounded-bl-none shadow-lg">
              <div class="flex gap-1">
                <div class="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 0ms"/>
                <div class="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 150ms"/>
                <div class="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 300ms"/>
              </div>
            </div>
          </div>
        </div>

        <!-- Быстрые вопросы (компактные плашки над полем ввода) -->
        <div class="flex flex-wrap gap-2 px-4 py-3">
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
        <div class="flex gap-3 p-4 border-t border-dark-800 bg-dark-900/50">
          <input
            v-model="inputMessage"
            @keyup.enter="sendMessage"
            type="text"
            class="input flex-1"
            placeholder="Напишите вопрос об инцидентах..."
            :disabled="isLoading"
          />
          <button
            @click="sendMessage"
            :disabled="!inputMessage || isLoading"
            class="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8m0 8l-6-4m6 4l6-4"/>
            </svg>
          </button>
          
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
            class="btn bg-dark-800 hover:bg-dark-700 border border-dark-700 hover:border-primary-500/50 text-dark-300 hover:text-primary-400 transition-all"
            title="Загрузить .log файл"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const chatContainer = ref(null)
const fileInput = ref(null)
const inputMessage = ref('')
const isLoading = ref(false)
const uploadedLogFile = ref(null)
const messages = ref([
  {
    role: 'ai',
    text: 'Привет! Я CyberLog AI ассистент. Я помогу вам анализировать инциденты безопасности и предоставлять рекомендации. Какой у вас вопрос?',
  },
])

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return

  // Добавить сообщение пользователя
  messages.value.push({
    role: 'user',
    text: inputMessage.value,
  })

  const userMessage = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true
  
  scrollToBottom()

  // Имитация ответа AI
  setTimeout(() => {
    messages.value.push({
      role: 'ai',
      text: generateAIResponse(userMessage),
    })
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
