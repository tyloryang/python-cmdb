<template>
  <div class="terminal-page">
    <!-- Header bar -->
    <div class="terminal-header">
      <el-button size="small" @click="router.back()" style="color: #ccc; border-color: #555;">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <span class="terminal-title">WebSSH 终端 - 服务器 #{{ serverId }}</span>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 12px; color: #aaa;">状态:</span>
        <el-tag :type="wsConnected ? 'success' : 'danger'" size="small" effect="dark">
          {{ wsConnected ? '已连接' : '未连接' }}
        </el-tag>
        <el-button
          v-if="!wsConnected"
          size="small"
          type="primary"
          @click="connectWs"
          style="margin-left: 4px;"
        >
          重连
        </el-button>
      </div>
    </div>

    <!-- Terminal container -->
    <div ref="terminalEl" id="terminal" class="terminal-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const serverId = route.params.serverId as string
const terminalEl = ref<HTMLElement | null>(null)
const wsConnected = ref(false)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

function initTerminal() {
  if (!terminalEl.value) return

  term = new Terminal({
    theme: {
      background: '#0d1117',
      foreground: '#c9d1d9',
      cursor: '#58a6ff',
      selectionBackground: '#264f78',
    },
    fontSize: 14,
    fontFamily: '"Cascadia Code", "Fira Code", "Courier New", monospace',
    cursorBlink: true,
    scrollback: 5000,
    allowTransparency: false,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalEl.value)
  fitAddon.fit()

  // Forward keyboard input to WebSocket
  term.onData((data: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data }))
    }
  })

  // Handle window resize
  resizeObserver = new ResizeObserver(() => {
    if (fitAddon && term) {
      fitAddon.fit()
      const { rows, cols } = term
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', rows, cols }))
      }
    }
  })
  resizeObserver.observe(terminalEl.value)
}

function connectWs() {
  if (ws) {
    ws.close()
    ws = null
  }

  const wsBase = import.meta.env.VITE_WS_BASE
  const token = authStore.token
  ws = new WebSocket(`${wsBase}/api/v1/terminal/${serverId}?token=${encodeURIComponent(token)}`)

  ws.onopen = () => {
    wsConnected.value = true
    if (term) {
      term.write('\r\n\x1b[32m[已连接到服务器 #' + serverId + ']\x1b[0m\r\n')
    }
    // Send initial resize
    if (term && fitAddon) {
      fitAddon.fit()
      const { rows, cols } = term
      ws!.send(JSON.stringify({ type: 'resize', rows, cols }))
    }
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'output' && term) {
        term.write(msg.data)
      } else if (msg.type === 'error' && term) {
        term.write('\r\n\x1b[31m[错误] ' + msg.data + '\x1b[0m\r\n')
      }
    } catch {
      if (term) {
        term.write(event.data)
      }
    }
  }

  ws.onerror = () => {
    wsConnected.value = false
    if (term) {
      term.write('\r\n\x1b[31m[连接错误]\x1b[0m\r\n')
    }
  }

  ws.onclose = (evt) => {
    wsConnected.value = false
    if (term) {
      term.write(`\r\n\x1b[33m[连接已断开 (code: ${evt.code})]\x1b[0m\r\n`)
    }
  }
}

onMounted(() => {
  initTerminal()
  connectWs()
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  if (term) {
    term.dispose()
    term = null
  }
})
</script>

<style scoped>
.terminal-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  background: #0d1117;
  border-radius: 6px;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  flex-shrink: 0;
}

.terminal-title {
  color: #c9d1d9;
  font-size: 14px;
  font-weight: 500;
  flex: 1;
}

.terminal-container {
  flex: 1;
  overflow: hidden;
  padding: 8px;
}

#terminal {
  height: 100%;
}
</style>
