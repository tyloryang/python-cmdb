<template>
  <div>
    <el-row :gutter="16">
      <!-- Left: Watcher list -->
      <el-col :span="16">
        <!-- Toolbar -->
        <el-card shadow="never" style="margin-bottom: 16px;">
          <div style="display: flex; gap: 12px; align-items: center;">
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新建监控任务
            </el-button>
          </div>
        </el-card>

        <!-- Table -->
        <el-card shadow="never">
          <el-table :data="watchers" v-loading="loading" style="width: 100%;" border>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="任务名称" min-width="140" />
            <el-table-column prop="log_path" label="日志路径" min-width="180" show-overflow-tooltip />
            <el-table-column prop="source_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small">{{ row.source_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="130">
              <template #default="{ row }">
                <div style="display: flex; align-items: center; gap: 6px;">
                  <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
                  <el-button
                    v-if="row.status !== 'running'"
                    size="small"
                    type="success"
                    circle
                    @click="handleStart(row)"
                    title="启动"
                  >
                    <el-icon><VideoPlay /></el-icon>
                  </el-button>
                  <el-button
                    v-else
                    size="small"
                    type="warning"
                    circle
                    @click="handlePause(row)"
                    title="暂停"
                  >
                    <el-icon><VideoPause /></el-icon>
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="last_run_at" label="最后执行" width="160">
              <template #default="{ row }">{{ row.last_run_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="handleRun(row)" title="立即执行">
                  <el-icon><CaretRight /></el-icon>
                </el-button>
                <el-button size="small" @click="goTemplates(row.id)">模板</el-button>
                <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @change="loadData"
            />
          </div>
        </el-card>
      </el-col>

      <!-- Right: Live events stream -->
      <el-col :span="8">
        <el-card shadow="never" style="height: calc(100vh - 160px);">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span>实时聚合事件</span>
              <el-tag :type="wsConnected ? 'success' : 'info'" size="small">
                {{ wsConnected ? 'LIVE' : '未连接' }}
              </el-tag>
            </div>
          </template>
          <div ref="liveContainer" class="live-stream">
            <div v-for="(evt, idx) in liveEvents" :key="idx" class="live-event">
              <span class="live-time">{{ evt.time }}</span>
              <span class="live-msg">{{ evt.message }}</span>
            </div>
            <div v-if="liveEvents.length === 0" style="color: #999; text-align: center; padding: 40px 0;">
              等待实时事件...
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="新建监控任务" width="580px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="130px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="日志路径" prop="log_path">
          <el-input v-model="form.log_path" placeholder="/var/log/app/*.log" />
        </el-form-item>
        <el-form-item label="来源类型" prop="source_type">
          <el-select v-model="form.source_type" style="width: 100%;">
            <el-option label="本地文件" value="local" />
            <el-option label="远程SSH" value="ssh" />
            <el-option label="Kubernetes" value="k8s" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务器ID" prop="server_id">
          <el-input-number v-model="form.server_id" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="Drain深度" prop="drain_depth">
          <el-input-number v-model="form.drain_depth" :min="3" :max="10" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="相似度阈值" prop="drain_sim_th">
          <el-slider v-model="form.drain_sim_th" :min="0.1" :max="1" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="日志格式正则" prop="log_format_regex">
          <el-input
            v-model="form.log_format_regex"
            type="textarea"
            :rows="3"
            placeholder="可选，如: (?P<time>\S+) (?P<level>\S+) (?P<message>.*)"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  getWatchers,
  createWatcher,
  deleteWatcher,
  startWatcher,
  pauseWatcher,
  runWatcher,
} from '@/api/logAnalysis'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const watchers = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

// Live stream
const wsConnected = ref(false)
const liveEvents = ref<{ time: string; message: string }[]>([])
const liveContainer = ref<HTMLElement | null>(null)
let ws: WebSocket | null = null
let currentWatcherId: number | null = null

const form = reactive({
  name: '',
  log_path: '',
  source_type: 'local',
  server_id: 1,
  drain_depth: 4,
  drain_sim_th: 0.5,
  log_format_regex: '',
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  log_path: [{ required: true, message: '请输入日志路径', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择来源类型', trigger: 'change' }],
}

function statusTagType(status: string) {
  const map: Record<string, string> = {
    running: 'success',
    paused: 'warning',
    stopped: 'info',
    error: 'danger',
  }
  return map[status] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const data = await getWatchers(page.value, pageSize.value)
    if (Array.isArray(data)) {
      watchers.value = data
      total.value = data.length
    } else {
      watchers.value = data.items || data.data || []
      total.value = data.total || 0
    }
    // Connect live ws for the first watcher if available
    if (watchers.value.length > 0 && !ws) {
      connectLiveWs(watchers.value[0].id)
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载监控任务失败')
  } finally {
    loading.value = false
  }
}

function connectLiveWs(watcherId: number) {
  if (ws) {
    ws.close()
    ws = null
  }
  currentWatcherId = watcherId
  const wsBase = import.meta.env.VITE_WS_BASE
  const token = authStore.token
  ws = new WebSocket(
    `${wsBase}/api/v1/log-analysis/watchers/${watcherId}/live?token=${encodeURIComponent(token)}`
  )

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      const time = new Date().toLocaleTimeString()
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      liveEvents.value.push({ time, message })
      if (liveEvents.value.length > 100) {
        liveEvents.value = liveEvents.value.slice(-100)
      }
      nextTick(() => {
        if (liveContainer.value) {
          liveContainer.value.scrollTop = liveContainer.value.scrollHeight
        }
      })
    } catch {
      // ignore
    }
  }

  ws.onerror = () => {
    wsConnected.value = false
  }

  ws.onclose = () => {
    wsConnected.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, {
    name: '',
    log_path: '',
    source_type: 'local',
    server_id: 1,
    drain_depth: 4,
    drain_sim_th: 0.5,
    log_format_regex: '',
  })
  dialogVisible.value = true
}

async function handleCreate() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createWatcher({ ...form })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function handleStart(row: any) {
  try {
    await startWatcher(row.id)
    ElMessage.success('已启动')
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '启动失败')
  }
}

async function handlePause(row: any) {
  try {
    await pauseWatcher(row.id)
    ElMessage.success('已暂停')
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '暂停失败')
  }
}

async function handleRun(row: any) {
  try {
    await runWatcher(row.id)
    ElMessage.success('已立即执行')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '执行失败')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除监控任务 "${row.name}"？`, '确认删除', { type: 'warning' })
    await deleteWatcher(row.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err?.response?.data?.detail || '删除失败')
    }
  }
}

function goTemplates(watcherId: number) {
  router.push(`/log-analysis/watchers/${watcherId}/templates`)
}

onMounted(loadData)

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style scoped>
.live-stream {
  height: calc(100vh - 260px);
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
}

.live-event {
  display: flex;
  gap: 8px;
  padding: 3px 0;
  border-bottom: 1px solid #f0f0f0;
  word-break: break-all;
}

.live-time {
  color: #999;
  flex-shrink: 0;
}

.live-msg {
  color: #333;
}
</style>
