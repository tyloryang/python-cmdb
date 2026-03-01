<template>
  <div>
    <!-- Toolbar -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索主机名..."
          style="width: 240px;"
          clearable
          @clear="loadData"
          @keyup.enter="loadData"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="loadData">
          <el-icon><Search /></el-icon> 搜索
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建服务器
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="servers" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="hostname" label="主机名" min-width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="os_type" label="操作系统" width="120" />
        <el-table-column prop="cpu_cores" label="CPU核数" width="90" />
        <el-table-column prop="memory_gb" label="内存(GB)" width="90" />
        <el-table-column prop="disk_gb" label="磁盘(GB)" width="90" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              @click="goTerminal(row.id)"
            >
              终端
            </el-button>
            <el-button
              size="small"
              type="success"
              @click="handlePing(row)"
              :loading="row.pinging"
            >
              验证
            </el-button>
            <el-button
              size="small"
              type="warning"
              @click="handleCollect(row)"
              :loading="row.collecting"
            >
              采集
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(row)"
            >
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

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="新建服务器" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="主机名" prop="hostname">
          <el-input v-model="form.hostname" placeholder="e.g. web-server-01" />
        </el-form-item>
        <el-form-item label="机房ID" prop="idc_room_id">
          <el-input-number v-model="form.idc_room_id" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="操作系统" prop="os_type">
          <el-select v-model="form.os_type" placeholder="选择操作系统" style="width: 100%;">
            <el-option label="CentOS 7" value="centos7" />
            <el-option label="CentOS 8" value="centos8" />
            <el-option label="Ubuntu 20.04" value="ubuntu20" />
            <el-option label="Ubuntu 22.04" value="ubuntu22" />
            <el-option label="Debian 11" value="debian11" />
          </el-select>
        </el-form-item>
        <el-form-item label="CPU核数" prop="cpu_cores">
          <el-input-number v-model="form.cpu_cores" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="内存(GB)" prop="memory_gb">
          <el-input-number v-model="form.memory_gb" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="磁盘(GB)" prop="disk_gb">
          <el-input-number v-model="form.disk_gb" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="SSH端口" prop="ssh_port">
          <el-input-number v-model="form.ssh_port" :min="1" :max="65535" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="SSH用户" prop="ssh_user">
          <el-input v-model="form.ssh_user" placeholder="e.g. root" />
        </el-form-item>
        <el-form-item label="认证方式" prop="ssh_auth_type">
          <el-select v-model="form.ssh_auth_type" style="width: 100%;">
            <el-option label="密码" value="password" />
            <el-option label="密钥" value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证凭证" prop="ssh_credential">
          <el-input
            v-model="form.ssh_credential"
            type="textarea"
            :rows="3"
            placeholder="密码或私钥内容"
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getServers, createServer, deleteServer, pingServer, collectServer } from '@/api/cmdb'

const router = useRouter()

const servers = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  hostname: '',
  idc_room_id: 1,
  os_type: '',
  cpu_cores: 4,
  memory_gb: 8,
  disk_gb: 100,
  ssh_port: 22,
  ssh_user: 'root',
  ssh_auth_type: 'password',
  ssh_credential: '',
})

const rules: FormRules = {
  hostname: [{ required: true, message: '请输入主机名', trigger: 'blur' }],
  os_type: [{ required: true, message: '请选择操作系统', trigger: 'change' }],
  ssh_user: [{ required: true, message: '请输入SSH用户', trigger: 'blur' }],
}

function statusTagType(status: string) {
  const map: Record<string, string> = {
    online: 'success',
    offline: 'danger',
    unknown: 'info',
    maintenance: 'warning',
  }
  return map[status] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const data = await getServers(page.value, pageSize.value)
    if (Array.isArray(data)) {
      servers.value = data
      total.value = data.length
    } else {
      servers.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载服务器列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, {
    hostname: '',
    idc_room_id: 1,
    os_type: '',
    cpu_cores: 4,
    memory_gb: 8,
    disk_gb: 100,
    ssh_port: 22,
    ssh_user: 'root',
    ssh_auth_type: 'password',
    ssh_credential: '',
  })
  dialogVisible.value = true
}

async function handleCreate() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createServer({ ...form })
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
    await ElMessageBox.confirm(`确认删除服务器 "${row.hostname}"？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      confirmButtonClass: 'el-button--danger',
    })
    await deleteServer(row.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err?.response?.data?.detail || '删除失败')
    }
  }
}

async function handlePing(row: any) {
  row.pinging = true
  try {
    const res = await pingServer(row.id)
    ElMessage.success(`${row.hostname}: ${res.msg || '验证成功'}`)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '验证失败')
  } finally {
    row.pinging = false
  }
}

async function handleCollect(row: any) {
  row.collecting = true
  try {
    const res = await collectServer(row.id)
    ElMessage.success(`${row.hostname}: ${res.msg || '采集成功'}`)
    // Update row data in place
    if (res.server) {
      Object.assign(row, res.server)
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '采集失败')
  } finally {
    row.collecting = false
  }
}

function goTerminal(id: number) {
  router.push(`/terminal/${id}`)
}

onMounted(loadData)
</script>
