import os
import io
import json
import csv
import time
import threading
import re
import sys
import base64
import webview  # pip install pywebview
from openai import OpenAI  # pip install openai
from datetime import datetime
from PIL import Image, ImageGrab

# ================= 资源路径处理 =================
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ================= 积木式配置管理类 =================
CONFIG_FILE = resource_path("config.json")

class ConfigManager:
    def __init__(self):
        # 默认配置：完美的 "积木式" 结构，Agent 最爱
        self.default_config = {
            "current_provider": "dashscope",  # 当前选中的供应商
            
            "providers": {
                "dashscope": {
                    "name": "阿里通义千问",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model_name": "qwen-vl-plus",
                    "api_key": ""
                },
                "doubao": {
                    "name": "字节豆包",
                    "base_url": "https://ep.api.vanguards.volces.com/api/v3", # 豆包的通用兼容地址
                    "model_name": "ep-xxxxxx", # Agent 需要替换为真实的 Endpoint
                    "api_key": ""
                },
                "openai": {
                    "name": "OpenAI 官方",
                    "base_url": "https://api.openai.com/v1",
                    "model_name": "gpt-4o",
                    "api_key": ""
                },
                "ollama": {
                    "name": "本地部署 (Ollama)",
                    "base_url": "http://localhost:11434/v1",
                    "model_name": "llava",
                    "api_key": "ollama" # 本地部署通常不需要真实 Key
                }
            },
            
            "settings": {
                "save_dir": os.path.join(os.path.expanduser("~"), 'Desktop', 'FocusOS_Data'),
                "interval_seconds": 30,
                "save_images": True
            }
        }
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config(self.default_config)
            return self.default_config
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # 递归合并配置，防止新版本增加字段时旧 JSON 报错
                merged = {**self.default_config, **loaded}
                merged["providers"] = {**self.default_config["providers"], **loaded.get("providers", {})}
                merged["settings"] = {**self.default_config["settings"], **loaded.get("settings", {})}
                return merged
        except:
            return self.default_config

    def save_config(self, new_config):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)
        self.config = new_config

# ================= 图像与文本处理 =================
def compress_image(image, target_size_kb=400, max_dimension=1024):
    width, height = image.size
    if max(width, height) > max_dimension:
        scale = max_dimension / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    if image.mode in ("RGBA", "P"): image = image.convert("RGB")
    
    target_bytes = target_size_kb * 1024
    quality = 90
    while True:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=quality)
        if img_byte_arr.tell() <= target_bytes: break
        if quality > 20: quality -= 10
        else:
            image = image.resize((int(image.size[0]*0.9), int(image.size[1]*0.9)), Image.Resampling.LANCZOS)
            quality = 60
    return img_byte_arr

def parse_llm_output(raw_text):
    result = {"json_data": [], "score_change": 0, "comment": "保持专注...", "context": "无数据"}
    try:
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match: result["json_data"] = json.loads(match.group())
    except: pass
    
    score_match = re.search(r'score\s*=\s*(-?\d+)', raw_text)
    if score_match: 
        try: 
            val = int(score_match.group(1))
            if val > 10: val = 1
            elif val < -10: val = -2
            result["score_change"] = val
        except: pass

    context_match = re.search(r'context\s*=\s*["\'](.*?)["\']', raw_text)
    if context_match: result["context"] = context_match.group(1)

    # 核心修复：\b 防止匹配到 context 里面的 text
    text_match = re.search(r'\btext\s*=\s*["\'](.*?)["\']', raw_text)
    if text_match: result["comment"] = text_match.group(1)

    return result

# ================= API 桥接类 =================
class FocusApi:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.is_running = False
        self.user_goal = "高效工作"
        self.current_score = 100
        self.ai_comment = "Focus OS 已就绪"
        self.history_data = []

    def get_settings(self):
        """提供给前端读取配置"""
        return self.config_manager.config

    def save_settings(self, new_settings):
        """提供给前端保存配置"""
        self.config_manager.save_config(new_settings)
        return {"status": "success", "msg": "设置已保存！"}

    def start_monitor(self, goal):
        cfg = self.config_manager.config
        provider = cfg["current_provider"]
        api_key = cfg["providers"][provider]["api_key"]
        
        if not api_key:
            return {"status": "error", "msg": f"请先在设置中配置 {provider} 的 API Key！"}

        if not self.is_running:
            self.is_running = True
            if goal: self.user_goal = goal
            t = threading.Thread(target=self._worker_loop)
            t.daemon = True
            t.start()
        return {"status": "started"}

    def stop_monitor(self):
        self.is_running = False
        return {"status": "stopped"}

    def update_goal(self, new_goal):
        if new_goal and new_goal.strip():
            self.user_goal = new_goal.strip()
        return {"status": "updated", "goal": self.user_goal}

    def get_status(self):
        return {
            "score": self.current_score,
            "comment": self.ai_comment,
            "running": self.is_running
        }

    def generate_report(self):
        if not self.history_data:
            return {"msg": "暂无数据可生成"}
        
        base_dir = self.config_manager.config["settings"]["save_dir"]
        today_folder = datetime.now().strftime('%y%m%d') # 生成类似 260310 的文件夹名
        save_dir = os.path.join(base_dir, today_folder)

        if not os.path.exists(save_dir): os.makedirs(save_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(save_dir, f"report_{timestamp}.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "goal", "score", "context", "comment", "change"])
            writer.writeheader()
            writer.writerows(self.history_data)
        
        return {"msg": f"报表已保存至: {csv_path}"}

    def _worker_loop(self):
        while self.is_running:
            start_time = time.time()
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            cfg = self.config_manager.config
            provider_key = cfg["current_provider"]
            provider_cfg = cfg["providers"][provider_key]

            base_dir = cfg["settings"]["save_dir"]
            today_folder = datetime.now().strftime('%y%m%d')
            save_dir = os.path.join(base_dir, today_folder)
            
            if not os.path.exists(save_dir): os.makedirs(save_dir)

            try:
                # 1. 截图与压缩
                screen = ImageGrab.grab()
                compressed = compress_image(screen)
                
                # 2. 按需保存图片到硬盘 (供 Agent 检索)
                if cfg["settings"]["save_images"]:
                    img_path = os.path.join(save_dir, f"{file_timestamp}.jpg")
                    with open(img_path, "wb") as f: f.write(compressed.getvalue())

                # 3. 将图片转为 Base64 (彻底抛弃硬盘临时文件，提升性能)
                base64_image = base64.b64encode(compressed.getvalue()).decode('utf-8')

                # 4. 初始化万能 OpenAI 客户端
                client = OpenAI(
                    api_key=provider_cfg["api_key"],
                    base_url=provider_cfg["base_url"] if provider_cfg["base_url"] else None
                )

                # 5. 组装强力 Prompt
                prompt = (
                    f"用户目标:【{self.user_goal}】; 用户当前总分：【{self.current_score}】\n"
                    "请执行以下任务：\n"
                    "1. 识别窗口: 忽略任务栏，概括屏幕上的活动，内容不超过30字\n"
                    "2. 专注力打分: 严格参照用户目标，强相关+1分，偏离-1分，完全分心-2分。除非与目标强相关，否则一律扣分。\n"
                    "3. 精神导师评价: 结合当前总分和状态，对用户说一句简短的话，鼓励或者提醒。\n"
                    "专注力打分只能是 1 或 -1 或 -2，绝对不能输出用户的总分！\n"
                    "严格按照以下格式输出(不要用逗号分隔)：\n"
                    "score=1 context=\"概括窗口内容\" text=\"导师评价\""
                )

                # 6. 发送多模态请求 (适配全世界 99% 的 VLM)
                res = client.chat.completions.create(
                    model=provider_cfg["model_name"],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )

                # 7. 解析与存储
                raw = res.choices[0].message.content
                data = parse_llm_output(raw)
                
                self.current_score = max(0, min(200, self.current_score + data["score_change"]))
                self.ai_comment = data["comment"]

                self.history_data.append({
                    "time": timestamp_str,
                    "goal": self.user_goal,
                    "score": self.current_score,
                    "context": data["context"],
                    "comment": data["comment"],
                    "change": data["score_change"]
                })
                
            except Exception as e:
                print(f"Loop Error: {e}")
                self.ai_comment = f"API 连接异常，请检查网络或 Key..."

            # 8. 动态等待时间
            interval = cfg["settings"]["interval_seconds"]
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            for _ in range(int(sleep_time * 10)):
                if not self.is_running: break
                time.sleep(0.1)

# ================= 主程序启动 =================
if __name__ == '__main__':
    api = FocusApi()
    
    window = webview.create_window(
        'Focus OS',
        url=resource_path('gui/index.html'), 
        js_api=api,
        width=340, height=365,  
        resizable=False,
        frameless=True,         
        easy_drag=True,         
        on_top=True             
    )
    
    webview.start(debug=True)