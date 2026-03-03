<template>
  <div class="dashboard">
    <!-- Summary Cards -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="4" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: card.gradient }">
              <el-icon :size="26" style="color: #fff;"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>服务器状态</span>
              <el-tag size="small" type="info">{{ summary.counts?.servers || 0 }} 台</el-tag>
            </div>
          </template>
          <v-chart :option="serverStatusOption" autoresize style="height: 240px;" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>操作系统分布</span>
            </div>
          </template>
          <v-chart :option="osDistOption" autoresize style="height: 240px;" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>构建状态</span>
              <el-tag size="small" type="info">{{ summary.counts?.builds || 0 }} 次</el-tag>
            </div>
          </template>
          <v-chart :option="buildStatusOption" autoresize style="height: 240px;" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Build Trend + Tables -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>近7天构建趋势</span>
            </div>
          </template>
          <v-chart :option="buildTrendOption" autoresize style="height: 280px;" />
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-row :gutter="20">
          <el-col :span="24" style="margin-bottom: 20px;">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>最近告警</span>
                  <el-button size="small" text type="primary" @click="$router.push('/monitor/events')">查看全部</el-button>
                </div>
              </template>
              <el-table :data="summary.recent_alerts || []" size="small" style="width: 100%;">
                <el-table-column prop="rule_id" label="规则" width="60" />
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'firing' ? 'danger' : 'success'" size="small">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="metric_value" label="指标值" width="80" />
                <el-table-column prop="fired_at" label="触发时间" show-overflow-tooltip />
              </el-table>
              <div v-if="!summary.recent_alerts?.length" class="empty-tip">暂无告警</div>
            </el-card>
          </el-col>
          <el-col :span="24">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>最近构建</span>
                  <el-button size="small" text type="primary" @click="$router.push('/cicd/pipelines')">查看全部</el-button>
                </div>
              </template>
              <el-table :data="summary.recent_builds || []" size="small" style="width: 100%;">
                <el-table-column prop="build_no" label="构建号" width="80" />
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="buildStatusType(row.status)" size="small">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="pipeline_id" label="流水线" width="80" />
                <el-table-column prop="created_at" label="创建时间" show-overflow-tooltip />
              </el-table>
              <div v-if="!summary.recent_builds?.length" class="empty-tip">暂无构建记录</div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDashboardSummary } from '@/api/dashboard'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([PieChart, BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const summary = ref<any>({})

const statCards = computed(() => [
  {
    label: '服务器',
    value: summary.value.counts?.servers ?? 0,
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    icon: 'Monitor',
  },
  {
    label: '流水线',
    value: summary.value.counts?.pipelines ?? 0,
    gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    icon: 'Connection',
  },
  {
    label: '构建',
    value: summary.value.counts?.builds ?? 0,
    gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    icon: 'Cpu',
  },
  {
    label: '发布单',
    value: summary.value.counts?.releases ?? 0,
    gradient: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
    icon: 'Promotion',
  },
  {
    label: '活跃告警',
    value: summary.value.counts?.alert_firing ?? 0,
    gradient: 'linear-gradient(135deg, #f5576c 0%, #ff6a00 100%)',
    icon: 'Bell',
  },
  {
    label: '日志监控',
    value: summary.value.counts?.watchers ?? 0,
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    icon: 'Document',
  },
])

const statusColors: Record<string, string> = {
  running: '#67C23A',
  stopped: '#909399',
  maintenance: '#E6A23C',
  decommissioned: '#F56C6C',
}

const serverStatusOption = computed(() => {
  const data = Object.entries(summary.value.server_status || {}).map(([name, value]) => ({
    name,
    value,
    itemStyle: { color: statusColors[name] || '#409EFF' },
  }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data,
    }],
  }
})

const osDistOption = computed(() => {
  const data = Object.entries(summary.value.os_distribution || {}).map(([name, value]) => ({
    name,
    value,
  }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272'],
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data,
    }],
  }
})

const buildStatusColors: Record<string, string> = {
  success: '#67C23A',
  failed: '#F56C6C',
  running: '#E6A23C',
  pending: '#909399',
  cancelled: '#C0C4CC',
}

const buildStatusOption = computed(() => {
  const data = Object.entries(summary.value.build_status || {}).map(([name, value]) => ({
    name,
    value,
    itemStyle: { color: buildStatusColors[name] || '#409EFF' },
  }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data,
    }],
  }
})

const buildTrendOption = computed(() => {
  const trend = summary.value.build_trend || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '8%', right: '5%', bottom: '12%', top: '10%' },
    xAxis: {
      type: 'category',
      data: trend.map((t: any) => t.date),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: trend.map((t: any) => t.count),
      barWidth: '40%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' },
          ],
        },
      },
    }],
  }
})

function buildStatusType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  const map: Record<string, 'success' | 'danger' | 'warning' | 'info'> = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'info',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

onMounted(async () => {
  try {
    summary.value = await getDashboardSummary()
  } catch (err: any) {
    ElMessage.error('加载仪表盘数据失败')
    console.error(err)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 4px;
}

.stat-card {
  cursor: default;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.chart-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.empty-tip {
  text-align: center;
  color: #c0c4cc;
  padding: 20px 0;
  font-size: 13px;
}
</style>
