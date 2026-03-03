<template>
  <div>
    <!-- Toolbar -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建流水线
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="pipelines" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="repo_url" label="仓库地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="branch" label="分支" width="100" />
        <el-table-column prop="trigger_type" label="触发方式" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.trigger_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="engine" label="引擎" width="100">
          <template #default="{ row }">
            <el-tag :type="row.engine === 'jenkins' ? 'primary' : 'success'" effect="plain" size="small">
              {{ row.engine === 'jenkins' ? 'Jenkins' : '本地' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="激活" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="handleTrigger(row)">
              触发
            </el-button>
            <el-button size="small" @click="goBuilds(row.id)">
              构建历史
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
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

    <!-- Build History Dialog -->
    <el-dialog v-model="buildsDialogVisible" title="构建历史" width="800px" destroy-on-close>
      <el-table :data="builds" v-loading="buildsLoading" style="width: 100%;" border>
        <el-table-column prop="id" label="Build ID" width="80" />
        <el-table-column prop="build_no" label="构建号" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="buildStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="triggered_by" label="触发人" width="100" />
        <el-table-column prop="created_at" label="触发时间" width="160" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" @click="goBuildLog(row.id)">日志</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="buildPage"
          v-model:page-size="buildPageSize"
          :total="buildTotal"
          layout="total, prev, pager, next"
          @change="loadBuilds"
        />
      </div>
    </el-dialog>

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="新建流水线" width="600px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="流水线名称" />
        </el-form-item>
        <el-form-item label="执行引擎" prop="engine">
          <el-radio-group v-model="form.engine">
            <el-radio label="local">本地轻量级</el-radio>
            <el-radio label="jenkins">Jenkins</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <template v-if="form.engine === 'local'">
          <el-form-item label="仓库地址" prop="repo_url">
            <el-input v-model="form.repo_url" placeholder="https://github.com/..." />
          </el-form-item>
          <el-form-item label="分支" prop="branch">
            <el-input v-model="form.branch" placeholder="main" />
          </el-form-item>
          <el-form-item label="触发方式" prop="trigger_type">
            <el-select v-model="form.trigger_type" style="width: 100%;">
              <el-option label="手动" value="manual" />
              <el-option label="定时" value="schedule" />
              <el-option label="Webhook" value="webhook" />
            </el-select>
          </el-form-item>
          <el-form-item label="配置文件" prop="config_yaml">
            <el-input
              v-model="form.config_yaml"
              type="textarea"
              :rows="8"
              placeholder="粘贴 YAML 格式的流水线配置..."
              style="font-family: monospace;"
            />
          </el-form-item>
        </template>
        
        <template v-else>
          <el-form-item label="Jenkins Job" prop="jenkins_job">
            <el-input v-model="form.jenkins_job" placeholder="Jenkins Job 名称" />
          </el-form-item>
          <el-alert title="触发时将调用全局配置的 Jenkins 服务" type="info" :closable="false" style="margin-bottom: 16px;" />
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getPipelines, createPipeline, deletePipeline, triggerPipeline, getBuilds } from '@/api/cicd'

const router = useRouter()

const pipelines = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

// Build history
const buildsDialogVisible = ref(false)
const builds = ref<any[]>([])
const buildsLoading = ref(false)
const buildTotal = ref(0)
const buildPage = ref(1)
const buildPageSize = ref(10)
const currentPipelineId = ref<number | null>(null)

const form = reactive({
  name: '',
  engine: 'local',
  jenkins_job: '',
  repo_url: '',
  branch: 'main',
  trigger_type: 'manual',
  config_yaml: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  repo_url: [{ required: true, message: '请输入仓库地址', trigger: 'blur' }],
  branch: [{ required: true, message: '请输入分支', trigger: 'blur' }],
  jenkins_job: [{ required: true, message: '请输入 Jenkins Job 名称', trigger: 'blur' }],
}

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

async function loadData() {
  loading.value = true
  try {
    const data = await getPipelines(page.value, pageSize.value)
    if (Array.isArray(data)) {
      pipelines.value = data
      total.value = data.length
    } else {
      pipelines.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载流水线列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, { 
    name: '', 
    engine: 'local',
    jenkins_job: '',
    repo_url: '', 
    branch: 'main', 
    trigger_type: 'manual', 
    config_yaml: '' 
  })
  dialogVisible.value = true
}

async function handleCreate() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createPipeline({ ...form })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除流水线 "${row.name}"？`, '确认删除', { type: 'warning' })
    await deletePipeline(row.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err?.response?.data?.detail || '删除失败')
    }
  }
}

async function handleTrigger(row: any) {
  try {
    const build = await triggerPipeline(row.id)
    ElMessage.success(`构建已触发，Build ID: ${build.id || build.build_no || ''}`)
    goBuilds(row.id)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '触发失败')
  }
}

function goBuilds(pipelineId: number) {
  currentPipelineId.value = pipelineId
  buildPage.value = 1
  buildsDialogVisible.value = true
  loadBuilds()
}

async function loadBuilds() {
  if (!currentPipelineId.value) return
  buildsLoading.value = true
  try {
    const data = await getBuilds(currentPipelineId.value, buildPage.value, buildPageSize.value)
    if (Array.isArray(data)) {
      builds.value = data
      buildTotal.value = data.length
    } else {
      builds.value = data.items || data.data || []
      buildTotal.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载构建历史失败')
  } finally {
    buildsLoading.value = false
  }
}

function goBuildLog(buildId: number) {
  router.push(`/cicd/builds/${buildId}/log`)
}

onMounted(loadData)
</script>
