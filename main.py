import os
import io
import json
import csv
import time
import threading
import re
import sys
import base64
import webview
from openai import OpenAI
from datetime import datetime
from PIL import Image, ImageGrab
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

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
        self.default_config = {
            "current_provider": "dashscope",
            "providers": {
                "dashscope": {"name": "阿里通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model_name": "qwen-vl-plus", "api_key": ""},
                "doubao": {"name": "字节豆包", "base_url": "https://ep.api.vanguards.volces.com/api/v3", "model_name": "ep-xxxxxx", "api_key": ""},
                "openai": {"name": "OpenAI 官方", "base_url": "https://api.openai.com/v1", "model_name": "gpt-4o", "api_key": ""},
                "ollama": {"name": "本地部署 (Ollama)", "base_url": "http://localhost:11434/v1", "model_name": "llava", "api_key": "ollama"}
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
    text_match = re.search(r'\btext\s*=\s*["\'](.*?)["\']', raw_text)
    if text_match: result["comment"] = text_match.group(1)

    return result

# ================= 核心组件 1：FocusEngine (纯后台大脑) =================
class FocusEngine:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.is_running = False
        self.user_goal = "高效工作"
        self.current_score = 100
        self.ai_comment = "Focus OS 已就绪"
        self.history_data = []
        self._monitor_thread = None

    def start(self, goal=None):
        if not self.is_running:
            self.is_running = True
            if goal: self.user_goal = goal
            self._monitor_thread = threading.Thread(target=self._worker_loop)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()

    def stop(self):
        self.is_running = False

    def update_goal(self, new_goal):
        if new_goal and new_goal.strip():
            self.user_goal = new_goal.strip()

    def get_status(self):
        return {
            "score": self.current_score,
            "comment": self.ai_comment,
            "running": self.is_running,
            "current_goal": self.user_goal
        }

    def generate_report(self):
        if not self.history_data:
            return {"msg": "暂无数据可生成"}
        
        base_dir = self.config_manager.config["settings"]["save_dir"]
        today_folder = datetime.now().strftime('%y%m%d')
        save_dir = os.path.join(base_dir, today_folder)
        if not os.path.exists(save_dir): os.makedirs(save_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(save_dir, f"report_{timestamp}.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "goal", "score", "context", "comment", "change"])
            writer.writeheader()
            writer.writerows(self.history_data)
        
        return {"msg": f"报表已保存至: {csv_path}", "path": csv_path}

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
                screen = ImageGrab.grab()
                compressed = compress_image(screen)
                
                if cfg["settings"]["save_images"]:
                    img_path = os.path.join(save_dir, f"{file_timestamp}.jpg")
                    with open(img_path, "wb") as f: f.write(compressed.getvalue())

                base64_image = base64.b64encode(compressed.getvalue()).decode('utf-8')

                client = OpenAI(
                    api_key=provider_cfg["api_key"],
                    base_url=provider_cfg["base_url"] if provider_cfg["base_url"] else None
                )

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

                res = client.chat.completions.create(
                    model=provider_cfg["model_name"],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                    ],
                    max_tokens=300
                )

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

            interval = cfg["settings"]["interval_seconds"]
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            for _ in range(int(sleep_time * 10)):
                if not self.is_running: break
                time.sleep(0.1)

# ================= 核心组件 2：FocusApi (GUI 专属前台客服) =================
class FocusApi:
    def __init__(self, engine: FocusEngine):
        self.engine = engine  

    def get_settings(self):
        return self.engine.config_manager.config

    def save_settings(self, new_settings):
        self.engine.config_manager.save_config(new_settings)
        return {"status": "success", "msg": "设置已保存！"}

    def start_monitor(self, goal):
        cfg = self.engine.config_manager.config
        provider = cfg["current_provider"]
        api_key = cfg["providers"][provider]["api_key"]
        if not api_key: return {"status": "error", "msg": f"请先在设置中配置 {provider} 的 API Key！"}
        self.engine.start(goal)
        return {"status": "started"}

    def stop_monitor(self):
        self.engine.stop()
        return {"status": "stopped"}

    def update_goal(self, new_goal):
        self.engine.update_goal(new_goal)
        return {"status": "updated", "goal": self.engine.user_goal}

    def get_status(self):
        return self.engine.get_status()

    def generate_report(self):
        return self.engine.generate_report()

# ================= 核心组件 3：Agent API 服务 (纯本地 HTTP) =================
class AgentAPIHandler(BaseHTTPRequestHandler):
    engine: FocusEngine = None  # 静态挂载核心大脑

    def _send_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    # 静默日志，防止控制台被刷屏
    def log_message(self, format, *args): pass 

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/focus/score':
            self._send_response(self.engine.get_status())
        elif parsed.path == '/api/history':
            self._send_response({"history": self.engine.history_data})
        else:
            self._send_response({"error": "Not Found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8')) if post_data else {}

        if parsed.path == '/api/start':
            goal = data.get('goal', self.engine.user_goal)
            self.engine.start(goal)
            self._send_response({"status": "started", "goal": self.engine.user_goal})
        elif parsed.path == '/api/stop':
            self.engine.stop()
            self._send_response({"status": "stopped"})
        elif parsed.path == '/api/goal':
            self.engine.update_goal(data.get('goal', ''))
            self._send_response({"status": "goal_updated", "goal": self.engine.user_goal})
        elif parsed.path == '/api/config':
            self.engine.config_manager.save_config(data)
            self._send_response({"status": "config_updated"})
        else:
            self._send_response({"error": "Not Found"}, 404)

def run_agent_server(engine: FocusEngine, port=8765):
    AgentAPIHandler.engine = engine
    server = HTTPServer(('127.0.0.1', port), AgentAPIHandler)
    print(f"\n[🚀 Agent API 就绪] OpenClaw 可通过 http://127.0.0.1:{port}/api/* 进行调用\n")
    server.serve_forever()


# =================== 主程序启动 ===================
if __name__ == '__main__':
    core_engine = FocusEngine()
    gui_api = FocusApi(core_engine)
    
    # 启动供 Agent 调用的后台本地服务器线程 (端口 8765)
    api_thread = threading.Thread(target=run_agent_server, args=(core_engine, 8765))
    api_thread.daemon = True
    api_thread.start()
    
    # 启动图形界面
    window = webview.create_window(
        'Focus OS', url=resource_path('gui/index.html'), js_api=gui_api,
        width=340, height=365, resizable=False, frameless=True, easy_drag=True, on_top=True             
    )
    webview.start(debug=False)#默认关闭，可选打开以便debug