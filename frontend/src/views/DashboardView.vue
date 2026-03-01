<template>
  <div>
    <el-row :gutter="24" style="margin-bottom: 24px;">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: card.color }">
              <el-icon :size="28" style="color: #fff;"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="24">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>最近告警事件</span>
          </template>
          <el-table :data="recentAlerts" style="width: 100%;" size="small">
            <el-table-column prop="rule_id" label="规则ID" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'firing' ? 'danger' : 'success'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="metric_value" label="指标值" />
            <el-table-column prop="fired_at" label="触发时间" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>最近构建</span>
          </template>
          <el-table :data="recentBuilds" style="width: 100%;" size="small">
            <el-table-column prop="build_no" label="构建号" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="buildStatusType(row.status)" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="pipeline_id" label="流水线ID" />
            <el-table-column prop="created_at" label="时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getServers } from '@/api/cmdb'
import { getPipelines } from '@/api/cicd'
import { getReleases } from '@/api/release'
import { getAlertEvents } from '@/api/monitor'
import { ElMessage } from 'element-plus'

const serverCount = ref(0)
const pipelineCount = ref(0)
const releaseCount = ref(0)
const alertCount = ref(0)
const recentAlerts = ref<any[]>([])
const recentBuilds = ref<any[]>([])

const statCards = ref([
  { label: '服务器', value: serverCount, color: '#1890ff', icon: 'Monitor' },
  { label: '流水线', value: pipelineCount, color: '#52c41a', icon: 'Connection' },
  { label: '发布单', value: releaseCount, color: '#fa8c16', icon: 'Promotion' },
  { label: '活跃告警', value: alertCount, color: '#f5222d', icon: 'Bell' },
])

function buildStatusType(status: string) {
  const map: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'info',
  }
  return map[status] || 'info'
}

onMounted(async () => {
  try {
    const [servers, pipelines, releases, alerts] = await Promise.allSettled([
      getServers(1, 1),
      getPipelines(1, 1),
      getReleases(1, 1),
      getAlertEvents('firing', 1, 5),
    ])

    if (servers.status === 'fulfilled') {
      const d = servers.value
      serverCount.value = d.total ?? (Array.isArray(d) ? d.length : 0)
    }
    if (pipelines.status === 'fulfilled') {
      const d = pipelines.value
      pipelineCount.value = d.total ?? (Array.isArray(d) ? d.length : 0)
    }
    if (releases.status === 'fulfilled') {
      const d = releases.value
      releaseCount.value = d.total ?? (Array.isArray(d) ? d.length : 0)
    }
    if (alerts.status === 'fulfilled') {
      const d = alerts.value
      alertCount.value = d.total ?? (Array.isArray(d) ? d.length : 0)
      recentAlerts.value = Array.isArray(d) ? d.slice(0, 5) : (d.items || d.data || []).slice(0, 5)
    }
  } catch (err) {
    ElMessage.error('加载仪表盘数据失败')
  }
})
</script>

<style scoped>
.stat-card {
  cursor: default;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #333;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 6px;
}
</style>
