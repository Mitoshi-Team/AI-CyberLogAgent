<template>
  <div class="fixed top-4 right-4 space-y-2 max-w-xs z-50">
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
        <div class="flex items-center gap-2">
          <div :class="['notification-icon', `icon-${notification.type}`]">
            <component :is="getIcon(notification.type)" />
          </div>
          <p class="text-xs font-medium flex-1">{{ notification.message }}</p>
        </div>
        <button
          @click="appStore.removeNotification(notification.id)"
          class="text-slate-400 hover:text-slate-600 flex-shrink-0"
        >
          <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
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
  @apply flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg shadow-xl bg-dark-900/95 backdrop-blur-xl border;
}

.notification-success {
  @apply border-l-4 border-success-500 border-t border-r border-b border-success-500/20 shadow-success-500/20;
}

.notification-warning {
  @apply border-l-4 border-warning-500 border-t border-r border-b border-warning-500/20 shadow-warning-500/20;
}

.notification-danger {
  @apply border-l-4 border-danger-500 border-t border-r border-b border-danger-500/20 shadow-danger-500/20;
}

.notification-info {
  @apply border-l-4 border-primary-500 border-t border-r border-b border-primary-500/20 shadow-primary-500/20;
}

.notification-icon {
  @apply w-5 h-5;
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

.notification p {
  @apply text-dark-100;
}

.notification button {
  @apply text-dark-400 hover:text-dark-200;
}

.slide-enter-active {
  @apply transition-all duration-500 ease-out;
}

.slide-leave-active {
  @apply transition-all duration-300 ease-in;
}

.slide-enter-from {
  @apply -translate-y-8 translate-x-8 opacity-0 scale-95;
}

.slide-leave-to {
  @apply translate-x-full opacity-0 scale-90;
}

.slide-move {
  @apply transition-transform duration-300;
}
</style>
