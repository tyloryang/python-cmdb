<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
        <el-button @click="router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 16px; font-weight: 500;">Build #{{ buildInfo?.build_no || buildId }}</span>
          <el-tag :type="buildStatusType(buildInfo?.status)" size="large">
            {{ buildInfo?.status || 'loading...' }}
          </el-tag>
        </div>
        <div v-if="buildInfo" style="color: #666; font-size: 13px;">
          <span>流水线ID: {{ buildInfo.pipeline_id }}</span>
          <el-divider direction="vertical" />
          <span>触发人: {{ buildInfo.triggered_by || '-' }}</span>
          <el-divider direction="vertical" />
          <span>开始时间: {{ buildInfo.created_at || '-' }}</span>
          <el-divider direction="vertical" />
          <span>耗时: {{ duration }}</span>
        </div>
        <div style="margin-left: auto; display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 12px; color: #999;">连接状态:</span>
          <el-tag :type="wsConnected ? 'success' : 'danger'" size="small">
            {{ wsConnected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span>构建日志</span>
          <el-checkbox v-model="autoScroll">自动滚动</el-checkbox>
        </div>
      </template>
      <div ref="logContainer" class="log-container">
        <pre class="log-content">{{ logContent }}</pre>
        <div v-if="!logContent && !wsConnected" style="color: #999; text-align: center; padding: 40px;">
          暂无日志
        </div>
        <div v-if="!wsConnected && logContent" style="color: #f5222d; margin-top: 8px; font-size: 12px;">
          [连接已断开]
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getBuild } from '@/api/cicd'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const buildId = route.params.buildId as string
const buildInfo = ref<any>(null)
const logContent = ref('')
const wsConnected = ref(false)
const autoScroll = ref(true)
const logContainer = ref<HTMLElement | null>(null)
let ws: WebSocket | null = null

const duration = computed(() => {
  if (!buildInfo.value?.created_at) return '-'
  const start = new Date(buildInfo.value.created_at).getTime()
  const end = buildInfo.value.finished_at
    ? new Date(buildInfo.value.finished_at).getTime()
    : Date.now()
  const seconds = Math.floor((end - start) / 1000)
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
})

function buildStatusType(status: string) {
  const map: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'info',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function connectWs() {
  const wsBase = import.meta.env.VITE_WS_BASE
  const token = authStore.token
  const url = `${wsBase}/api/v1/cicd/builds/${buildId}/log?token=${encodeURIComponent(token)}`

  ws = new WebSocket(url)

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'log') {
        logContent.value += (msg.line || msg.data || '') + '\n'
      } else if (msg.type === 'output') {
        logContent.value += (msg.data || '') + '\n'
      } else if (typeof event.data === 'string') {
        logContent.value += event.data + '\n'
      }
    } catch {
      logContent.value += event.data + '\n'
    }

    if (autoScroll.value) {
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
    }
  }

  ws.onerror = () => {
    ElMessage.error('WebSocket 连接失败')
    wsConnected.value = false
  }

  ws.onclose = () => {
    wsConnected.value = false
  }
}

async function loadBuildInfo() {
  try {
    buildInfo.value = await getBuild(parseInt(buildId))
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载构建信息失败')
  }
}

onMounted(() => {
  loadBuildInfo()
  connectWs()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style scoped>
.log-container {
  background: #0d1117;
  border-radius: 4px;
  padding: 16px;
  height: 60vh;
  overflow-y: auto;
}

.log-content {
  color: #c9d1d9;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
