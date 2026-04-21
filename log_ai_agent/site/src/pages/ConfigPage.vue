<template>
  <div class="pt-8 pb-8">
    <div class="px-8">
      <div class="mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">Конфиг</h1>
        <p class="text-[#7f8799]">Настройка конфигурации системы</p>
      </div>

      <div class="mb-8 rounded-xl border border-[#2d313d] bg-[#252525] p-6">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Sigma правила</h2>
          <button
            @click="createSigmaFile"
            class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors flex items-center justify-center"
            title="Добавить файл Sigma"
          >
            <img src="/plus_icon.svg" alt="add" class="w-4 h-4" />
          </button>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div class="rounded-lg border border-[#2d313d] bg-[#242424] p-3">
            <p class="text-sm font-medium text-[#949daf] mb-3">Каталог файлов</p>
            <div class="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              <button
                v-for="fileName in sigmaFiles"
                :key="fileName"
                @click="selectSigmaFile(fileName)"
                class="w-full text-left px-3 py-2 rounded-lg border transition-colors"
                :class="selectedSigmaFile === fileName
                  ? 'bg-[#2f2f2f] border-[#4a5070] text-white'
                  : 'bg-[#252525] border-[#2d313d] text-[#c6cde0] hover:bg-[#2f2f2f]'"
              >
                {{ fileName }}
              </button>
              <p v-if="!sigmaFiles.length" class="text-sm text-[#7f8799]">Файлы не найдены</p>
            </div>
          </div>

          <div class="rounded-lg border border-[#2d313d] bg-[#242424] p-3">
            <div class="flex items-center justify-between mb-3">
              <p class="text-sm font-medium text-[#949daf]">
                Редактор: <span class="text-[#d8deec]">{{ selectedSigmaFile || '—' }}</span>
              </p>
              <div class="flex items-center gap-2">
                <button
                  @click="deleteSigmaFile"
                  :disabled="!selectedSigmaFile || sigmaSaving || sigmaDeleting"
                  class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  title="Удалить Sigma файл"
                >
                  <img src="/trash_icon.svg" alt="delete" class="w-4 h-4" />
                </button>
                <button
                  @click="saveSigmaFile"
                  :disabled="!selectedSigmaFile || sigmaSaving || sigmaDeleting"
                  class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  title="Сохранить Sigma файл"
                >
                  <img src="/save_icon.svg" alt="save" class="w-4 h-4" />
                </button>
              </div>
            </div>
            <textarea
              v-model="sigmaEditorContent"
              class="w-full h-[420px] resize-none rounded-lg border border-[#2d313d] bg-[#1A1A1A] p-3 text-[#d6dceb] font-mono text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-[#7971F0] focus:border-transparent"
              spellcheck="false"
              placeholder="Выберите файл Sigma для редактирования"
            />
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-[#2d313d] bg-[#252525] p-6">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Yara правила</h2>
          <button
            @click="saveYaraFile"
            :disabled="yaraSaving"
            class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            title="Сохранить Yara файл"
          >
            <img src="/save_icon.svg" alt="save" class="w-4 h-4" />
          </button>
        </div>
        <textarea
          v-model="yaraEditorContent"
          class="w-full h-[420px] resize-none rounded-lg border border-[#2d313d] bg-[#1A1A1A] p-3 text-[#d6dceb] font-mono text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-[#7971F0] focus:border-transparent"
          spellcheck="false"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { configRules } from '@/services/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const sigmaFiles = ref([])
const selectedSigmaFile = ref('')
const sigmaEditorContent = ref('')
const sigmaSaving = ref(false)
const sigmaDeleting = ref(false)

const yaraEditorContent = ref('')
const yaraSaving = ref(false)

const loadSigmaFiles = async () => {
  try {
    const response = await configRules.listSigmaFiles()
    sigmaFiles.value = response.data.files || []
    if (!selectedSigmaFile.value && sigmaFiles.value.length > 0) {
      await selectSigmaFile(sigmaFiles.value[0])
    }
  } catch (error) {
    console.error('Ошибка загрузки Sigma файлов:', error)
    appStore.addNotification('Ошибка загрузки Sigma файлов', 'error')
  }
}

const selectSigmaFile = async (fileName) => {
  selectedSigmaFile.value = fileName
  try {
    const response = await configRules.getSigmaFile(fileName)
    sigmaEditorContent.value = response.data.content || ''
  } catch (error) {
    console.error('Ошибка чтения Sigma файла:', error)
    appStore.addNotification('Ошибка чтения Sigma файла', 'error')
  }
}

const createSigmaFile = async () => {
  const fileName = window.prompt('Введите имя нового файла (.yml или .yaml):')
  if (!fileName) {
    return
  }

  try {
    await configRules.createSigmaFile(fileName.trim())
    await loadSigmaFiles()
    await selectSigmaFile(fileName.trim())
    appStore.addNotification('Новый Sigma файл создан', 'success')
  } catch (error) {
    console.error('Ошибка создания Sigma файла:', error)
    const message = error?.response?.data?.detail || 'Ошибка создания Sigma файла'
    appStore.addNotification(message, 'error')
  }
}

const saveSigmaFile = async () => {
  if (!selectedSigmaFile.value) {
    return
  }

  sigmaSaving.value = true
  try {
    await configRules.saveSigmaFile(selectedSigmaFile.value, sigmaEditorContent.value)
    appStore.addNotification('Sigma файл сохранен и обновлен в Docker', 'success')
  } catch (error) {
    console.error('Ошибка сохранения Sigma файла:', error)
    const message = error?.response?.data?.detail || 'Ошибка сохранения Sigma файла'
    appStore.addNotification(message, 'error')
  } finally {
    sigmaSaving.value = false
  }
}

const deleteSigmaFile = async () => {
  if (!selectedSigmaFile.value) {
    return
  }

  const fileToDelete = selectedSigmaFile.value
  const confirmed = window.confirm(`Удалить файл ${fileToDelete}?`)
  if (!confirmed) {
    return
  }

  sigmaDeleting.value = true
  try {
    await configRules.deleteSigmaFile(fileToDelete)
    const oldFiles = [...sigmaFiles.value]
    await loadSigmaFiles()

    const remainingFiles = sigmaFiles.value.filter((name) => name !== fileToDelete)
    if (!remainingFiles.includes(selectedSigmaFile.value)) {
      const oldIndex = oldFiles.indexOf(fileToDelete)
      const nextFile = remainingFiles[Math.min(oldIndex, remainingFiles.length - 1)]
      if (nextFile) {
        await selectSigmaFile(nextFile)
      } else {
        selectedSigmaFile.value = ''
        sigmaEditorContent.value = ''
      }
    }

    appStore.addNotification('Sigma файл удален и обновлен в Docker', 'success')
  } catch (error) {
    console.error('Ошибка удаления Sigma файла:', error)
    const message = error?.response?.data?.detail || 'Ошибка удаления Sigma файла'
    appStore.addNotification(message, 'error')
  } finally {
    sigmaDeleting.value = false
  }
}

const loadYaraFile = async () => {
  try {
    const response = await configRules.getYaraFile()
    yaraEditorContent.value = response.data.content || ''
  } catch (error) {
    console.error('Ошибка чтения Yara файла:', error)
    appStore.addNotification('Ошибка чтения Yara файла', 'error')
  }
}

const saveYaraFile = async () => {
  yaraSaving.value = true
  try {
    await configRules.saveYaraFile(yaraEditorContent.value)
    appStore.addNotification('Yara файл сохранен и обновлен в Docker', 'success')
  } catch (error) {
    console.error('Ошибка сохранения Yara файла:', error)
    const message = error?.response?.data?.detail || 'Ошибка сохранения Yara файла'
    appStore.addNotification(message, 'error')
  } finally {
    yaraSaving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadSigmaFiles(), loadYaraFile()])
})
</script>
