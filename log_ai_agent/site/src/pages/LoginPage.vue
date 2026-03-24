<template>
  <div class="login-page">
    <video
      class="login-video"
      autoplay
      muted
      loop
      playsinline
      disablepictureinpicture
      disableremoteplayback
      controlslist="nodownload noplaybackrate noremoteplayback nofullscreen"
      tabindex="-1"
      aria-hidden="true"
      @contextmenu.prevent
    >
      <source src="/animation.webm" type="video/webm">
    </video>

    <div class="login-overlay"></div>

    <section class="login-panel" aria-label="Форма входа">
      <header class="brand-block">
        <img
          class="brand-logo"
          src="/wavescan_logo.svg"
          alt="Wavescan"
          width="380"
          height="186"
        />
      </header>

      <form @submit.prevent="handleLogin" class="login-form">
        <label class="field">
          <span class="sr-only">Логин</span>
          <input
            v-model="username"
            type="text"
            class="field-input"
            placeholder="Введите логин"
            required
          />
        </label>
        <label class="field password-field">
          <span class="sr-only">Пароль</span>
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            class="field-input"
            placeholder="Введите пароль"
            required
          />
          <button
            type="button"
            class="toggle-password"
            @click="showPassword = !showPassword"
            :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
          >
            <img
              v-if="!showPassword"
              src="/open_eye_icon.svg"
              alt=""
              aria-hidden="true"
            />
            <img
              v-else
              src="/close_eye_icon.svg"
              alt=""
              aria-hidden="true"
            />
          </button>
        </label>

        <button type="submit" :disabled="isLoading" class="submit-btn">
          <span v-if="!isLoading">Войти</span>
          <span v-else class="loader" aria-hidden="true"></span>
        </button>

        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      </form>

      <p class="help-text">Забыли логин или пароль? Обратитесь к<br>администратору.</p>
    </section>
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
  } catch {
    errorMessage.value = 'Введен неверный логин или пароль'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: stretch;
  background: #1f1f2c;
  font-family: 'Inter', 'Segoe UI', sans-serif;
}

.login-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
  user-select: none;
}

.login-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at 70% 25%, rgba(124, 99, 255, 0.08), transparent 44%),
    radial-gradient(circle at 78% 76%, rgba(72, 102, 255, 0.06), transparent 40%);
}

.login-panel {
  position: relative;
  z-index: 2;
  width: min(470px, 420px);
  min-width: 340px;
  height: 100vh;
  padding: clamp(26px, 3.6vh, 48px) 20px 22px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  background: rgba(37, 37, 37, 0.85);
  border-right: 1px solid rgba(60, 60, 60, 0.5);
  backdrop-filter: blur(8px);
}

.brand-block {
  width: min(340px, 100%);
  display: flex;
  justify-content: center;
  margin-bottom: clamp(28px, 5.4vh, 54px);
}

.brand-logo {
  display: block;
  width: min(300px, 100%);
  height: auto;
  object-fit: contain;
  margin-top: 50px;
}

.login-form {
  width: min(340px, 100%);
  display: flex;
  flex-direction: column;
  gap: 30px;
  margin-top: 50px;
}

.field {
  position: relative;
  display: block;
}

.login-form .field:first-child {
  margin-top: 12px;
}

.field-input {
  width: 100%;
  height: 44px;
  border: none;
  border-bottom: 2px solid rgba(170, 176, 195, 0.45);
  background: transparent;
  color: #ffffff;
  font-size: clamp(15px, 0.9vw, 17px);
  font-weight: 300;
  font-family: inherit;
  padding: 0 34px 0 0;
  outline: none;
}

.password-field .field-input {
  padding: 0 34px 0 0px;
}

.password-icon {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  opacity: 0.72;
  pointer-events: none;
}

.field-input::placeholder {
  color: rgba(235, 239, 255, 0.62);
  font-weight: 300;
}

.field-input:focus {
  border-bottom-color: rgba(139, 180, 255, 0.92);
}

.toggle-password {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  width: 26px;
  height: 26px;
  color: rgba(226, 233, 245, 0.62);
  cursor: pointer;
  padding: 0;
}

.toggle-password img {
  width: 20px;
  height: 20px;
}

.submit-btn {
  width: 152px;
  height: 44px;
  margin-top: 12px;
  align-self: center;
  border: solid 1px #3C3C3C;
  border-radius: 9px;
  background: #1964D3;
  color: #ffffff;
  font-size: 16px;
  font-weight: 400;
  font-family: inherit;
  cursor: pointer;;
}

.submit-btn:hover:not(:disabled) {
  background: #1963d3e4;
}


.loader {
  width: 16px;
  height: 16px;
  display: inline-block;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #ffffff;
  border-radius: 999px;
  animation: spin 0.9s linear infinite;
}

.error-text {
  margin: 2px 0 0;
  color: #ff7c9a;
  font-size: 12px;
  text-align: center;
}

.help-text {
  margin: auto 0 24px;
  max-width: 340px;
  color: rgba(255, 255, 255, 0.55);
  text-align: center;
  font-size: clamp(13px, 0.82vw, 15px);
  font-weight: 300;
  line-height: 1.28;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1024px) {
  .login-panel {
    width: min(460px, 54vw);
    min-width: 0;
    padding-inline: 20px;
  }

  .field-input {
    font-size: 15px;
    height: 42px;
  }

  .submit-btn {
    width: 138px;
    height: 40px;
    font-size: 15px;
  }

  .help-text {
    font-size: 12px;
  }
}

@media (max-width: 768px) {
  .login-page {
    justify-content: center;
  }

  .login-panel {
    width: 100%;
    min-width: 0;
    border-right: none;
    border-left: none;
    height: 100vh;
    padding-inline: 20px;
  }

  .brand-block {
    margin-top: 10px;
    margin-bottom: 26px;
  }

  .brand-logo {
    width: min(296px, 90%);
  }

  .login-form {
    width: 100%;
    gap: 24px;
    margin-top: clamp(14px, 3vh, 24px);
  }

  .field-input {
    height: 38px;
    font-size: 13px;
    border-bottom-width: 1px;
  }

  .submit-btn {
    width: 128px;
    height: 36px;
    border-radius: 8px;
    font-size: 14px;
  }

  .help-text {
    max-width: 320px;
    margin: auto auto 14px;
    font-size: 11px;
  }
}
</style>
