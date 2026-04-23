<template>
  <header class="fixed top-0 right-0 left-64 bg-dark-900/80 backdrop-blur-xl border-b border-dark-800 z-40">
    <div class="px-8 py-2 flex items-center justify-end">
      <div class="flex items-center gap-4">
        <!-- Профиль -->
        <div class="flex items-center gap-3">
          <div class="text-right">
            <p class="text-sm font-medium text-dark-200">
              {{ appStore.currentUser?.username || 'User' }}
            </p>
            <p class="text-xs text-dark-500">Администратор</p>
          </div>
          <button
            @click="logout"
            class="p-2 text-dark-400 hover:text-danger-400 rounded-lg hover:bg-dark-800/50 transition-all"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { useRouter } from 'vue-router'

const appStore = useAppStore()
const router = useRouter()

const handleSearch = (e) => {
  const query = e.target.value
  if (query.length > 0) {
    router.push({ name: 'Incidents', query: { search: query } })
  }
}

const logout = async () => {
  await appStore.logout()
  router.push('/login')
}
</script>
