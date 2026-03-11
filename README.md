# 🎯 FocusAI: Agent-Native Visual Context Engine

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/UI-PyWebView-orange.svg" alt="UI">
  <img src="https://img.shields.io/badge/Agent-Ready-success.svg" alt="Agent Ready">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</div>

<br>

**FocusAI** 不仅仅是一个桌面防分心计时器，它是一个 **为 AI Agent（如 OpenClaw）设计的“全天候视觉记忆中枢”**。它在后台默默记录你的屏幕活动，使用先进的视觉大模型（VLM）为你打分，并提供本地 API 让你的 AI 助手随时“看见”并理解你的工作状态。

![FocusAI Screenshot][(https://github.com/HR2AY/focusAI/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-10%20231521.jpg?raw=true](https://github.com/HR2AY/diary/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-03-10%20231518.png?raw=true)

## ✨ 核心特性 (Key Features)

### 🤖 面向智能体 (Agent-Native)
- **本地微型 HTTP 服务**: 默认运行在 `127.0.0.1:8765`，你的 Agent 可以通过 RESTful API 随时读取你的当前状态、修改目标或获取全天历史。
- **RAG-Ready 记忆流**: 数据按日期（`YYMMDD`）整齐归档。极轻量的 CSV 文本日志供 Agent 快速概览，高精度截图供 Agent 视觉溯源。
- **配置热重载**: Agent 可通过接口直接修改 `config.json`，无需触碰 Python 源码即可无缝切换底层大模型。

### 🧠 万能 VLM 引擎底座 (Universal Model Support)
基于 OpenAI 标准库重构，通过“积木式”配置，支持一键切换全球主流视觉大模型：
- 🟢 **阿里通义千问** (Qwen-VL)
- 🔵 **字节豆包** (Doubao-Vision)
- ⚫ **OpenAI** (GPT-4o)
- 🟠 **本地部署** (Ollama / Llava - 100% 免费断网运行)

### 🖥️ 沉浸式悬浮 UI (Glassmorphism Widget)
- 采用 HTML/CSS/JS + `pywebview` 打造的绝美毛玻璃悬浮窗。
- 隐藏式交互设计，支持专注度实时环形图反馈和 AI 导师毒舌/鼓励点评。

---

## 🚀 快速开始 (Quick Start)

### 对于 Windows 用户（小白/极客皆宜）
我们提供了极简的一键启动脚本，它会自动处理 Python 虚拟环境和所有依赖。

1. 克隆仓库：
   ```bash
   git clone [https://github.com/HR2AY/focusAI.git](https://github.com/HR2AY/focusAI.git)
   cd focusAI
2. 双击运行 `start.bat`。
3. 点击悬浮窗右上角的 **⚙️ 齿轮图标**，选择你的大模型供应商并填入 API Key。
4. 输入你的当前目标（如“写周报”），点击“开始监控”。

### 手动安装 (Mac/Linux/Windows)

```bash
# 1. 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install openai pillow pywebview

# 3. 启动引擎
python main.py

```

---

## 🧩 为 AI Agent 赋能 (Integration for Agents)

让你的 AI 助手（如 OpenClaw, AutoGPT）接管 FocusAI，只需要两步：

1. **导入技能提示词**: 将项目根目录下的 `Skill_FocusAI_Context.md` 复制并添加到你的 Agent System Prompt 中。
2. **通过 API 交互**:
FocusAI 启动后，Agent 即可调用以下本地接口：

| Method | Endpoint | Description | Request Example |
| --- | --- | --- | --- |
| `GET` | `/api/status` | 获取当前专注分数与活动状态 | - |
| `GET` | `/api/history` | 获取本日的所有工作流历史摘要 | - |
| `POST` | `/api/start` | 启动监控并可同步更新任务目标 | `{"goal": "写代码"}` |
| `POST` | `/api/stop` | 停止监控 | - |
| `POST` | `/api/config` | 热重载修改配置 (如模型/频率) | 完整的 JSON 对象 |

*详细 API 规范请参考 `API_Integration.md`。*

---

## ⚙️ 配置文件 (config.json)

首次运行程序会自动生成 `config.json`。它的“积木式”结构如下，你可以随时手动或通过 API 修改它：

```json
{
    "current_provider": "dashscope",
    "providers": {
        "dashscope": {
            "name": "阿里通义千问",
            "base_url": "[https://dashscope.aliyuncs.com/compatible-mode/v1](https://dashscope.aliyuncs.com/compatible-mode/v1)",
            "model_name": "qwen-vl-plus",
            "api_key": "sk-your-key-here"
        },
        "doubao": { ... },
        "openai": { ... },
        "ollama": { ... }
    },
    "settings": {
        "save_dir": "C:\\Users\\Desktop\\FocusOS_Data",
        "interval_seconds": 30,
        "save_images": true
    }
}

```

---

## 🛡️ 隐私与数据安全

* **数据完全本地化**：截图和行为日志默认全部保存在你本地的 `FocusOS_Data` 文件夹中。
* **内存级传输**：程序在向云端 VLM 传输图像时，使用纯内存 Base64 编码，绝不产生多余的临时文件切片。
* **支持全离线模式**：只需在设置中将 Provider 切换为 `ollama`，即可实现 100% 断网的本地监控（需预先配置好本地大模型）。

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```
