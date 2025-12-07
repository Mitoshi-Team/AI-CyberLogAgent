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
  logout: () => apiClient.post('/auth/logout'),
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
}

/**
 * Работа с чатом
 */
export const chat = {
  send: (message) => apiClient.post('/chat/message', { message }),
  history: (limit = 50) => apiClient.get('/chat/history', { params: { limit } }),
}

export default apiClient
