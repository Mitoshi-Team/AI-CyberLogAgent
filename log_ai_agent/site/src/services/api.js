import axios from 'axios'

/**
 * HTTP клиент для взаимодействия с FastAPI бэкенджем
 * Централизованное управление запросами и обработка ошибок
 */
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Добавление токена в заголовки запроса
 */
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * Обработка ошибок ответа
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

/**
 * Аутентификация пользователя
 */
export const auth = {
  login: (username, password) =>
    apiClient.post('/auth/login', { username, password }),
  logout: () => {
    localStorage.removeItem('auth_token')
    return Promise.resolve()
  },
  me: () => apiClient.get('/auth/me'),
}

/**
 * Работа с инцидентами
 */
export const incidents = {
  list: (params) => apiClient.get('/incidents', { params }),
  get: (id) => apiClient.get(`/incidents/${id}`),
  search: (query) => apiClient.get(`/incidents/search`, { params: { q: query } }),
}

/**
 * Работа со статистикой
 */
export const statistics = {
  overview: () => apiClient.get('/statistics/overview'),
  timeline: (days = 30) => apiClient.get('/statistics/timeline', { params: { days } }),
  severity: (startDate, endDate) => apiClient.get('/statistics/severity', { params: { start_date: startDate, end_date: endDate } }),
  threats: (startDate, endDate) => apiClient.get('/statistics/threats', { params: { start_date: startDate, end_date: endDate } }),
  activity: (periodType, startDate, endDate) => 
    apiClient.get('/statistics/activity', { 
      params: { 
        period_type: periodType, 
        start_date: startDate, 
        end_date: endDate 
      } 
    }),
}

/**
 * Работа с чатом
 */
export const chat = {
  sendMessage: (userId, role, content) => 
    apiClient.post('/chat/messages', { user_id: userId, role, content }),
  getMessages: (userId, limit = 50) => 
    apiClient.get('/chat/messages', { params: { user_id: userId, limit } }),
  clearMessages: (userId) => 
    apiClient.delete('/chat/messages', { params: { user_id: userId } }),
  sendToAI: (userId, message) =>
    apiClient.post('/chat/send', { user_id: userId, message }),
}

/**
 * Работа с отчетами
 */
export const reports = {
  history: (params) => apiClient.get('/reports/history', { params }),
  filters: () => apiClient.get('/reports/filters'),
  details: (id) => apiClient.get(`/reports/${id}`),
}

/**
 * Работа с логами
 */
export const logs = {
  upload: (userId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    return apiClient.post(`/logs/upload?user_id=${userId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

export default apiClient
