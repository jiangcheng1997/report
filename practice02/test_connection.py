#!/usr/bin/env python3
"""
测试 LM Studio 连接
"""

import os
import json
import http.client
from urllib.parse import urlparse
import sys
import time

def load_dotenv():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")
    
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip("\"'")
    return env_vars

def test_connection():
    print("=== 测试 LM Studio 连接 ===", flush=True)
    
    env = load_dotenv()
    api_key = env.get("API_KEY", "dummy")
    base_url = env.get("BASE_URL")
    model_name = env.get("MODEL")
    
    print(f"BASE_URL: {base_url}", flush=True)
    print(f"MODEL: {model_name}", flush=True)
    print(f"API_KEY: {api_key}", flush=True)
    print("", flush=True)
    
    if not base_url or not model_name:
        print("错误：BASE_URL 或 MODEL 未配置", flush=True)
        return
    
    parsed_url = urlparse(base_url)
    host = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    path = parsed_url.path.rstrip("/") + "/chat/completions"
    
    print(f"连接到: {host}:{port}{path}", flush=True)
    print("", flush=True)
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        print("发送请求...", flush=True)
        if parsed_url.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=60)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=60)
        
        print(f"请求体: {json.dumps(payload, ensure_ascii=False)}", flush=True)
        
        start_time = time.time()
        conn.request("POST", path, body=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
        print("请求已发送，等待响应...", flush=True)
        
        response = conn.getresponse()
        elapsed_time = time.time() - start_time
        print(f"收到响应，耗时: {elapsed_time:.2f}秒", flush=True)
        
        print(f"响应状态码: {response.status}", flush=True)
        response_data = response.read().decode('utf-8')
        print(f"响应内容: {response_data}", flush=True)
        
        conn.close()
        
        if response.status == 200:
            result = json.loads(response_data)
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                print(f"\n连接成功！", flush=True)
                print(f"模型回复: {content}", flush=True)
            else:
                print(f"\n响应格式异常: {response_data}", flush=True)
        else:
            print(f"\n请求失败", flush=True)
            print(f"响应内容: {response_data}", flush=True)
        
    except Exception as e:
        print(f"\n连接错误: {e}", flush=True)
        print("\n可能的原因:", flush=True)
        print("1. LM Studio 服务未启动", flush=True)
        print("2. 端口号不正确（默认是 1234）", flush=True)
        print("3. 模型名称不正确", flush=True)
        print("4. 防火墙阻止了连接", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()
