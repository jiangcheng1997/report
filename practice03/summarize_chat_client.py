#!/usr/bin/env python3
"""
OpenAI 兼容协议 LLM 聊天客户端（支持聊天记录总结和压缩）
功能：
1. 终端界面输入聊天内容
2. 支持流式输出（逐字显示）
3. 支持历史聊天记录自动添加到上下文
4. 当聊天历史超过5轮或上下文长度超过3k时，自动触发聊天记录总结
5. 对前70%左右的内容进行压缩，最后30%左右的内容保留原文
6. 直到用户按 Ctrl+C 退出终端
"""

import os
import json
import http.client
from urllib.parse import urlparse

def load_dotenv():
    """从项目根目录加载 .env 文件，返回字典"""
    # 获取项目根目录
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")
    
    env_vars = {}
    if not os.path.exists(env_path):
        print(f"警告: .env 文件不存在于 {env_path}")
        print("使用默认配置...")
        # 使用默认配置
        env_vars = {
            "BASE_URL": "http://localhost:1234/v1",
            "MODEL": "Qwen3.5-4b",
            "API_KEY": "lm-studio",
            "TEMPERATURE": "0.7",
            "MAX_TOKENS": "4096",
            "TIMEOUT": "30"
        }
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
        print(f"成功加载 .env 文件: {env_path}")
    except Exception as e:
        print(f"读取 .env 文件出错: {e}")
        # 使用默认配置
        print("使用默认配置...")
        env_vars = {
            "BASE_URL": "http://localhost:1234/v1",
            "MODEL": "Qwen3.5-4b",
            "API_KEY": "lm-studio",
            "TEMPERATURE": "0.7",
            "MAX_TOKENS": "4096",
            "TIMEOUT": "30"
        }
    return env_vars

def call_llm_stream(api_key, base_url, model, temperature, max_tokens, messages, timeout=30):
    """流式调用 LLM API"""
    # 解析 URL
    parsed_url = urlparse(base_url)
    
    host = parsed_url.hostname
    if not host:
        print("错误: 无法解析主机名")
        return None
    
    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    path = parsed_url.path.rstrip("/") + "/chat/completions"
    
    # 构建请求数据
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 发送请求
    try:
        if parsed_url.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        
        conn.request("POST", path, body=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
        response = conn.getresponse()
        
        # 处理流式响应
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

def summarize_chat_history(api_key, base_url, model, temperature, max_tokens, chat_history, timeout=30):
    """总结聊天历史记录"""
    print("\n[正在总结聊天记录...]")
    
    # 构建总结请求的消息
    summarize_messages = [
        {
            "role": "system",
            "content": "你是一个聊天记录总结助手，需要对以下聊天记录进行简洁的总结，保留主要内容和关键点。"
        },
        {
            "role": "user",
            "content": f"请对以下聊天记录进行总结：\n{json.dumps(chat_history, ensure_ascii=False)}"
        }
    ]
    
    # 调用LLM进行总结
    summary = call_llm_stream(api_key, base_url, model, temperature, max_tokens, summarize_messages, timeout)
    
    if summary:
        print("\n[聊天记录总结完成]")
        return summary
    else:
        print("\n[聊天记录总结失败]")
        return ""

def calculate_context_length(chat_history):
    """计算聊天上下文的长度"""
    total_length = 0
    for message in chat_history:
        if "content" in message:
            total_length += len(message["content"])
    return total_length

def main():
    print("=== LLM 聊天客户端（支持聊天记录总结和压缩）===")
    print("按 Ctrl+C 退出聊天")
    print("=============================================")
    
    # 加载环境变量
    env = load_dotenv()
    
    # 获取配置
    api_key = env.get("API_KEY", "dummy")
    base_url = env.get("BASE_URL")
    model_name = env.get("MODEL")
    temperature = float(env.get("TEMPERATURE", "0.7"))
    max_tokens = int(env.get("MAX_TOKENS", "2048"))
    timeout = int(env.get("TIMEOUT", "30"))

    # 检查必要的配置
    if not base_url or not model_name:
        print("错误：请配置 .env 中的 BASE_URL 和 MODEL")
        return

    print(f"API URL: {base_url}")
    print(f"模型名称: {model_name}")
    print()
    
    # 初始化聊天历史
    chat_history = []
    
    # 添加系统提示词
    system_prompt = "你是一个智能助手，能够回答用户的各种问题。"
    chat_history.append({"role": "system", "content": system_prompt})
    
    # 统计实际的聊天轮数（不包括系统消息和总结消息）
    chat_rounds = 0
    
    try:
        while True:
            # 获取用户输入
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            
            # 添加用户消息到聊天历史
            chat_history.append({"role": "user", "content": user_input})
            chat_rounds += 1
            
            # 检查是否需要总结聊天记录
            context_length = calculate_context_length(chat_history)
            if chat_rounds > 5 or context_length > 3000:
                # 对聊天历史进行处理：前70%压缩，后30%保留原文
                # 排除系统消息
                actual_chat = [msg for msg in chat_history if msg["role"] != "system" and not msg.get("content", "").startswith("[聊天记录总结]")]
                
                if len(actual_chat) > 0:
                    # 计算分割点
                    split_point = int(len(actual_chat) * 0.7)
                    
                    # 提取需要总结的部分和需要保留的部分
                    to_summarize = actual_chat[:split_point]
                    to_keep = actual_chat[split_point:]
                    
                    # 总结前70%的内容
                    summary = summarize_chat_history(api_key, base_url, model_name, temperature, max_tokens, to_summarize, timeout)
                    
                    if summary:
                        # 构建新的聊天历史：系统消息 + 总结 + 保留的部分
                        new_chat_history = [chat_history[0]]  # 保留系统消息
                        new_chat_history.append({"role": "assistant", "content": f"[聊天记录总结]\n{summary}"})
                        new_chat_history.extend(to_keep)
                        
                        # 更新聊天历史
                        chat_history = new_chat_history
                        chat_rounds = len([msg for msg in chat_history if msg["role"] == "user"])
                        print(f"[聊天记录已压缩，当前轮数: {chat_rounds}]")
            
            print("助手: ", end="", flush=True)
            
            # 调用LLM获取响应
            assistant_response = call_llm_stream(
                api_key, base_url, model_name, temperature, max_tokens, chat_history, timeout
            )
            
            if assistant_response:
                chat_history.append({"role": "assistant", "content": assistant_response})
            else:
                print("[无响应]", flush=True)
            
            print()
            
    except KeyboardInterrupt:
        print("\n\n退出聊天...")

if __name__ == "__main__":
    main()
