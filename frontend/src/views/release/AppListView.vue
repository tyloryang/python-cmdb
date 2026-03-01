<template>
  <div>
    <!-- Toolbar -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建应用
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="apps" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="应用名称" min-width="160" />
        <el-table-column prop="pipeline_id" label="流水线ID" width="100" />
        <el-table-column prop="owner_id" label="负责人ID" width="100" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="160" />
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
    <el-dialog v-model="dialogVisible" title="新建应用" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="应用名称" prop="name">
          <el-input v-model="form.name" placeholder="应用名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="应用描述" />
        </el-form-item>
        <el-form-item label="流水线ID" prop="pipeline_id">
          <el-input-number v-model="form.pipeline_id" :min="1" style="width: 100%;" />
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getApps, createApp } from '@/api/release'

const apps = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  description: '',
  pipeline_id: 1,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入应用名称', trigger: 'blur' }],
  pipeline_id: [{ required: true, message: '请输入流水线ID', trigger: 'blur' }],
}

async function loadData() {
  loading.value = true
  try {
    const data = await getApps(page.value, pageSize.value)
    if (Array.isArray(data)) {
      apps.value = data
      total.value = data.length
    } else {
      apps.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载应用列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, { name: '', description: '', pipeline_id: 1 })
  dialogVisible.value = true
}

async function handleCreate() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createApp({ ...form })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
