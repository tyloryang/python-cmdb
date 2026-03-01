<template>
  <div>
    <!-- Filter & Live Metrics -->
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="18">
        <el-card shadow="never">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 14px; color: #666;">状态筛选:</span>
            <el-radio-group v-model="statusFilter" @change="handleFilterChange">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="firing">告警中</el-radio-button>
              <el-radio-button label="resolved">已恢复</el-radio-button>
            </el-radio-group>
            <el-button @click="loadData" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" style="height: 100%;">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-size: 13px; color: #666;">实时指标</span>
            <el-tag :type="wsConnected ? 'success' : 'info'" size="small">
              {{ wsConnected ? '已连接' : '已断开' }}
            </el-tag>
          </div>
          <div v-if="latestMetric" style="margin-top: 8px; font-size: 12px; color: #333; word-break: break-all;">
            {{ JSON.stringify(latestMetric) }}
          </div>
          <div v-else style="margin-top: 8px; font-size: 12px; color: #999;">暂无实时数据</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="events" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="rule_id" label="规则ID" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'firing' ? 'danger' : 'success'" size="small">
              {{ row.status === 'firing' ? '告警中' : '已恢复' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metric_value" label="指标值" width="100" />
        <el-table-column prop="fired_at" label="触发时间" width="160" />
        <el-table-column prop="resolved_at" label="恢复时间" width="160">
          <template #default="{ row }">
            {{ row.resolved_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="notified" label="已通知" width="80">
          <template #default="{ row }">
            <el-tag :type="row.notified ? 'success' : 'info'" size="small">
              {{ row.notified ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlertEvents } from '@/api/monitor'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const events = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const wsConnected = ref(false)
const latestMetric = ref<any>(null)
let ws: WebSocket | null = null

async function loadData() {
  loading.value = true
  try {
    const data = await getAlertEvents(statusFilter.value || undefined, page.value, pageSize.value)
    if (Array.isArray(data)) {
      events.value = data
      total.value = data.length
    } else {
      events.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载告警事件失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  page.value = 1
  loadData()
}

function connectMetricsWs() {
  const wsBase = import.meta.env.VITE_WS_BASE
  const token = authStore.token
  ws = new WebSocket(`${wsBase}/api/v1/monitor/metrics/live?token=${encodeURIComponent(token)}`)

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    try {
      latestMetric.value = JSON.parse(event.data)
    } catch {
      latestMetric.value = event.data
    }
  }

  ws.onerror = () => {
    wsConnected.value = false
  }

  ws.onclose = () => {
    wsConnected.value = false
  }
}

onMounted(() => {
  loadData()
  connectMetricsWs()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>
