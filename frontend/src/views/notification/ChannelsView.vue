<template>
  <div>
    <!-- Toolbar -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建通知渠道
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="channels" v-loading="loading" style="width: 100%;" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="渠道名称" min-width="160" />
        <el-table-column prop="channel_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="channelTagType(row.channel_type)" size="small">
              {{ channelTypeLabel(row.channel_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              :loading="testingId === row.id"
              @click="handleTest(row)"
            >
              测试
            </el-button>
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

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="新建通知渠道" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.name" placeholder="渠道名称" />
        </el-form-item>
        <el-form-item label="渠道类型" prop="channel_type">
          <el-select v-model="form.channel_type" style="width: 100%;" @change="onTypeChange">
            <el-option label="钉钉" value="dingtalk" />
            <el-option label="邮件" value="email" />
            <el-option label="Webhook" value="webhook" />
          </el-select>
        </el-form-item>

        <!-- Dingtalk config -->
        <template v-if="form.channel_type === 'dingtalk'">
          <el-form-item label="Webhook URL" prop="config.webhook_url">
            <el-input v-model="form.config.webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </el-form-item>
          <el-form-item label="签名密钥">
            <el-input v-model="form.config.secret" placeholder="可选，加签密钥" />
          </el-form-item>
        </template>

        <!-- Email config -->
        <template v-if="form.channel_type === 'email'">
          <el-form-item label="SMTP 主机" prop="config.smtp_host">
            <el-input v-model="form.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="SMTP 端口" prop="config.smtp_port">
            <el-input-number v-model="form.config.smtp_port" :min="1" :max="65535" style="width: 100%;" />
          </el-form-item>
          <el-form-item label="SMTP 用户名" prop="config.smtp_user">
            <el-input v-model="form.config.smtp_user" placeholder="user@example.com" />
          </el-form-item>
          <el-form-item label="SMTP 密码" prop="config.smtp_password">
            <el-input v-model="form.config.smtp_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="收件人" prop="config.to">
            <el-select
              v-model="form.config.to"
              multiple
              filterable
              allow-create
              placeholder="输入邮箱后回车"
              style="width: 100%;"
            />
          </el-form-item>
        </template>

        <!-- Webhook config -->
        <template v-if="form.channel_type === 'webhook'">
          <el-form-item label="Webhook URL" prop="config.url">
            <el-input v-model="form.config.url" placeholder="https://your-webhook-url.com" />
          </el-form-item>
          <el-form-item label="请求头">
            <el-input
              v-model="form.config.headers_json"
              type="textarea"
              :rows="3"
              placeholder='可选，JSON格式，如: {"Authorization":"Bearer xxx"}'
            />
          </el-form-item>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getChannels, createChannel, deleteChannel, testChannel } from '@/api/notification'

const channels = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const testingId = ref<number | null>(null)

const form = reactive<{
  name: string
  channel_type: string
  config: Record<string, any>
}>({
  name: '',
  channel_type: 'dingtalk',
  config: {
    webhook_url: '',
    secret: '',
    smtp_host: '',
    smtp_port: 465,
    smtp_user: '',
    smtp_password: '',
    to: [] as string[],
    url: '',
    headers_json: '',
  },
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  channel_type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }],
}

function channelTagType(type: string) {
  const map: Record<string, string> = {
    dingtalk: 'primary',
    email: 'success',
    webhook: 'warning',
  }
  return map[type] || 'info'
}

function channelTypeLabel(type: string) {
  const map: Record<string, string> = {
    dingtalk: '钉钉',
    email: '邮件',
    webhook: 'Webhook',
  }
  return map[type] || type
}

function onTypeChange() {
  // Reset config on type change
  Object.assign(form.config, {
    webhook_url: '',
    secret: '',
    smtp_host: '',
    smtp_port: 465,
    smtp_user: '',
    smtp_password: '',
    to: [],
    url: '',
    headers_json: '',
  })
}

async function loadData() {
  loading.value = true
  try {
    const data = await getChannels(page.value, pageSize.value)
    if (Array.isArray(data)) {
      channels.value = data
      total.value = data.length
    } else {
      channels.value = data.items || data.data || []
      total.value = data.total || 0
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载通知渠道失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, {
    name: '',
    channel_type: 'dingtalk',
    config: {
      webhook_url: '',
      secret: '',
      smtp_host: '',
      smtp_port: 465,
      smtp_user: '',
      smtp_password: '',
      to: [],
      url: '',
      headers_json: '',
    },
  })
  dialogVisible.value = true
}

async function handleCreate() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    // Build payload
    const payload: any = {
      name: form.name,
      channel_type: form.channel_type,
      config: {},
    }

    if (form.channel_type === 'dingtalk') {
      payload.config = { webhook_url: form.config.webhook_url, secret: form.config.secret }
    } else if (form.channel_type === 'email') {
      payload.config = {
        smtp_host: form.config.smtp_host,
        smtp_port: form.config.smtp_port,
        smtp_user: form.config.smtp_user,
        smtp_password: form.config.smtp_password,
        to: form.config.to,
      }
    } else if (form.channel_type === 'webhook') {
      let headers: Record<string, string> = {}
      if (form.config.headers_json) {
        try {
          headers = JSON.parse(form.config.headers_json)
        } catch {
          ElMessage.error('请求头格式错误，请使用有效的 JSON')
          submitting.value = false
          return
        }
      }
      payload.config = { url: form.config.url, headers }
    }

    await createChannel(payload)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function handleTest(row: any) {
  testingId.value = row.id
  try {
    await testChannel(row.id)
    ElMessage.success('测试消息已发送，请检查接收端')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '测试发送失败')
  } finally {
    testingId.value = null
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除通知渠道 "${row.name}"？`, '确认删除', { type: 'warning' })
    await deleteChannel(row.id)
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
