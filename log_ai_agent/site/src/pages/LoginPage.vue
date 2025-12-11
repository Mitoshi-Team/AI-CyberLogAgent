<template>
  <div class="min-h-screen bg-dark-950 flex items-center justify-center px-4 relative overflow-hidden">
    <!-- Фоновые эффекты -->
    <div class="absolute inset-0 overflow-hidden">
      <div class="absolute top-20 left-20 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse-soft"></div>
      <div class="absolute bottom-20 right-20 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl animate-pulse-soft" style="animation-delay: 1s;"></div>
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full">
        <div class="w-full h-full" style="background-image: radial-gradient(circle at 1px 1px, rgba(14, 165, 233, 0.05) 1px, transparent 0); background-size: 40px 40px;"></div>
      </div>
    </div>

    <div class="w-full max-w-md relative z-10">
      <!-- Логотип -->
      <div class="text-center mb-8">
        <div class="flex items-center justify-center gap-3 mb-4 pb-2">
          <div class="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-2xl shadow-primary-500/50 animate-glow">
            <svg class="w-7 h-7 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/>
            </svg>
          </div>
          <h1 class="text-4xl font-bold bg-gradient-to-r from-primary-400 via-primary-500 to-primary-600 bg-clip-text text-transparent leading-relaxed pb-1">CyberLog</h1>
        </div>
        <p class="text-dark-400 text-sm">AI-powered система мониторинга инцидентов</p>
      </div>

      <!-- Форма входа -->
      <div class="card backdrop-blur-2xl border-dark-800">
        <form @submit.prevent="handleLogin" class="space-y-6">
          <div>
            <label class="block text-sm font-medium text-dark-300 mb-2">
              Логин
            </label>
            <input
              v-model="username"
              type="text"
              class="input"
              placeholder="Введите логин"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-dark-300 mb-2">
              Пароль
            </label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="input pr-10"
                placeholder="Введите пароль"
                required
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-200 transition-colors"
              >
                <svg v-if="!showPassword" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              </button>
            </div>
          </div>

          <button
            type="submit"
            :disabled="isLoading"
            class="w-full btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden group"
          >
            <span v-if="!isLoading" class="relative z-10">Войти</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
            </span>
            <div class="absolute inset-0 bg-gradient-to-r from-primary-600 to-primary-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </button>

          <!-- Сообщение об ошибке -->
          <div v-if="errorMessage" class="text-center">
            <div class="inline-block px-4 py-2 bg-red-900/30 rounded-lg border border-red-700/50">
              <p class="text-sm text-red-400">{{ errorMessage }}</p>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const showPassword = ref(false)

const handleLogin = async () => {
  if (!username.value || !password.value) return

  isLoading.value = true
  errorMessage.value = ''
  
  try {
    const result = await appStore.login(username.value, password.value)
    
    if (result.success) {
      appStore.addNotification(`Добро пожаловать, ${username.value}!`, 'success')
      router.push('/')
    } else {
      errorMessage.value = result.message || 'Введен неверный логин или пароль'
    }
  } catch (error) {
    errorMessage.value = 'Введен неверный логин или пароль'
  } finally {
    isLoading.value = false
  }
}
</script>
