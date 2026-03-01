<template>
  <div>
    <!-- Header -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
        <el-button @click="router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <span style="font-size: 16px; font-weight: 500;">
          日志模板列表 (Watcher #{{ watcherId }})
        </span>
        <div style="margin-left: auto; display: flex; align-items: center; gap: 16px;">
          <el-button type="primary" @click="askDialogVisible = true">
            <el-icon style="margin-right: 6px;"><ChatDotRound /></el-icon> AI 智能问答
          </el-button>
          
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 13px; color: #666;">排序:</span>
            <el-radio-group v-model="orderBy" @change="loadData">
              <el-radio-button label="hit_count">命中次数</el-radio-button>
              <el-radio-button label="last_seen_at">最后时间</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table
        :data="templates"
        v-loading="loading"
        style="width: 100%;"
        border
        row-key="cluster_id"
        @expand-change="handleExpand"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 12px 40px; background: #f5f7fa;">
              <div style="font-weight: 500; margin-bottom: 8px; color: #666;">样例日志:</div>
              <pre
                v-for="(log, idx) in row.sample_logs || []"
                :key="idx"
                style="margin: 4px 0; font-size: 12px; color: #333; background: #fff; padding: 6px; border-radius: 4px; border: 1px solid #e8e8e8; word-break: break-all; white-space: pre-wrap;"
              >{{ log }}</pre>
              <div v-if="!row.sample_logs || row.sample_logs.length === 0" style="color: #999;">
                暂无样例日志
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="cluster_id" label="Cluster ID" width="100" />
        <el-table-column prop="template_str" label="模板" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <code style="font-size: 12px; word-break: break-all;">{{ row.template_str }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="hit_count" label="命中次数" width="180">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-progress
                :percentage="maxHits > 0 ? Math.round((row.hit_count / maxHits) * 100) : 0"
                :stroke-width="10"
                style="flex: 1;"
                :format="() => ''"
              />
              <span style="font-size: 12px; color: #333; min-width: 40px; text-align: right;">
                {{ row.hit_count }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="last_seen_at" label="最后时间" width="160">
          <template #default="{ row }">{{ row.last_seen_at || '-' }}</template>
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

    <!-- AI Ask Dialog -->
    <el-dialog v-model="askDialogVisible" title="AI 智能日志助手" width="600px" destroy-on-close>
      <div style="margin-bottom: 20px;">
        <div style="margin-bottom: 8px; font-weight: 500;">分析时间范围（最近几小时）：</div>
        <el-input-number v-model="askHours" :min="1" :max="720" style="width: 150px; margin-bottom: 16px;" />
        
        <div style="margin-bottom: 8px; font-weight: 500;">您的问题：</div>
        <el-input 
          v-model="askQuestion" 
          type="textarea" 
          :rows="3" 
          placeholder="例如：最近几小时是否有 timeout 或 out_of_memory 的日志？"
        />
      </div>

      <div v-if="askAnswer" style="padding: 16px; background-color: #f6f8fa; border-radius: 8px; border: 1px solid #dcdfe6; position: relative;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #409eff;">
          <el-icon style="margin-right: 4px;"><Cpu /></el-icon> AI 回复：
        </div>
        <div style="white-space: pre-wrap; line-height: 1.6; color: #333;">{{ askAnswer }}</div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="askDialogVisible = false">关闭</el-button>
          <el-button type="primary" :loading="asking" @click="handleAsk">
            发送询问
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ChatDotRound, Cpu } from '@element-plus/icons-vue'
import { getTemplates, askLogs } from '@/api/logAnalysis'

const route = useRoute()
const router = useRouter()

const watcherId = route.params.watcherId as string

const templates = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const orderBy = ref('hit_count')

// AI Query state
const askDialogVisible = ref(false)
const askQuestion = ref('')
const askHours = ref(24)
const asking = ref(false)
const askAnswer = ref('')

const maxHits = computed(() => {
  if (templates.value.length === 0) return 0
  return Math.max(...templates.value.map((t: any) => t.hit_count || 0))
})

async function loadData() {
  loading.value = true
  try {
    const data = await getTemplates(parseInt(watcherId), page.value, pageSize.value, orderBy.value)
    if (Array.isArray(data)) {
      templates.value = data
      total.value = data.length
    } else {
      templates.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载模板列表失败')
  } finally {
    loading.value = false
  }
}

async function handleAsk() {
  if (!askQuestion.value.trim()) {
    ElMessage.warning('请输入您的问题')
    return
  }
  asking.value = true
  askAnswer.value = ''
  try {
    const res = await askLogs(parseInt(watcherId), askQuestion.value, askHours.value)
    askAnswer.value = res.answer
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || 'AI服务出错请求失败')
    askAnswer.value = '请求失败：' + (err?.message || '未知错误')
  } finally {
    asking.value = false
  }
}

function handleExpand(_row: any, _expandedRows: any[]) {
  // Row expand is handled by el-table automatically
}

onMounted(loadData)
</script>
