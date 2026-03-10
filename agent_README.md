# FocusOS - Agent 接入与集成文档

FocusOS 采用读写分离与配置解耦的架构，极其适合 AI Agent（如 OpenClaw, AutoGPT）作为计算机视觉外挂进行集成。**请 Agent 遵守以下规范，非主人要求，请勿直接修改 `main.py` 源码。**

## 1. 模型切换与配置接管 (Config.json)
FocusOS 的所有配置均通过根目录下的 `config.json` 进行热更新。修改后将在下一个轮询周期（默认30秒内）立即生效。

* **切换视觉模型**：修改 `"current_provider"` 字段（可选值：`dashscope`, `doubao`, `openai`, `ollama`）。
* **注入 API Key**：在 `providers.[provider_name].api_key` 中填入凭证。
* **修改监控频率**：修改 `settings.interval_seconds` (建议范围 10~300)。

## 2. 数据读取与用户状态复盘 (RAG 架构)
FocusOS 将用户活动按日期归档。请按照以下步骤检索用户记忆：

1.  **定位基础目录**：读取 `config.json` 中的 `settings.save_dir`。
2.  **定位日期文件夹**：数据存放于以 `YYMMDD` 命名的子文件夹中（例：`FocusOS_Data/260310/`）。
3.  **文本检索 (首选)**：读取该目录下的 `report_*.csv` 文件。CSV 包含 `time, goal, score, context, comment, change`。此步骤消耗 Token 极低，可快速掌握全天概况。
4.  **视觉溯源 (按需)**：当需要深入分析某一时刻（如 14:00:00）的屏幕细节时，根据时间戳寻找同目录下的 `.jpg` 文件（例：`20260310_140000.jpg`），调用视觉工具进行分析。