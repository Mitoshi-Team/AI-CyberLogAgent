import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auth } from '@/services/api'

/**
 * Хранилище состояния приложения
 * Управляет аутентификацией, уведомлениями и общим состоянием UI
 */
export const useAppStore = defineStore('app', () => {
  // Состояние аутентификации
  const isAuthenticated = ref(false)
  const currentUser = ref(null)
  const token = ref(localStorage.getItem('auth_token') || null)
  const isAdmin = computed(() => Boolean(currentUser.value?.isAdmin))
  const authSynced = ref(false)
  
  // Состояние Sidebar
  const sidebarCollapsed = ref(false)
  
  // Состояние непрочитанных сообщений в чате
  const unreadChatMessages = ref(0)
  const chatIsLoading = ref(false)
  const chatIsLogAnalysisInProgress = ref(false)
  const chatLogUploadAbortController = ref(null)
  const originalPageTitle = ref(document.title)
  const chatUpdateVersion = ref(0)
  const reportsUpdateVersion = ref(0)

  // Pipeline progress for log analysis
  const pipelineStages = ref([])
  const pipelineCurrentStageName = ref('')
  const pipelineCurrentStageLabel = ref('')
  const pipelineStartTime = ref(null)
  const pipelineElapsed = ref(0)

  // Инициализация: восстанавливаем сессию из localStorage
  const initializeAuth = () => {
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('current_user')
    
    if (savedToken && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser)
        token.value = savedToken
        currentUser.value = {
          ...parsedUser,
          isAdmin: Boolean(parsedUser?.isAdmin),
        }
        isAuthenticated.value = true
        authSynced.value = false
      } catch (error) {
        console.error('Error restoring session:', error)
        logout()
      }
    }
  }

  // Вызываем инициализацию при создании store
  initializeAuth()

  // Уведомления
  const notifications = ref([])
  const pendingNotifications = ref([]) // Очередь уведомлений для показа при возврате на вкладку
  const incidents = ref([])
  const isLoadingIncidents = ref(false)
  
  // Обработчик изменения видимости вкладки
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible' && pendingNotifications.value.length > 0) {
      // Показываем отложенные уведомления
      pendingNotifications.value.forEach(notif => {
        showNotificationNow(notif.message, notif.type, notif.duration, notif.playSound)
      })
      pendingNotifications.value = []
    }
  }
  
  // Подписываемся на изменение видимости
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }

  // Статистика
  const statistics = ref({
    totalIncidents: 0,
    criticalCount: 0,
    suspiciousCount: 0,
    normalCount: 0,
    lastUpdate: new Date(),
  })

  /**
   * Вход пользователя
   */
  const login = async (username, password) => {
    try {
      const { data } = await auth.login(username, password)
      
      if (data.success && data.user && data.token) {
        isAuthenticated.value = true
        currentUser.value = {
          id: data.user.user_id,
          username: data.user.login,
          email: `${data.user.login}@cyberagent.com`,
          isAdmin: Boolean(data.user.is_admin),
        }
        token.value = data.token
        
        // Сохраняем токен и пользователя в localStorage для сессии
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('current_user', JSON.stringify(currentUser.value))
        authSynced.value = true
        
        return { success: true }
      } else {
        return { success: false, message: data.message || 'Введен неверный логин или пароль' }
      }
    } catch (error) {
      console.error('Login error:', error)
      return { success: false, message: 'Введен неверный логин или пароль' }
    }
  }

  const refreshCurrentUser = async () => {
    if (!token.value) {
      return false
    }
    if (authSynced.value) {
      return true
    }

    try {
      const { data } = await auth.me()
      if (data?.success && data.user) {
        currentUser.value = {
          id: data.user.user_id,
          username: data.user.login,
          email: `${data.user.login}@cyberagent.com`,
          isAdmin: Boolean(data.user.is_admin),
        }
        localStorage.setItem('current_user', JSON.stringify(currentUser.value))
        isAuthenticated.value = true
        authSynced.value = true
        return true
      }
      return false
    } catch (error) {
      console.error('Error refreshing current user:', error)
      if (error?.response?.status === 401) {
        await logout()
      }
      return false
    }
  }

  /**
   * Выход пользователя
   */
  const logout = async () => {
    try {
      await auth.logout(currentUser.value?.id)
    } catch (error) {
      console.error('Logout API error:', error)
    } finally {
      isAuthenticated.value = false
      currentUser.value = null
      token.value = null
      authSynced.value = false
      chatIsLoading.value = false
      chatIsLogAnalysisInProgress.value = false
      chatLogUploadAbortController.value = null
      localStorage.removeItem('auth_token')
      localStorage.removeItem('current_user')
    }
  }

  const normalizeNotificationType = (type = 'info') => {
    const aliasMap = {
      error: 'danger',
      warn: 'warning',
    }
    return aliasMap[type] || type
  }

  /**
   * Показать уведомление немедленно
   */
  const showNotificationNow = (message, type = 'info', duration = 5000, playSound = false) => {
    const id = Math.random()
    const normalizedType = normalizeNotificationType(type)
    const notification = { id, message, type: normalizedType, duration }
    
    // Ограничение на 5 уведомлений - удаляем старые
    if (notifications.value.length >= 5) {
      notifications.value.shift()
    }
    
    notifications.value.push(notification)
    
    // Воспроизведение звука только если указано
    if (playSound) {
      playNotificationSound()
    }

    if (duration) {
      setTimeout(() => {
        removeNotification(id)
      }, duration)
    }

    return id
  }
  
  /**
   * Добавление уведомления (с проверкой видимости вкладки)
   */
  const addNotification = (message, type = 'info', duration = 5000, playSound = false) => {
    // Воспроизводим звук сразу, независимо от видимости вкладки
    if (playSound) {
      playNotificationSound()
    }
    
    // Если вкладка не активна, добавляем в очередь (только визуальное уведомление)
    if (document.visibilityState !== 'visible') {
      pendingNotifications.value.push({ message, type, duration, playSound: false }) // playSound: false т.к. уже воспроизвели
      return null
    }
    
    // Если вкладка активна, показываем сразу (без повторного звука)
    return showNotificationNow(message, type, duration, false) // playSound: false т.к. уже воспроизвели выше
  }
  
  /**
   * Воспроизведение звука уведомления
   */
  const playNotificationSound = () => {
    try {
      const audio = new Audio('/sounds/notification.mp3')
      audio.volume = 0.5 // Средняя громкость
      audio.play().catch(() => {
        // Игнорируем ошибки воспроизведения (например, если браузер блокирует автовоспроизведение)
      })
    } catch (e) {
      // Игнорируем ошибки воспроизведения
    }
  }

  /**
   * Удаление уведомления
   */
  const removeNotification = (id) => {
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  /**
   * Загрузка инцидентов
   */
  const loadIncidents = async () => {
    isLoadingIncidents.value = true
    try {
      // Имитация данных - будет заменено на реальный API запрос
      incidents.value = [
        {
          id: 1,
          title: 'Попытка несанкционированного доступа',
          description: 'Обнаружено 15 неудачных попыток входа с IP 192.168.1.100',
          severity: 'critical',
          status: 'open',
          timestamp: new Date(Date.now() - 5 * 60000),
          source: 'SSH Log',
          details: {
            attempts: 15,
            sourceIP: '192.168.1.100',
            targetUser: 'admin',
          },
        },
        {
          id: 2,
          title: 'Аномальная активность базы данных',
          description: 'Необычно высокий объём запросов к БД в течение 10 минут',
          severity: 'warning',
          status: 'open',
          timestamp: new Date(Date.now() - 15 * 60000),
          source: 'Database Log',
          details: {
            queryCount: 5000,
            avgTime: '250ms',
            normalTime: '50ms',
          },
        },
      ]

      // Обновление статистики
      statistics.value = {
        totalIncidents: incidents.value.length,
        criticalCount: incidents.value.filter((i) => i.severity === 'critical').length,
        suspiciousCount: incidents.value.filter((i) => i.severity === 'warning').length,
        normalCount: incidents.value.filter((i) => i.severity === 'normal').length,
        lastUpdate: new Date(),
      }
    } finally {
      isLoadingIncidents.value = false
    }
  }

  /**
   * Добавление нового инцидента (получен через WebSocket)
   */
  const addIncident = (incident) => {
    incidents.value.unshift(incident)
    if (incident.severity === 'critical') {
      statistics.value.criticalCount++
    } else if (incident.severity === 'warning') {
      statistics.value.suspiciousCount++
    }
    statistics.value.totalIncidents++
    if (incident.source === 'Manual Log Upload') {
      addNotification('Отчет по запросу был сформирован', 'info')
      return
    }
    addNotification('Найден новый инцидент!', 'warning')
  }
  
  /**
   * Добавление непрочитанного сообщения в чат
   */
  const addUnreadChatMessage = () => {
    unreadChatMessages.value++
    updatePageTitle()
  }
  
  /**
   * Очистка счетчика непрочитанных сообщений
   */
  const clearUnreadChatMessages = () => {
    unreadChatMessages.value = 0
    updatePageTitle()
  }
  
  /**
   * Обновление заголовка страницы с индикатором непрочитанных
   */
  const updatePageTitle = () => {
    if (unreadChatMessages.value > 0) {
      document.title = `(${unreadChatMessages.value}) ${originalPageTitle.value}`
    } else {
      document.title = originalPageTitle.value
    }
  }

  /**
   * Сигнализирует страницам отчетов о появлении нового отчета в реальном времени.
   */
  const notifyReportsUpdated = (_payload = null) => {
    reportsUpdateVersion.value += 1
  }

  /**
   * Сигнализирует странице чата о новом сообщении от ассистента.
   */
  const notifyChatUpdated = (_payload = null) => {
    chatUpdateVersion.value += 1
  }

  const startPipeline = () => {
    pipelineStages.value = []
    pipelineCurrentStageName.value = ''
    pipelineCurrentStageLabel.value = ''
    pipelineStartTime.value = Date.now()
    pipelineElapsed.value = 0
  }

  const setPipelineStage = (stageName, label) => {
    if (stageName === 'complete') {
      if (pipelineCurrentStageLabel.value) {
        pipelineStages.value.push({ stage: pipelineCurrentStageName.value, label: pipelineCurrentStageLabel.value })
      }
      pipelineCurrentStageName.value = ''
      pipelineCurrentStageLabel.value = ''
      return
    }
    if (stageName === pipelineCurrentStageName.value) return
    if (pipelineCurrentStageLabel.value) {
      pipelineStages.value.push({ stage: pipelineCurrentStageName.value, label: pipelineCurrentStageLabel.value })
    }
    pipelineCurrentStageName.value = stageName
    pipelineCurrentStageLabel.value = label
  }

  const clearPipeline = () => {
    pipelineStages.value = []
    pipelineCurrentStageName.value = ''
    pipelineCurrentStageLabel.value = ''
    pipelineStartTime.value = null
    pipelineElapsed.value = 0
  }

  return {
    isAuthenticated,
    currentUser,
    token,
    isAdmin,
    authSynced,
    sidebarCollapsed,
    notifications,
    incidents,
    isLoadingIncidents,
    statistics,
    unreadChatMessages,
    chatIsLoading,
    chatIsLogAnalysisInProgress,
    chatLogUploadAbortController,
    chatUpdateVersion,
    reportsUpdateVersion,
    pipelineStages,
    pipelineCurrentStageName,
    pipelineCurrentStageLabel,
    pipelineStartTime,
    pipelineElapsed,
    login,
    refreshCurrentUser,
    logout,
    addNotification,
    removeNotification,
    loadIncidents,
    addUnreadChatMessage,
    clearUnreadChatMessages,
    addIncident,
    notifyChatUpdated,
    notifyReportsUpdated,
    startPipeline,
    setPipelineStage,
    clearPipeline,
  }
})
