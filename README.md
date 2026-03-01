# Python-CMDB & DevOps Management Platform

这是一个基于 **FastAPI** (后端) 和 **Vue 3 + Element Plus** (前端) 构建的现代化 DevOps 管理平台。
它集成了资产管理 (CMDB)、持续集成/持续部署 (CI/CD)、日志聚合分析 (AI 驱动) 以及监控报警功能。

## 🌟 核心功能

### 1. 资产管理 (CMDB)
*   **服务器管理**：支持服务器资产的增删改查。
*   **连接验证**：内置 SSH 连通性测试工具，一键验证资产凭据有效性。
*   **IP 地址池**：自动化的 IP 地址分配与占用情况追踪。

### 2. CI/CD 流水线 (多引擎支持)
*   **本地轻量级引擎**：基于 YAML 配置，直接在本地节点执行构建任务，适合小型项目。
*   **Jenkins 引擎集成**：无缝对接已有 Jenkins 服务，支持触发 Job、实时流式回显控制台日志及状态追踪。
*   **实时交互**：通过 WebSocket 提供丝滑的构建日志查看体验。

### 3. AI 智能日志分析 (基于 Drain3)
*   **日志聚类**：利用 `drain3` 算法对海量非结构化日志进行实时模式提取与聚类。
*   **AI 助手**：集成 LLM (LangChain + OpenAI/Zhipu)，支持用户以自然语言询问日志异常（例如：“最近 24 小时是否有 Timeout 或 OOM 报错？”）。
*   **可视化模板**：直观展示日志模板分布及出现频次。

### 4. 发布与监控
*   **应用发布**：支持全量、蓝绿及金丝雀发布策略管理。
*   **监控报警**：自定义策略监控，支持钉钉等主流渠道告警推送。

## 🛠 技术栈

*   **后端**: Python 3.10+, FastAPI, SQLAlchemy (Async/MySQL), Celery (Redis), Pydantic v2.
*   **前端**: Vue 3, Vite, TypeScript, Element Plus, Pinia, ECharts.
*   **集成**: Drain3 (日志挖掘), LangChain (AI 逻辑), Paramiko (SSH), Python-Jenkins.

## 🚀 快速开始

### 1. 后端设置
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (.env)
DATABASE_URL=mysql+aiomysql://root:123456@192.168.9.226:3306/devops_db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your_key
JENKINS_URL=http://your_jenkins

# 启动服务
uvicorn app.main:app --reload
```

### 2. 前端设置
```bash
cd frontend
npm install
npm run dev
```

## 📝 许可证
MIT License
