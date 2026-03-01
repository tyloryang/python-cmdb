<template>
  <el-container style="height: 100vh;">
    <!-- Sidebar -->
    <el-aside width="220px" style="background: #001529; overflow: hidden;">
      <div class="logo">
        <span>DevOps 管理平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
        router
        style="border-right: none; height: calc(100vh - 60px); overflow-y: auto;"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>

        <el-sub-menu index="cmdb">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>CMDB</span>
          </template>
          <el-menu-item index="/cmdb/servers">服务器管理</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="cicd">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>CI/CD</span>
          </template>
          <el-menu-item index="/cicd/pipelines">流水线</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="release">
          <template #title>
            <el-icon><Promotion /></el-icon>
            <span>发布管理</span>
          </template>
          <el-menu-item index="/release/apps">应用管理</el-menu-item>
          <el-menu-item index="/release/releases">发布记录</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="monitor">
          <template #title>
            <el-icon><Bell /></el-icon>
            <span>监控告警</span>
          </template>
          <el-menu-item index="/monitor/alert-rules">告警规则</el-menu-item>
          <el-menu-item index="/monitor/alert-events">告警事件</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="log-analysis">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>日志分析</span>
          </template>
          <el-menu-item index="/log-analysis/watchers">监控任务</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/notification/channels">
          <el-icon><ChatDotRound /></el-icon>
          <span>通知渠道</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main content area -->
    <el-container style="flex-direction: column;">
      <!-- Header -->
      <el-header style="background: #fff; border-bottom: 1px solid #e8e8e8; display: flex; align-items: center; justify-content: space-between; padding: 0 24px;">
        <div style="font-size: 16px; font-weight: 500; color: #333;">
          {{ pageTitle }}
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <el-avatar :size="32" style="background: #1890ff;">
            {{ userInitial }}
          </el-avatar>
          <span style="color: #333;">{{ authStore.user?.username || '用户' }}</span>
          <el-button type="text" @click="handleLogout" style="color: #666;">
            <el-icon><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
      </el-header>

      <!-- Page content -->
      <el-main style="background: #f0f2f5; padding: 24px; overflow-y: auto;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

const routeTitleMap: Record<string, string> = {
  '/dashboard': '仪表盘',
  '/cmdb/servers': '服务器管理',
  '/cicd/pipelines': '流水线管理',
  '/release/apps': '应用管理',
  '/release/releases': '发布记录',
  '/monitor/alert-rules': '告警规则',
  '/monitor/alert-events': '告警事件',
  '/log-analysis/watchers': '日志监控任务',
  '/notification/channels': '通知渠道',
  '/terminal': 'WebSSH 终端',
}

const pageTitle = computed(() => {
  const path = route.path
  for (const key of Object.keys(routeTitleMap)) {
    if (path.startsWith(key)) return routeTitleMap[key]
  }
  return 'DevOps 管理平台'
})

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确认退出登录？', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    authStore.logout()
    router.push('/login')
  } catch {
    // cancelled
  }
}
</script>

<style scoped>
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  background: #002140;
  padding: 0 16px;
  overflow: hidden;
  white-space: nowrap;
}
</style>
