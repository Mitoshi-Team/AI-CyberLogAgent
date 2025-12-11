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
  
  // Состояние Sidebar
  const sidebarCollapsed = ref(false)
  
  // Состояние непрочитанных сообщений в чате
  const unreadChatMessages = ref(0)
  const originalPageTitle = ref(document.title)

  // Инициализация: восстанавливаем сессию из localStorage
  const initializeAuth = () => {
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('current_user')
    
    if (savedToken && savedUser) {
      try {
        token.value = savedToken
        currentUser.value = JSON.parse(savedUser)
        isAuthenticated.value = true
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
        }
        token.value = data.token
        
        // Сохраняем токен и пользователя в localStorage для сессии
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('current_user', JSON.stringify(currentUser.value))
        
        return { success: true }
      } else {
        return { success: false, message: data.message || 'Введен неверный логин или пароль' }
      }
    } catch (error) {
      console.error('Login error:', error)
      return { success: false, message: 'Введен неверный логин или пароль' }
    }
  }

  /**
   * Выход пользователя
   */
  const logout = () => {
    isAuthenticated.value = false
    currentUser.value = null
    token.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('current_user')
  }

  /**
   * Показать уведомление немедленно
   */
  const showNotificationNow = (message, type = 'info', duration = 5000, playSound = false) => {
    const id = Math.random()
    const notification = { id, message, type }
    
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
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      
      // Создаем очень низкий и приглушенный звук
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.frequency.value = 196 // G3 - низкая частота
      oscillator.type = 'sine' // Мягкий синусоидальный тон
      
      // Очень плавное и долгое нарастание и затухание
      gainNode.gain.setValueAtTime(0, audioContext.currentTime)
      gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.08) // Медленное нарастание
      gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.5) // Длинное затухание
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.5)
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
    addNotification(`Новый инцидент: ${incident.title}`, 'warning')
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

  return {
    isAuthenticated,
    currentUser,
    token,
    sidebarCollapsed,
    notifications,
    incidents,
    isLoadingIncidents,
    statistics,
    unreadChatMessages,
    login,
    logout,
    addNotification,
    removeNotification,
    loadIncidents,
    addUnreadChatMessage,
    clearUnreadChatMessages,
    addIncident,
  }
})
