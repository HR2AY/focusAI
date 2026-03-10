# FocusOS API 文档

FocusOS 通过 `pywebview` 的 `js_api` 机制将 Python 后端方法暴露给前端 JavaScript 调用。

## 调用方式

前端通过 `window.pywebview.api.<methodName>(...args)` 调用 Python 方法：

```javascript
// 示例：开始监控
window.pywebview.api.start_monitor("编写代码").then(res => {
    console.log(res.status); // "started"
});

// 示例：获取状态
window.pywebview.api.get_status().then(data => {
    console.log(data.score, data.comment, data.running);
});
```

---

## 接口列表

### `start_monitor(goal)`

启动专注监控循环。

**参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| goal | string | 用户设定的当前目标（如"编写 Python 代码"）|

**返回值：**
```json
{"status": "started"}
```

**说明：**
- 启动后台线程，每 30 秒截图并调用 Qwen-VL-Plus 分析
- 如果已在运行，调用无效果

---

### `stop_monitor()`

停止专注监控。

**返回值：**
```json
{"status": "stopped"}
```

---

### `get_status()`

获取当前专注状态（供前端轮询更新 UI）。

**返回值：**
```json
{
    "score": 100,           // 当前专注分数 (0-200)
    "comment": "保持专注...", // AI 评价文本
    "running": true         // 监控是否运行中
}
```

---

### `generate_report()`

导出历史数据为 CSV 报表。

**返回值：**
```json
{"msg": "报表已保存至: C:\\Users\\...\\report_20250308_143022.csv"}
```

**说明：**
- 文件保存到 `~/Desktop/FocusOS_Data/`
- 若暂无数据返回 `{"msg": "暂无数据可生成"}`

---

## 数据结构

### 历史记录项 (history_data 单条)

```python
{
    "time": "2025-03-08 14:30:00",  # 时间戳
    "score": 100,                    # 当时的分数
    "comment": "专注工作中",          # AI 评价
    "change": 1                      # 分数变化 (+1 或 -2)
}
```

---

## 前端事件

### `pywebviewready`

Python 后端就绪后触发。

```javascript
window.addEventListener('pywebviewready', function() {
    console.log('FocusOS 后端已就绪');
});
```

---

## 文件位置

- **主程序**：`main.py` (FocusApi 类)
- **前端页面**：`gui/index.html`

## 注意事项

1. 所有 API 调用都是异步的，返回 Promise
2. 截图临时文件保存在 `~/Desktop/FocusOS_Data/_monitor_temp.jpg`
3. 报告 CSV 使用 UTF-8-SIG 编码，Excel 可直接打开
