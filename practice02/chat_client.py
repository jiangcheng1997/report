#!/usr/bin/env python3
"""
OpenAI 兼容协议 LLM 聊天客户端（支持流式输出和历史记录）
适配 LM Studio
"""

import os
import json
import http.client
from urllib.parse import urlparse

def load_dotenv():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")

    env_vars = {}
    if not os.path.exists(env_path):
        print(f"错误: .env 文件不存在于 {env_path}")
        return env_vars

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip("\"'")
    except Exception as e:
        print(f"读取 .env 文件出错: {e}")
    return env_vars

def call_llm_stream(api_key, base_url, model, temperature, max_tokens, messages, timeout=30):
    parsed_url = urlparse(base_url)
    host = parsed_url.hostname
    if not host:
        print("错误: 无法解析主机名")
        return None

    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    path = parsed_url.path.rstrip("/") + "/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        if parsed_url.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("POST", path, body=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
        response = conn.getresponse()

        full_content = ""
        buffer = ""

        while True:
            chunk = response.read(4096)
            if not chunk:
                break

            try:
                buffer += chunk.decode("utf-8")
            except UnicodeDecodeError:
                continue

            # 处理缓冲区中的所有完整事件
            while "data:" in buffer:
                # 找到第一个 data: 的位置
                data_pos = buffer.find("data:")
                # 找到下一个 data: 或者字符串结束
                next_data_pos = buffer.find("data:", data_pos + 5)

                if next_data_pos == -1:
                    # 没有下一个 data:，检查是否有完整的 JSON
                    json_str = buffer[data_pos:]
                    # 尝试找到 [DONE] 或 JSON 结束
                    if "[DONE]" in json_str:
                        # [DONE] 消息，解析到那里
                        json_str = json_str[:json_str.find("[DONE]")].strip()
                        if json_str:
                            try:
                                data = json.loads(json_str[5:].strip())
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        content = delta["content"]
                                        print(content, end="", flush=True)
                                        full_content += content
                            except json.JSONDecodeError:
                                pass
                        break
                    else:
                        # JSON 可能不完整，等待更多数据
                        break
                else:
                    # 有下一个 data:，解析当前的数据
                    json_str = buffer[data_pos:next_data_pos].strip()
                    if json_str.startswith("data:"):
                        json_str = json_str[5:].strip()
                        if json_str and json_str != "[DONE]":
                            try:
                                data = json.loads(json_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        content = delta["content"]
                                        print(content, end="", flush=True)
                                        full_content += content
                            except json.JSONDecodeError:
                                pass
                    buffer = buffer[next_data_pos:]

        conn.close()
        return full_content

    except Exception as e:
        print(f"\n错误: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()
        return None

def main():
    print("=== LLM 聊天客户端（LM Studio 适配版）===")
    print("按 Ctrl+C 退出")
    print("="*40)

    env = load_dotenv()
    api_key = env.get("API_KEY", "dummy")
    base_url = env.get("BASE_URL")
    model_name = env.get("MODEL")
    temperature = float(env.get("TEMPERATURE", "0.7"))
    max_tokens = int(env.get("MAX_TOKENS", "2048"))

    if not base_url or not model_name:
        print("错误：请配置 .env 中的 BASE_URL 和 MODEL")
        return

    chat_history = []

    try:
        while True:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue

            chat_history.append({"role": "user", "content": user_input})
            if len(chat_history) > 10:
                chat_history = chat_history[-10:]

            print("助手: ", end="", flush=True)
            res = call_llm_stream(api_key, base_url, model_name, temperature, max_tokens, chat_history)
            if res:
                chat_history.append({"role": "assistant", "content": res})
            else:
                print("[无响应]", flush=True)

    except KeyboardInterrupt:
        print("\n\n退出聊天～")

if __name__ == "__main__":
    main()
