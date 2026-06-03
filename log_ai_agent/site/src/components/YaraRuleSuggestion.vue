<template>
  <div class="yara-rule-suggestion mt-3 bg-[#252525]">
    <div class="flex items-center gap-2 mb-2 text-sm text-dark-300">
      <span class="font-medium text-dark-100">Предложенное YARA-правило</span>
      <span class="text-[#9CA3AF]">{{ rule.technique_id }} {{ rule.technique_name }}</span>
    </div>

    <div class="text-xs text-dark-400 mb-2 font-mono">
      {{ rule.rule_name }}
    </div>

    <pre class="yara-rule-content mb-3 bg-[#1A1A1A]"><code>{{ rule.rule_content }}</code></pre>

    <div v-if="status === 'pending'" class="flex gap-2">
      <button
        class="btn btn-sm flex items-center gap-1 bg-[#6C70F3]"
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
        class="btn btn-sm flex items-center gap-1 bg-[#414141]"
        :disabled="loading"
        @click="reject"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        Отклонить
      </button>
    </div>

    <div v-else-if="status === 'accepted'" class="flex items-center gap-2 text-sm text-dark-300">
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

    <div v-if="errorMsg" class="mt-2 text-xs text-dark-300">{{ errorMsg }}</div>
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

<style scoped>
.yara-rule-suggestion {
  border-radius: 0.75rem;
  padding: 1.25rem;
  box-shadow: none;
}

.yara-rule-content {
  border-radius: 0.5rem;
  padding: 0.75rem;
  overflow-x: auto;
  font-size: 0.75rem;
  font-family: monospace;
  color: rgb(229 231 235);
  line-height: 1.625;
  max-height: 12rem;
  overflow-y: auto;
}

.yara-rule-suggestion button {
  box-shadow: none;
}

.yara-rule-suggestion button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
