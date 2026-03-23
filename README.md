# 🎯 FocusEngine: Agent-Native Visual Context Engine

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/UI-PyWebView-orange.svg" alt="UI">
  <img src="https://img.shields.io/badge/HTTP-stdlib-blueviolet.svg" alt="HTTP Server">
  <img src="https://img.shields.io/badge/VLM-OpenAI--Compatible-lightgrey.svg" alt="VLM">
  <img src="https://img.shields.io/badge/Agent-Ready-success.svg" alt="Agent Ready">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</div>

<br>

<div align="center">
  <img src="https://github.com/HR2AY/diary/blob/main/ENGINE.png" width="70%">
</div>

**FocusEngine** 是一个为 AI Agent（如 OpenClaw、AutoGPT）设计的 **"全天候视觉记忆中枢"**。它在后台持续截取屏幕，通过视觉大模型（VLM）实时评估专注度，并以本地 HTTP API 的形式将用户的工作状态暴露给外部 Agent，让你的 AI 助手随时"看见"并理解你在做什么。

---

## 📐 架构概览 (Architecture for AI Agents)

> **如果你是一个 AI Agent，请阅读本节来理解 FocusEngine 的全部能力。**

### 系统架构图

```
┌───────────────────────────────────────────────────────────────┐
│                        main.py (352 行单文件)                  │
│                                                               │
│  ┌─────────────────┐   ┌──────────────┐   ┌───────────────┐  │
│  │  FocusEngine    │   │  FocusApi    │   │AgentAPIHandler│  │
│  │  (核心引擎)      │◄──│  (GUI 桥接)  │   │  (HTTP API)   │  │
│  │                 │   └──────┬───────┘   └───────┬───────┘  │
│  │ - 截图采集       │          │ pywebview          │ HTTP     │
│  │ - 图片压缩       │          │ JS Bridge          │ REST     │
│  │ - VLM API 调用   │          ▼                    ▼         │
│  │ - 评分解析       │   ┌──────────────┐   ┌───────────────┐  │
│  │ - 历史记录管理    │   │ index.html   │   │ 外部 AI Agent │  │
│  └────────┬────────┘   │ (毛玻璃悬浮窗) │   │ 127.0.0.1:8765│  │
│           │            └──────────────┘   └───────────────┘  │
│           ▼                                                   │
│  ┌─────────────────┐                                          │
│  │ ConfigManager   │                                          │
│  │ (config.json)   │                                          │
│  └─────────────────┘                                          │
└───────────────────────────────────────────────────────────────┘
           │
           ▼  文件输出
  ~/Desktop/FocusOS_Data/YYMMDD/
    ├── YYYYMMDD_HHMMSS.jpg   (截图)
    └── report_*.csv           (结构化日志)
```

### 技术栈

| 层级 | 技术选型 | 说明 |
|:---|:---|:---|
| **语言/运行时** | Python 3.8+ | 单文件 `main.py`（352 行），零框架依赖 |
| **VLM 客户端** | `openai` SDK | 统一接入所有 OpenAI 兼容接口（千问/豆包/GPT-4o/Ollama） |
| **截图 & 压缩** | `Pillow` (`ImageGrab` + `Image`) | 自适应 JPEG 压缩，目标 ≤400KB，最大边 1024px |
| **桌面 GUI** | `pywebview` + 原生 HTML/CSS/JS | 毛玻璃悬浮窗 340×365px，无任何前端框架 |
| **HTTP API 服务** | `http.server.HTTPServer` (stdlib) | 仅绑定 `127.0.0.1:8765`，支持 CORS |
| **数据存储** | 本地文件系统 (JSON + CSV + JPEG) | 按日期 `YYMMDD` 文件夹归档 |
| **线程模型** | `threading` (stdlib) | 主线程 GUI/HTTP，守护线程截图轮询（100ms 可中断 sleep） |
| **配置管理** | `config.json` (热重载) | Agent 可通过 API 直接修改，运行时生效 |

### 四个核心类

| 类名 | 职责 | 关键方法 |
|:---|:---|:---|
| **`FocusEngine`** | 核心大脑：截图→压缩→VLM 调用→评分解析→历史记录 | `start(goal)`, `stop()`, `get_status()`, `_worker_loop()`, `compress_image()`, `parse_llm_output()` |
| **`ConfigManager`** | 配置持久化：读写 `config.json`，首次运行自动生成默认配置 | `load_config()`, `save_config(new_config)` |
| **`FocusApi`** | pywebview JS Bridge：把引擎方法暴露给前端 JS 调用 | `get_settings()`, `save_settings()`, `start_monitor(goal)`, `stop_monitor()`, `get_status()`, `generate_report()` |
| **`AgentAPIHandler`** | HTTP REST 服务：供外部 AI Agent 远程调控引擎 | 继承 `BaseHTTPRequestHandler`，处理 `do_GET` / `do_POST` |

### 数据流

```
用户屏幕
  │  ImageGrab.grab()
  ▼
图片压缩 (compress_image)
  │  - 缩放至 ≤1024px
  │  - JPEG 自适应质量 (90→10 递减)
  │  - 目标 ≤400KB
  ▼
Base64 编码 → OpenAI SDK 调用
  │  - Prompt: 用户目标 + 当前分数 + 评分任务描述
  │  - Image: data:image/jpeg;base64,{...}
  │  - max_tokens: 300
  ▼
VLM 返回原始文本 → parse_llm_output() 正则解析
  │  - score=(-2|-1|+1)  分数变化量
  │  - context="窗口概括"  ≤30 字
  │  - text="导师评价"
  ▼
更新引擎状态
  ├─→ current_score (0~200 范围钳制)
  ├─→ ai_comment (导师评语)
  ├─→ history_data[] (内存列表追加)
  ├─→ 磁盘: 保存截图 JPEG (可选)
  ├─→ HTTP API: /api/focus/score 可读取
  └─→ GUI: 前端每 1s 轮询 get_status() 更新环形图
```

---

## ✨ 核心特性 (Key Features)

### 🤖 面向智能体 (Agent-Native)
- **本地 HTTP 服务**: 仅绑定 `127.0.0.1:8765`，基于 Python stdlib `HTTPServer`，支持 CORS，Agent 通过 RESTful API 随时读取状态、修改目标或获取全天历史。
- **RAG-Ready 记忆流**: 数据按日期（`YYMMDD`）整齐归档。CSV 文本日志供 Agent 快速概览，JPEG 截图供 Agent 视觉溯源。
- **配置热重载**: Agent 可通过 `POST /api/config` 直接修改 `config.json`，运行时切换底层大模型，无需重启。
- **Headless 模式**: 支持 `python main.py --headless` 无 GUI 启动，仅运行 HTTP API 服务，适合服务器/后台场景。

### 🧠 万能 VLM 引擎底座 (Universal Model Support)
全部通过 OpenAI SDK 的统一 `chat.completions.create()` 接口接入，切换只需改 `config.json` 中的 `current_provider`：

| Provider | base_url | 默认模型 | 特点 |
|:---|:---|:---|:---|
| 🟢 **阿里通义千问** (Dashscope) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` | 默认推荐，性价比极高 |
| 🔵 **字节豆包** (Doubao) | `https://ep.api.vanguards.volces.com/api/v3` | 自定义 endpoint | 可接入火山引擎模型 |
| ⚫ **OpenAI** | `https://api.openai.com/v1` | `gpt-4o` | 最强能力，成本较高 |
| 🟠 **Ollama** (本地) | `http://localhost:11434/v1` | `llava` | 100% 离线免费，无需 API Key |

### 🖥️ 沉浸式悬浮 UI (Glassmorphism Widget)
- 基于 `pywebview` + 原生 HTML/CSS/JS，340×365px 无边框悬浮窗。
- 毛玻璃效果（`backdrop-filter: blur(30px)`），圆环进度图（`conic-gradient`）实时反馈分数。
- 颜色语义：分数 ≥80 绿色 / <80 橙色 / <50 红色，配合缩放动画。
- 内置设置面板（齿轮图标触发滑入动画），可直接切换 Provider、填写 API Key。

---

<p align="center">
    <img src="https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-12%20181129.jpg?raw=true" width="32%">
    <img src="https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-12%20181238.jpg?raw=true" width="32%">
    <img src="https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-12%20181157.jpg?raw=true" width="32%">
</p>

---

## 🚀 快速开始 (Quick Start)

### 对于 Windows 用户（一键启动）

`start.bat` 会自动创建 venv、通过清华镜像安装依赖、启动程序。

1. 克隆仓库：
   ```bash
   git clone https://github.com/HR2AY/focusAI.git
   cd focusAI
   ```
2. 双击运行 `start.bat`。
3. 点击悬浮窗右上角的 **⚙️ 齿轮图标**，选择你的大模型供应商并填入 API Key。
4. 输入你的当前目标（如"写周报"），点击"开始监控"。

### 手动安装 (Mac/Linux/Windows)

```bash
# 1. 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖（仅 3 个包）
pip install openai pillow pywebview

# 3. 启动引擎（带 GUI）
python main.py

# 3b. 或以 Headless 模式启动（仅 HTTP API，无 GUI）
python main.py --headless
```

### 依赖清单

| 包名 | 用途 |
|:---|:---|
| `openai` | 统一的多 Provider VLM 客户端 |
| `Pillow` | 屏幕截图（`ImageGrab`）+ 图片压缩 |
| `pywebview` | 桌面悬浮窗 GUI（Chromium 内核） |

---

## 📶 Agent HTTP API 参考

FocusEngine 启动后，HTTP 服务监听 `http://127.0.0.1:8765`。所有响应均为 JSON，支持 CORS。

| Method | Endpoint | 请求体 | 响应 | 说明 |
|:---|:---|:---|:---|:---|
| `GET` | `/api/focus/score` | - | `{score, comment, running, current_goal}` | 获取当前专注分数与实时状态 |
| `GET` | `/api/history` | - | `{history: [{time, goal, score, context, comment, change}, ...]}` | 获取本次运行以来的所有历史记录 |
| `POST` | `/api/start` | `{"goal": "写代码"}` (可选) | `{status: "started", goal: "..."}` | 启动监控，可同时设置目标 |
| `POST` | `/api/stop` | - | `{status: "stopped"}` | 停止监控 |
| `POST` | `/api/goal` | `{"goal": "新目标"}` | `{status: "goal_updated", goal: "..."}` | 运行中更新任务目标 |
| `POST` | `/api/config` | 完整 config JSON 对象 | `{status: "config_updated"}` | 热重载配置（切换模型/频率等） |

### Agent 集成两步走

1. **导入技能提示词**: 将 `skills/SKILL.md` 添加到你的 Agent System Prompt 或 ClawHub 的 SKILL 文件夹中。
2. **通过 HTTP API 交互**: Agent 启动后即可调用上述接口读取状态、控制监控。

---

## 👁️ Agent 专属上下文感知 (Context Awareness)

FocusEngine 解决了 Agent "不知道用户离开时发生了什么"的问题。通过读取自动生成的结构化日志，Agent 可以瞬间补全用户的全天活动上下文。

**磁盘数据结构**:
```
~/Desktop/FocusOS_Data/
└── YYMMDD/                          # 按日期归档（如 260323）
    ├── YYYYMMDD_HHMMSS.jpg          # 屏幕截图（save_images=true 时保存）
    ├── YYYYMMDD_HHMMSS.jpg
    └── report_YYYYMMDD_HHMMSS.csv   # 导出的 CSV 报告
```

**CSV 格式**:
```csv
time,goal,score,context,comment,change
2026-03-23 14:30:45,高效工作,100,VS Code 编写 Python,专注力满分！,1
2026-03-23 14:31:15,高效工作,101,VS Code 编写 Python,继续加油！,1
```

**内存数据结构** (`history_data`，通过 `/api/history` 获取):
```json
[
  {
    "time": "2026-03-23 14:30:45",
    "goal": "高效工作",
    "score": 100,
    "context": "VS Code 编写 Python",
    "comment": "专注力满分！",
    "change": 1
  }
]
```

<div align="center">
  <img src="https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-12%20211802.jpg" width="50%">
</div>

---

## 🧩 高度 DIY：为 Vibe Coding 而生

整个后端仅 352 行 Python，单文件 `main.py`，无框架绑定，非常适合用 Cursor、Claw 或 Windsurf 进行 **Vibe Coding**。

### 为什么它极易改造？
* **单文件四类架构**：`FocusEngine` + `ConfigManager` + `FocusApi` + `AgentAPIHandler`，职责清晰，改一个不影响其他。
* **代码透明度高**：不依赖任何第三方 GUI/Web 框架，HTML/CSS 原生写法，毛玻璃效果和交互动画一目了然。
* **开放式扩展**：
    * 想加个"分心时自动播放警报"？在 `_worker_loop` 里加 3 行代码即可。
    * 想把分数实时同步到 Notion 或飞书？只需在 `history_data` 记录处挂载一个 Webhook。
    * 想接入本地摄像头进行疲劳监测？核心引擎已为你留好了多模态输入的接口位。

> **"如果你能用嘴描述出来，你就能用 AI 将 FocusEngine 改造成你想要的任何样子。"**

---

## ⚙️ 配置文件 (config.json)

首次运行由 `ConfigManager` 自动生成。可手动编辑或通过 `POST /api/config` 热重载：

```json
{
    "current_provider": "dashscope",
    "providers": {
        "dashscope": {
            "name": "阿里通义千问",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": "qwen-vl-plus",
            "api_key": "sk-your-key-here"
        },
        "doubao": {
            "name": "字节豆包",
            "base_url": "https://ep.api.vanguards.volces.com/api/v3",
            "model_name": "ep-xxxxxx",
            "api_key": ""
        },
        "openai": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o",
            "api_key": ""
        },
        "ollama": {
            "name": "Ollama 本地",
            "base_url": "http://localhost:11434/v1",
            "model_name": "llava",
            "api_key": "ollama"
        }
    },
    "settings": {
        "save_dir": "~/Desktop/FocusOS_Data",
        "interval_seconds": 30,
        "save_images": true
    }
}
```

---

## 💸 极低运行成本：AI 助理的"月租"仅需一杯奶茶

![Cost Analysis](https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-12%20190122.jpg)

### 📊 成本计算模型

以**高强度使用**（每天工作 6 小时，每周 6 天）为例：

| 项目 | 数据指标 | 备注 |
| :--- | :--- | :--- |
| **单次请求 Token** | ~837 Tokens | 截图 Base64 (~700) + Prompt & 输出 (~137) |
| **模型单价** | ¥0.0015 / 1k Tokens | 阿里云/字节等主流 VLM 兼容接口价格 |
| **采样频率** | 30 秒 / 次 | 默认间隔，可通过 config 调整 |
| **日运行量** | 720 次请求 / 天 | 120次/小时 × 6小时 |

### 💰 费用清单 (RMB)

| 周期 | Token 消耗 | 预计费用 | 形象比喻 |
| :--- | :--- | :--- | :--- |
| **每日 (6h)** | ~602 K | **¥ 0.90** | 一根冰棍 |
| **每周 (36h)** | ~3.6 M | **¥ 5.40** | 一瓶可乐 |
| **每月 (144h)** | ~14.4 M | **¥ 21.60** | 一杯奶茶 |

> [!TIP]
> **如何进一步省钱？**
> 1. **延长间隔**：将 `interval_seconds` 调整为 60，成本直接**降低 50%**。
> 2. **本地模式**：切换 Provider 为 `ollama`，使用本地视觉模型（如 Llava），运行成本为 **0**。

### 🔍 为什么这么省？
1. **输入优化**：`compress_image()` 在上传前将截图智能压缩至 ≤400KB，最大边 ≤1024px，极大减少 Base64 体积。
2. **零废话输出**：Prompt 要求 AI 仅输出 `score=... context="..." text="..."`，平均每次输出仅约 40 Tokens。

---

## 🛡️ 隐私与数据安全

* **数据完全本地化**：截图和行为日志全部保存在本地 `FocusOS_Data` 文件夹中，不上传任何第三方存储。
* **内存级传输**：截图在内存中 Base64 编码后直接发送至 VLM API，不产生临时文件。
* **网络隔离**：HTTP API 仅绑定 `127.0.0.1`（loopback），外部网络无法访问。
* **全离线模式**：将 Provider 切换为 `ollama`，即可实现 100% 断网本地监控。

---

## ClawHub 安装指南

* 在 ClawHub 中搜索 **focus-ai** 即可自动安装。***注意：若已本地安装 FocusEngine，配置 Skill 时请告诉 Clawbot 本地路径。***

![FocusEngine Screenshot](https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-10%20231518.png?raw=true)

---

## 📁 项目结构

```
focusAI/
├── main.py              # 完整后端（352 行）：FocusEngine + ConfigManager + FocusApi + AgentAPIHandler
├── config.json          # 运行时自动生成的配置文件
├── start.bat            # Windows 一键启动脚本（自动 venv + 清华镜像装依赖）
├── gui/
│   └── index.html       # 毛玻璃悬浮窗 UI（纯 HTML/CSS/JS，无框架）
├── skills/
│   └── SKILL.md         # Agent 集成技能提示词（ClawHub 兼容）
└── README.md
```

---

## 联系方式

本项目为单人 Vibe Coding 开发而成，bug 反馈 / 功能建议 / 交流合作请添加微信号：**Hrzay050204**

<div align="center">
  <img src="https://github.com/HR2AY/diary/blob/main/default.jpg" width="30%">
</div>

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
