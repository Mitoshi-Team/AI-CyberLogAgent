<template>
  <div class="fixed top-4 right-4 space-y-3 max-w-sm z-50">
    <transition-group
      name="slide"
      tag="div"
      class="space-y-2"
    >
      <div
        v-for="notification in appStore.notifications.slice(0, 5)"
        :key="notification.id"
        :class="['notification', `notification-${notification.type}`]"
      >
        <div class="notification-body">
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <div :class="['notification-icon', `icon-${notification.type}`]">
              <component :is="getIcon(notification.type)" />
            </div>
            <p class="notification-text">{{ notification.message }}</p>
          </div>
          <button
            @click="appStore.removeNotification(notification.id)"
            class="notification-close"
            aria-label="Закрыть уведомление"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>
        <div
          v-if="notification.duration"
          class="notification-progress"
          :style="{ animationDuration: `${notification.duration}ms` }"
        />
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import IconSuccess from '@/components/icons/IconSuccess.vue'
import IconWarning from '@/components/icons/IconWarning.vue'
import IconError from '@/components/icons/IconError.vue'
import IconInfo from '@/components/icons/IconInfo.vue'

const appStore = useAppStore()

const getIcon = (type) => {
  const icons = {
    success: IconSuccess,
    warning: IconWarning,
    danger: IconError,
    info: IconInfo,
  }
  return icons[type] || IconInfo
}
</script>

<style scoped>
.notification {
  @apply relative overflow-hidden px-4 py-3.5 rounded-xl bg-[#252525] border;
}

.notification-body {
  @apply flex items-center justify-between gap-3;
}

.notification-success {
  @apply border-[#3C3C3C]/90 border-t border-r border-b;
}

.notification-warning {
  @apply border-[#3C3C3C]/90 border-t border-r border-b;
}

.notification-danger {
  @apply border-[#3C3C3C]/90 border-t border-r border-b;
}

.notification-info {
  @apply border-[#3C3C3C]/90 border-t border-r border-b;
}

.notification-icon {
  @apply w-6 h-6 flex-shrink-0;
}

.notification-text {
  @apply text-sm font-medium text-dark-100 leading-5;
}

.notification-close {
  @apply text-dark-400 hover:text-dark-200 flex-shrink-0 transition-colors;
}

.icon-success {
  @apply text-success-400;
}

.icon-warning {
  @apply text-warning-400;
}

.icon-danger {
  @apply text-danger-400;
}

.icon-info {
  @apply text-primary-400;
}

.notification-progress {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 2px;
  transform-origin: left center;
  animation-name: notification-progress;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
}

.notification-success .notification-progress {
  @apply bg-[#7971F0]/80;
}

.notification-warning .notification-progress {
  @apply bg-[#7971F0]/80;
}

.notification-danger .notification-progress {
  @apply bg-[#7971F0]/80;
}

.notification-info .notification-progress {
  @apply bg-[#7971F0]/80;
}

@keyframes notification-progress {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}

.slide-enter-active {
  @apply transition-all duration-500 ease-out;
}

.slide-leave-active {
  @apply transition-all duration-300 ease-in;
}

.slide-enter-from {
  @apply translate-x-full opacity-0 scale-95;
}

.slide-leave-to {
  @apply translate-x-full opacity-0 scale-90;
}

.slide-move {
  @apply transition-transform duration-300;
}
</style>
