<template>
  <div class="yara-rule-suggestion card mt-3">
    <div class="flex items-center gap-2 mb-2">
      <span class="badge badge-info">🆕 YARA-правило</span>
      <span class="text-sm text-dark-400">
        {{ rule.technique_id }} {{ rule.technique_name }}
      </span>
    </div>

    <div class="text-xs text-dark-400 mb-1 font-mono">
      {{ rule.rule_name }}
    </div>

    <pre class="bg-dark-950/80 border border-dark-800 rounded-lg p-3 overflow-x-auto text-xs font-mono text-dark-200 leading-relaxed max-h-48 overflow-y-auto mb-3"><code>{{ rule.rule_content }}</code></pre>

    <div v-if="status === 'pending'" class="flex gap-2">
      <button
        class="btn btn-sm btn-primary flex items-center gap-1"
        :disabled="loading"
        @click="accept"
      >
        <svg v-if="!loading" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span v-if="loading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        Принять
      </button>
      <button
        class="btn btn-sm btn-secondary flex items-center gap-1"
        :disabled="loading"
        @click="reject"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        Отклонить
      </button>
    </div>

    <div v-else-if="status === 'accepted'" class="flex items-center gap-2 text-sm text-green-400">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
      Правило добавлено в базу
    </div>

    <div v-else-if="status === 'rejected'" class="flex items-center gap-2 text-sm text-dark-400">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
      Правило отклонено
    </div>

    <div v-if="errorMsg" class="mt-2 text-xs text-red-400">{{ errorMsg }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/app'
import { configRules } from '../services/api.js'

const appStore = useAppStore()

const props = defineProps({
  rule: {
    type: Object,
    required: true,
  },
})

const status = ref('pending')
const loading = ref(false)
const errorMsg = ref('')

async function accept() {
  loading.value = true
  errorMsg.value = ''
  try {
    await configRules.acceptPendingYaraRule(
      appStore.currentUser?.id,
      props.rule.pending_rule_id,
      props.rule.rule_name,
      props.rule.rule_content,
    )
    status.value = 'accepted'
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Ошибка при сохранении правила'
  } finally {
    loading.value = false
  }
}

async function reject() {
  loading.value = true
  errorMsg.value = ''
  try {
    await configRules.rejectPendingYaraRule(
      appStore.currentUser?.id,
      props.rule.pending_rule_id,
    )
    status.value = 'rejected'
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Ошибка при отклонении правила'
  } finally {
    loading.value = false
  }
}
</script>
