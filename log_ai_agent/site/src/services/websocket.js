/**
 * WebSocket сервис для получения уведомлений в реальном времени
 * Управляет подключением и обработкой сообщений о новых инцидентах
 */
class WebSocketService {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
  }

  /**
   * Подключение к WebSocket серверу
   */
  connect(url = 'ws://localhost:8000/ws') {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(url)

        this.socket.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectAttempts = 0
          resolve()
        }

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.notifyListeners('message', data)
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e)
          }
        }

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.notifyListeners('error', error)
          reject(error)
        }

        this.socket.onclose = () => {
          console.log('WebSocket disconnected')
          this.notifyListeners('disconnect')
          this.attemptReconnect(url)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Отправка сообщения на сервер
   */
  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  /**
   * Подписка на события
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  /**
   * Отписка от событий
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * Уведомление всех слушателей
   */
  notifyListeners(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((callback) => callback(data))
    }
  }

  /**
   * Попытка переподключения
   */
  attemptReconnect(url) {
    // Отключаем автоматический реконнект, чтобы избежать спама ошибок
    // WebSocket не критичен для работы приложения
    console.log('WebSocket disconnected. Auto-reconnect disabled.')
  }

  /**
   * Закрытие соединения
   */
  disconnect() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }
}

export default new WebSocketService()
