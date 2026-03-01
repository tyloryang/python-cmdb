<template>
  <div>
    <!-- Toolbar -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button type="primary" @click="openCreateDialog(null)">
          <el-icon><Plus /></el-icon> 新建告警规则
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="rules" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column prop="target_type" label="目标类型" width="100" />
        <el-table-column prop="metric" label="指标" width="120" />
        <el-table-column prop="condition" label="条件" width="80" />
        <el-table-column prop="threshold" label="阈值" width="80" />
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="激活" width="70">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="handleToggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openCreateDialog(row)">编辑</el-button>
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

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingRule ? '编辑告警规则' : '新建告警规则'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="告警规则名称" />
        </el-form-item>
        <el-form-item label="目标类型" prop="target_type">
          <el-select v-model="form.target_type" style="width: 100%;">
            <el-option label="主机" value="host" />
            <el-option label="服务" value="service" />
            <el-option label="数据库" value="database" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标ID" prop="target_id">
          <el-input-number v-model="form.target_id" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="指标" prop="metric">
          <el-select v-model="form.metric" style="width: 100%;" filterable allow-create>
            <el-option label="CPU使用率" value="cpu_usage" />
            <el-option label="内存使用率" value="memory_usage" />
            <el-option label="磁盘使用率" value="disk_usage" />
            <el-option label="网络入流量" value="net_in" />
            <el-option label="网络出流量" value="net_out" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件" prop="condition">
          <el-select v-model="form.condition" style="width: 100%;">
            <el-option label="大于 >" value="gt" />
            <el-option label="小于 <" value="lt" />
            <el-option label="大于等于 >=" value="gte" />
            <el-option label="小于等于 <=" value="lte" />
            <el-option label="等于 ==" value="eq" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值" prop="threshold">
          <el-input-number v-model="form.threshold" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="持续时间(s)" prop="duration">
          <el-input-number v-model="form.duration" :min="0" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="严重程度" prop="severity">
          <el-select v-model="form.severity" style="width: 100%;">
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="critical" />
            <el-option label="紧急" value="emergency" />
          </el-select>
        </el-form-item>
        <el-form-item label="激活">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingRule ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getAlertRules, createAlertRule, updateAlertRule, deleteAlertRule } from '@/api/monitor'

const rules = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const editingRule = ref<any>(null)

const form = reactive({
  name: '',
  target_type: 'host',
  target_id: 1,
  metric: '',
  condition: 'gt',
  threshold: 80,
  duration: 60,
  severity: 'warning',
  is_active: true,
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  metric: [{ required: true, message: '请选择指标', trigger: 'change' }],
  condition: [{ required: true, message: '请选择条件', trigger: 'change' }],
  severity: [{ required: true, message: '请选择严重程度', trigger: 'change' }],
}

function severityType(severity: string) {
  const map: Record<string, string> = {
    info: 'info',
    warning: 'warning',
    critical: 'danger',
    emergency: 'danger',
  }
  return map[severity] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const data = await getAlertRules(page.value, pageSize.value)
    if (Array.isArray(data)) {
      rules.value = data
      total.value = data.length
    } else {
      rules.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载告警规则失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog(rule: any) {
  editingRule.value = rule
  if (rule) {
    Object.assign(form, {
      name: rule.name,
      target_type: rule.target_type,
      target_id: rule.target_id,
      metric: rule.metric,
      condition: rule.condition,
      threshold: rule.threshold,
      duration: rule.duration,
      severity: rule.severity,
      is_active: rule.is_active,
    })
  } else {
    Object.assign(form, {
      name: '',
      target_type: 'host',
      target_id: 1,
      metric: '',
      condition: 'gt',
      threshold: 80,
      duration: 60,
      severity: 'warning',
      is_active: true,
    })
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingRule.value) {
      await updateAlertRule(editingRule.value.id, { ...form })
      ElMessage.success('更新成功')
    } else {
      await createAlertRule({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleToggleActive(row: any) {
  try {
    await updateAlertRule(row.id, { is_active: row.is_active })
    ElMessage.success(`规则已${row.is_active ? '激活' : '停用'}`)
  } catch (err: any) {
    row.is_active = !row.is_active
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除告警规则 "${row.name}"？`, '确认删除', { type: 'warning' })
    await deleteAlertRule(row.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err?.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(loadData)
</script>
