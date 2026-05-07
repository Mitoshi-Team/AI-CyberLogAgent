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
            @click="createYaraFile"
            class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors flex items-center justify-center"
            title="Добавить файл Yara"
          >
            <img src="/plus_icon.svg" alt="add" class="w-4 h-4" />
          </button>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div class="rounded-lg border border-[#2d313d] bg-[#242424] p-3">
            <p class="text-sm font-medium text-[#949daf] mb-3">Каталог файлов</p>
            <div class="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              <button
                v-for="fileName in yaraFiles"
                :key="fileName"
                @click="selectYaraFile(fileName)"
                class="w-full text-left px-3 py-2 rounded-lg border transition-colors"
                :class="selectedYaraFile === fileName
                  ? 'bg-[#2f2f2f] border-[#4a5070] text-white'
                  : 'bg-[#252525] border-[#2d313d] text-[#c6cde0] hover:bg-[#2f2f2f]'"
              >
                {{ fileName }}
              </button>
              <p v-if="!yaraFiles.length" class="text-sm text-[#7f8799]">Файлы не найдены</p>
            </div>
          </div>

          <div class="rounded-lg border border-[#2d313d] bg-[#242424] p-3">
            <div class="flex items-center justify-between mb-3">
              <p class="text-sm font-medium text-[#949daf]">
                Редактор: <span class="text-[#d8deec]">{{ selectedYaraFile || '—' }}</span>
              </p>
              <div class="flex items-center gap-2">
                <button
                  @click="deleteYaraFile"
                  :disabled="!selectedYaraFile || yaraSaving || yaraDeleting"
                  class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  title="Удалить Yara файл"
                >
                  <img src="/trash_icon.svg" alt="delete" class="w-4 h-4" />
                </button>
                <button
                  @click="saveYaraFile"
                  :disabled="!selectedYaraFile || yaraSaving || yaraDeleting"
                  class="w-9 h-9 rounded-lg bg-[#252525] hover:bg-[#2f2f2f] border border-[#2d313d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  title="Сохранить Yara файл"
                >
                  <img src="/save_icon.svg" alt="save" class="w-4 h-4" />
                </button>
              </div>
            </div>
            <textarea
              v-model="yaraEditorContent"
              class="w-full h-[420px] resize-none rounded-lg border border-[#2d313d] bg-[#1A1A1A] p-3 text-[#d6dceb] font-mono text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-[#7971F0] focus:border-transparent"
              spellcheck="false"
              placeholder="Выберите файл Yara для редактирования"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно создания файла -->
    <div
      v-if="showCreateFileModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="closeCreateFileModal"
    >
      <div class="bg-[#252525] rounded-xl max-w-md w-full border border-[#3C3C3C]">
        <!-- Заголовок модального окна -->
        <div class="bg-[#252525] rounded-xl px-6 py-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Создание файла</h2>
          <button
            @click="closeCreateFileModal"
            class="hover:text-white transition-colors p-1"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Содержимое модального окна -->
        <div class="p-6">
          <p class="mb-4 text-sm text-[#c6cde0]">
            {{ createFileType === 'sigma' ? 'Введите имя файла Sigma (.yml или .yaml):' : 'Введите имя файла Yara (.yar или .yara):' }}
          </p>
          <input
            v-model="createFileInput"
            type="text"
            class="w-full px-3 py-2 rounded-lg border border-[#3a3d46] bg-[#1A1A1A] text-[#f0f2f9] focus:outline-none focus:ring-2 focus:ring-[#7971F0] focus:border-transparent mb-6"
            :placeholder="createFileType === 'sigma' ? 'example.yml' : 'example.yar'"
            @keydown.enter="confirmCreateFile"
          />
          <div class="flex gap-3 justify-end">
            <button
              @click="closeCreateFileModal"
              class="px-4 py-2 bg-[#343434] hover:bg-[#444444] rounded-lg transition-colors text-[#c6cde0]"
            >
              Отмена
            </button>
            <button
              @click="confirmCreateFile"
              :disabled="!createFileInput.trim() || createFileLoading"
              class="px-4 py-2 bg-[#6675ff] hover:bg-[#7383ff] disabled:bg-[#4a4a4a] disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2 justify-center"
            >
              <span v-if="createFileLoading" class="inline-block w-4 h-4 border-2 border-[#e0e0e0] border-t-transparent rounded-full animate-spin"></span>
              {{ createFileLoading ? 'Создание...' : 'Создать' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно подтверждения удаления файла -->
    <div
      v-if="showDeleteFileModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="closeDeleteFileModal"
    >
      <div class="bg-[#252525] rounded-xl max-w-md w-full border border-[#3C3C3C]">
        <!-- Заголовок модального окна -->
        <div class="bg-[#252525] rounded-xl px-6 py-4 flex items-center justify-between">
          <h2 class="text-xl font-bold text-white">Подтверждение</h2>
          <button
            @click="closeDeleteFileModal"
            class="hover:text-white transition-colors p-1"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Содержимое модального окна -->
        <div class="p-6">
          <p class="mb-6 text-[#c6cde0]">
            Вы уверены, что хотите удалить файл <span class="font-semibold text-white">{{ deleteFileName }}</span>?
          </p>
          <div class="flex gap-3 justify-end">
            <button
              @click="closeDeleteFileModal"
              :disabled="deleteFileLoading"
              class="px-4 py-2 bg-[#343434] hover:bg-[#444444] disabled:bg-[#343434] disabled:cursor-not-allowed rounded-lg transition-colors text-[#c6cde0]"
            >
              Отмена
            </button>
            <button
              @click="confirmDeleteFile"
              :disabled="deleteFileLoading"
              class="px-4 py-2 bg-[#9F2727] hover:bg-[#C22D2D] disabled:bg-[#6a1a1a] disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2 justify-center"
            >
              <span v-if="deleteFileLoading" class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              {{ deleteFileLoading ? 'Удаление...' : 'Удалить' }}
            </button>
          </div>
        </div>
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

const yaraFiles = ref([])
const selectedYaraFile = ref('')
const yaraEditorContent = ref('')
const yaraSaving = ref(false)
const yaraDeleting = ref(false)

// Модальное окно для создания файла
const showCreateFileModal = ref(false)
const createFileInput = ref('')
const createFileType = ref('')
const createFileLoading = ref(false)

// Модальное окно для удаления файла
const showDeleteFileModal = ref(false)
const deleteFileName = ref('')
const deleteFileType = ref('')
const deleteFileLoading = ref(false)

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

const closeCreateFileModal = () => {
  if (createFileLoading.value) return
  showCreateFileModal.value = false
  createFileInput.value = ''
  createFileType.value = ''
}

const closeDeleteFileModal = () => {
  if (deleteFileLoading.value) return
  showDeleteFileModal.value = false
  deleteFileName.value = ''
  deleteFileType.value = ''
}

const createSigmaFile = () => {
  createFileType.value = 'sigma'
  createFileInput.value = ''
  showCreateFileModal.value = true
}

const confirmCreateFile = async () => {
  const fileName = createFileInput.value.trim()
  if (!fileName || createFileLoading.value) {
    return
  }

  createFileLoading.value = true
  try {
    if (createFileType.value === 'sigma') {
      await configRules.createSigmaFile(fileName)
      await loadSigmaFiles()
      await selectSigmaFile(fileName)
    } else if (createFileType.value === 'yara') {
      await configRules.createYaraFile(fileName)
      await loadYaraFiles()
      await selectYaraFile(fileName)
    }
    appStore.addNotification('Новый файл успешно создан', 'success')
  } catch (error) {
    console.error(`Ошибка создания файла:`, error)
    const fileType = createFileType.value === 'sigma' ? 'Sigma' : 'Yara'
    const message = error?.response?.data?.detail || `Ошибка создания ${fileType} файла`
    appStore.addNotification(message, 'error')
  } finally {
    createFileLoading.value = false
    showCreateFileModal.value = false
    createFileInput.value = ''
    createFileType.value = ''
  }
}

const saveSigmaFile = async () => {
  if (!selectedSigmaFile.value) {
    return
  }

  sigmaSaving.value = true
  try {
    await configRules.saveSigmaFile(selectedSigmaFile.value, sigmaEditorContent.value)
    appStore.addNotification('Файл успешно сохранен', 'success')
  } catch (error) {
    console.error('Ошибка сохранения Sigma файла:', error)
    const message = error?.response?.data?.detail || 'Ошибка сохранения Sigma файла'
    appStore.addNotification(message, 'error')
  } finally {
    sigmaSaving.value = false
  }
}

const showDeleteSigmaFileModal = () => {
  if (!selectedSigmaFile.value) {
    return
  }
  deleteFileType.value = 'sigma'
  deleteFileName.value = selectedSigmaFile.value
  showDeleteFileModal.value = true
}

const showDeleteYaraFileModal = () => {
  if (!selectedYaraFile.value) {
    return
  }
  deleteFileType.value = 'yara'
  deleteFileName.value = selectedYaraFile.value
  showDeleteFileModal.value = true
}

const confirmDeleteFile = async () => {
  if (!deleteFileName.value || deleteFileLoading.value) {
    return
  }

  deleteFileLoading.value = true
  try {
    if (deleteFileType.value === 'sigma') {
      await configRules.deleteSigmaFile(deleteFileName.value)
      const oldFiles = [...sigmaFiles.value]
      await loadSigmaFiles()

      const remainingFiles = sigmaFiles.value.filter((name) => name !== deleteFileName.value)
      if (!remainingFiles.includes(selectedSigmaFile.value)) {
        const oldIndex = oldFiles.indexOf(deleteFileName.value)
        const nextFile = remainingFiles[Math.min(oldIndex, remainingFiles.length - 1)]
        if (nextFile) {
          await selectSigmaFile(nextFile)
        } else {
          selectedSigmaFile.value = ''
          sigmaEditorContent.value = ''
        }
      }
    } else if (deleteFileType.value === 'yara') {
      await configRules.deleteYaraFile(deleteFileName.value)
      const oldFiles = [...yaraFiles.value]
      await loadYaraFiles()

      const remainingFiles = yaraFiles.value.filter((name) => name !== deleteFileName.value)
      if (!remainingFiles.includes(selectedYaraFile.value)) {
        const oldIndex = oldFiles.indexOf(deleteFileName.value)
        const nextFile = remainingFiles[Math.min(oldIndex, remainingFiles.length - 1)]
        if (nextFile) {
          await selectYaraFile(nextFile)
        } else {
          selectedYaraFile.value = ''
          yaraEditorContent.value = ''
        }
      }
    }
    appStore.addNotification('Файл успешно удален', 'success')
  } catch (error) {
    console.error('Ошибка удаления файла:', error)
    const fileType = deleteFileType.value === 'sigma' ? 'Sigma' : 'Yara'
    const message = error?.response?.data?.detail || `Ошибка удаления ${fileType} файла`
    appStore.addNotification(message, 'error')
  } finally {
    deleteFileLoading.value = false
    closeDeleteFileModal()
  }
}

const deleteSigmaFile = () => {
  showDeleteSigmaFileModal()
}

const loadYaraFiles = async () => {
  try {
    const response = await configRules.listYaraFiles()
    yaraFiles.value = response.data.files || []
    if (!selectedYaraFile.value && yaraFiles.value.length > 0) {
      await selectYaraFile(yaraFiles.value[0])
    }
  } catch (error) {
    console.error('Ошибка загрузки Yara файлов:', error)
    appStore.addNotification('Ошибка загрузки Yara файлов', 'error')
  }
}

const selectYaraFile = async (fileName) => {
  selectedYaraFile.value = fileName
  try {
    const response = await configRules.getYaraFile(fileName)
    yaraEditorContent.value = response.data.content || ''
  } catch (error) {
    console.error('Ошибка чтения Yara файла:', error)
    appStore.addNotification('Ошибка чтения Yara файла', 'error')
  }
}

const createYaraFile = () => {
  createFileType.value = 'yara'
  createFileInput.value = ''
  showCreateFileModal.value = true
}

const saveYaraFile = async () => {
  if (!selectedYaraFile.value) {
    return
  }

  yaraSaving.value = true
  try {
    await configRules.saveYaraFile(selectedYaraFile.value, yaraEditorContent.value)
    appStore.addNotification('Файл успешно сохранен', 'success')
  } catch (error) {
    console.error('Ошибка сохранения Yara файла:', error)
    const message = error?.response?.data?.detail || 'Ошибка сохранения Yara файла'
    appStore.addNotification(message, 'error')
  } finally {
    yaraSaving.value = false
  }
}

const deleteYaraFile = () => {
  showDeleteYaraFileModal()
}

onMounted(async () => {
  await Promise.all([loadSigmaFiles(), loadYaraFiles()])
})
</script>
