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
  const incidents = ref([])
  const isLoadingIncidents = ref(false)

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
   * Добавление уведомления
   */
  const addNotification = (message, type = 'info', duration = 3000) => {
    const id = Math.random()
    const notification = { id, message, type }
    notifications.value.push(notification)

    if (duration) {
      setTimeout(() => {
        removeNotification(id)
      }, duration)
    }

    return id
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

  return {
    isAuthenticated,
    currentUser,
    token,
    sidebarCollapsed,
    notifications,
    incidents,
    isLoadingIncidents,
    statistics,
    login,
    logout,
    addNotification,
    removeNotification,
    loadIncidents,
    addIncident,
  }
})
