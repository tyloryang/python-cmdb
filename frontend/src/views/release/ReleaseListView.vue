<template>
  <div>
    <!-- Toolbar -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建发布单
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="releases" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="app_id" label="应用ID" width="80" />
        <el-table-column prop="version" label="版本号" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="releaseStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deploy_type" label="发布类型" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.deploy_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deployed_at" label="发布时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="success"
              :disabled="['deployed', 'deploying'].includes(row.status)"
              @click="handleDeploy(row)"
            >
              发布
            </el-button>
            <el-button
              size="small"
              type="warning"
              :disabled="row.status !== 'deployed'"
              @click="openRollbackDialog(row)"
            >
              回滚
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

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="新建发布单" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="应用ID" prop="app_id">
          <el-input-number v-model="form.app_id" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="版本号" prop="version">
          <el-input v-model="form.version" placeholder="e.g. v1.2.3" />
        </el-form-item>
        <el-form-item label="发布类型" prop="deploy_type">
          <el-select v-model="form.deploy_type" style="width: 100%;">
            <el-option label="蓝绿发布" value="blue_green" />
            <el-option label="滚动发布" value="rolling" />
            <el-option label="金丝雀发布" value="canary" />
            <el-option label="全量发布" value="full" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标服务器">
          <el-select
            v-model="form.target_servers"
            multiple
            placeholder="选择目标服务器（可多选）"
            style="width: 100%;"
            filterable
            allow-create
          >
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Rollback Dialog -->
    <el-dialog v-model="rollbackDialogVisible" title="回滚发布" width="440px" destroy-on-close>
      <el-form ref="rollbackFormRef" :model="rollbackForm" :rules="rollbackRules" label-width="100px">
        <el-form-item label="目标版本" prop="to_version">
          <el-input v-model="rollbackForm.to_version" placeholder="e.g. v1.2.2" />
        </el-form-item>
        <el-form-item label="回滚原因" prop="reason">
          <el-input v-model="rollbackForm.reason" type="textarea" :rows="3" placeholder="请说明回滚原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rollbackDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="rollbackSubmitting" @click="handleRollback">确认回滚</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getReleases, createRelease, deployRelease, rollbackRelease } from '@/api/release'

const releases = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const rollbackDialogVisible = ref(false)
const rollbackFormRef = ref<FormInstance>()
const rollbackSubmitting = ref(false)
const currentReleaseId = ref<number | null>(null)

const form = reactive({
  app_id: 1,
  version: '',
  deploy_type: 'rolling',
  target_servers: [] as number[],
  description: '',
})

const rollbackForm = reactive({
  to_version: '',
  reason: '',
})

const rules: FormRules = {
  app_id: [{ required: true, message: '请输入应用ID', trigger: 'blur' }],
  version: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  deploy_type: [{ required: true, message: '请选择发布类型', trigger: 'change' }],
}

const rollbackRules: FormRules = {
  to_version: [{ required: true, message: '请输入目标版本', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入回滚原因', trigger: 'blur' }],
}

function releaseStatusType(status: string) {
  const map: Record<string, string> = {
    pending: 'info',
    deploying: 'warning',
    deployed: 'success',
    failed: 'danger',
    rolled_back: 'warning',
  }
  return map[status] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const data = await getReleases(page.value, pageSize.value)
    if (Array.isArray(data)) {
      releases.value = data
      total.value = data.length
    } else {
      releases.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载发布列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, { app_id: 1, version: '', deploy_type: 'rolling', target_servers: [], description: '' })
  dialogVisible.value = true
}

async function handleCreate() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createRelease({ ...form })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function handleDeploy(row: any) {
  try {
    await ElMessageBox.confirm(`确认发布版本 ${row.version} 到生产环境？`, '确认发布', {
      type: 'warning',
      confirmButtonText: '确认发布',
    })
    await deployRelease(row.id)
    ElMessage.success('发布指令已发送')
    await loadData()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err?.response?.data?.detail || '发布失败')
    }
  }
}

function openRollbackDialog(row: any) {
  currentReleaseId.value = row.id
  Object.assign(rollbackForm, { to_version: '', reason: '' })
  rollbackDialogVisible.value = true
}

async function handleRollback() {
  if (!rollbackFormRef.value) return
  const valid = await rollbackFormRef.value.validate().catch(() => false)
  if (!valid) return

  rollbackSubmitting.value = true
  try {
    await rollbackRelease(currentReleaseId.value!, rollbackForm.to_version, rollbackForm.reason)
    ElMessage.success('回滚指令已发送')
    rollbackDialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '回滚失败')
  } finally {
    rollbackSubmitting.value = false
  }
}

onMounted(loadData)
</script>
