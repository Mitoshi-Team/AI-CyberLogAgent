/**
 * WebSocket сервис для получения уведомлений в реальном времени
 * Управляет подключением и обработкой сообщений о новых инцидентах
 */
class WebSocketService {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 20
    this.reconnectDelay = 2000
    this.maxReconnectDelay = 30000
    this.heartbeatInterval = 25000
    this.connectPromise = null
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.currentUrl = null
    this.manuallyClosed = false
  }

  /**
   * Подключение к WebSocket серверу
   */
  connect(url = null) {
    const websocketUrl = url || this.getDefaultUrl()

    this.currentUrl = websocketUrl
    this.manuallyClosed = false

    if (this.socket?.readyState === WebSocket.OPEN) {
      return Promise.resolve()
    }

    if (this.connectPromise) {
      return this.connectPromise
    }

    const pendingConnection = new Promise((resolve, reject) => {
      let isSettled = false

      try {
        this.socket = new WebSocket(websocketUrl)

        this.socket.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectAttempts = 0
          this.clearReconnectTimer()
          this.startHeartbeat()
          this.notifyListeners('connect')
          if (!isSettled) {
            isSettled = true
            resolve()
          }
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
          if (!isSettled) {
            isSettled = true
            reject(error)
          }
        }

        this.socket.onclose = () => {
          console.log('WebSocket disconnected')
          this.stopHeartbeat()
          this.notifyListeners('disconnect')
          this.socket = null
          this.attemptReconnect(websocketUrl)
        }
      } catch (error) {
        if (!isSettled) {
          isSettled = true
          reject(error)
        }
      }
    })

    this.connectPromise = pendingConnection.finally(() => {
      this.connectPromise = null
    })

    return this.connectPromise
  }

  getDefaultUrl() {
    const explicitUrl = import.meta.env.VITE_WEBSOCKET_URL
    if (explicitUrl) {
      return explicitUrl
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProtocol}//${window.location.host}/ws/`
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
    if (this.manuallyClosed) {
      return
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('WebSocket reconnection limit reached')
      this.notifyListeners('reconnect_failed')
      return
    }

    this.clearReconnectTimer()
    this.reconnectAttempts += 1

    const delay = Math.min(
      this.reconnectDelay * 2 ** (this.reconnectAttempts - 1),
      this.maxReconnectDelay
    )

    console.log(
      `WebSocket reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`
    )

    this.notifyListeners('reconnect_attempt', {
      attempt: this.reconnectAttempts,
      maxAttempts: this.maxReconnectAttempts,
      delay,
    })

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect(url).catch((error) => {
        console.warn('WebSocket reconnect failed:', error)
      })
    }, delay)
  }

  startHeartbeat() {
    this.stopHeartbeat()

    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }))
      }
    }, this.heartbeatInterval)
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * Закрытие соединения
   */
  disconnect() {
    this.manuallyClosed = true
    this.clearReconnectTimer()
    this.stopHeartbeat()

    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }
}

export default new WebSocketService()
