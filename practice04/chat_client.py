#!/usr/bin/env python3
"""
OpenAI 兼容协议 LLM 聊天客户端（支持工具调用）
功能：
1. 终端界面输入聊天内容
2. 支持流式输出（逐字显示）
3. 支持历史聊天记录自动添加到上下文
4. 支持工具调用功能（文件操作、网络访问和AnythingLLM查询）
5. 直到用户按 Ctrl+C 退出终端
"""

import os
import json
import http.client
import time
from urllib.parse import urlparse

# 导入文件操作工具
from file_tools import list_files, rename_file, delete_file, create_file, read_file, curl
# 导入AnythingLLM查询工具
from anythingllm_query import query_anythingllm

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

def execute_tool(tool_call):
    """执行工具调用"""
    try:
        # 验证工具调用结构
        if not isinstance(tool_call, dict):
            return {
                "status": "error",
                "message": "工具调用结构错误: 不是字典类型"
            }
        
        if "function" not in tool_call:
            return {
                "status": "error",
                "message": "工具调用结构错误: 缺少function字段"
            }
        
        function = tool_call["function"]
        if not isinstance(function, dict):
            return {
                "status": "error",
                "message": "工具调用结构错误: function不是字典类型"
            }
        
        if "name" not in function:
            return {
                "status": "error",
                "message": "工具调用结构错误: 缺少name字段"
            }
        
        function_name = function["name"]

        # ====================== 核心修复 ======================
        # 处理不同格式的arguments
        arguments = function.get("arguments", {})
        # 如果arguments是字符串，尝试解析为JSON
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
                # 确保解析后是字典类型
                if not isinstance(arguments, dict):
                    arguments = {}
            except json.JSONDecodeError:
                # 如果解析失败，使用空字典
                arguments = {}
        # 确保arguments是字典类型
        if not isinstance(arguments, dict):
            arguments = {}
        # ======================================================
        
        print(f"执行工具: {function_name}")
        print(f"解析后的参数: {arguments}")
        
        if function_name == "list_files":
            directory = arguments.get("directory")
            if not directory:
                return {
                    "status": "error",
                    "message": "缺少必要参数: directory"
                }
            result = list_files(directory)
        elif function_name == "rename_file":
            directory = arguments.get("directory")
            old_name = arguments.get("old_name")
            new_name = arguments.get("new_name")
            if not all([directory, old_name, new_name]):
                return {
                    "status": "error",
                    "message": "缺少必要参数: directory, old_name, new_name"
                }
            result = rename_file(directory, old_name, new_name)
        elif function_name == "delete_file":
            directory = arguments.get("directory")
            file_name = arguments.get("file_name")
            if not all([directory, file_name]):
                return {
                    "status": "error",
                    "message": "缺少必要参数: directory, file_name"
                }
            result = delete_file(directory, file_name)
        elif function_name == "create_file":
            directory = arguments.get("directory")
            file_name = arguments.get("file_name")
            content = arguments.get("content", "")
            if not all([directory, file_name]):
                return {
                    "status": "error",
                    "message": "缺少必要参数: directory, file_name"
                }
            result = create_file(directory, file_name, content)
        elif function_name == "read_file":
            directory = arguments.get("directory")
            file_name = arguments.get("file_name")
            if not all([directory, file_name]):
                return {
                    "status": "error",
                    "message": "缺少必要参数: directory, file_name"
                }
            result = read_file(directory, file_name)
        elif function_name == "curl":
            url = arguments.get("url")
            if not url:
                return {
                    "status": "error",
                    "message": "缺少必要参数: url"
                }
            # 清理URL，移除多余的空格、反引号、花括号等
            url = url.strip()
            # 移除各种引号和括号
            for char in ['`', '"', "'", '{', '}', '[', ']', '(', ')']:
                url = url.replace(char, '')
            # 智能提取URL - 寻找http://或https://开头的部分
            import re
            url_match = re.search(r'(https?://[^\s]+)', url)
            if url_match:
                url = url_match.group(1)
            if not url:
                return {
                    "status": "error",
                    "message": "无效的URL"
                }
            # 处理可选参数
            method = arguments.get("method", "GET")
            headers = arguments.get("headers", None)
            data = arguments.get("data", None)
            result = curl(url, method, headers, data)
        elif function_name == "anythingllm_query":
            message = arguments.get("message")
            if not message:
                return {
                    "status": "error",
                    "message": "缺少必要参数: message"
                }
            result = query_anythingllm(message)
            if result:
                # 检查API返回的响应是否包含错误信息
                response_content = result.get("response", "")
                if "error" in response_content.lower() or "failed" in response_content.lower():
                    result = {
                        "status": "error",
                        "message": f"API返回错误: {response_content}"
                    }
                else:
                    result = {
                        "status": "success",
                        "message": "查询成功",
                        "response": response_content
                    }
            else:
                result = {
                    "status": "error",
                    "message": "查询失败"
                }
        else:
            result = {
                "status": "error",
                "message": f"未知工具: {function_name}"
            }
        
        try:
            # 尝试打印结果，处理Unicode编码错误
            print(f"工具执行结果: {result}")
        except UnicodeEncodeError:
            # 如果遇到编码错误，简化打印
            print(f"工具执行结果: {{'status': '{result.get('status')}', 'message': '{result.get('message')}'}}")
        return result
    except Exception as e:
        print(f"执行工具时出错: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"执行工具失败: {str(e)}"
        }

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
    
    # 工具列表
    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "列出指定目录下的所有文件及其属性",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        }
                    },
                    "required": ["directory"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "rename_file",
                "description": "修改指定目录下的文件名字",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "old_name": {
                            "type": "string",
                            "description": "原文件名"
                        },
                        "new_name": {
                            "type": "string",
                            "description": "新文件名"
                        }
                    },
                    "required": ["directory", "old_name", "new_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_file",
                "description": "删除指定目录下的文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "文件名"
                        }
                    },
                    "required": ["directory", "file_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "在指定目录下新建文件并写入内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "文件名"
                        },
                        "content": {
                            "type": "string",
                            "description": "文件内容"
                        }
                    },
                    "required": ["directory", "file_name", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取指定目录下的文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "文件名"
                        }
                    },
                    "required": ["directory", "file_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "curl",
                "description": "网络访问功能，模拟curl命令访问网页并返回内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "要访问的URL"
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP方法，默认为GET"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP请求头"
                        },
                        "data": {
                            "type": "string",
                            "description": "HTTP请求体数据"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "anythingllm_query",
                "description": "查询AnythingLLM文档仓库，获取文档信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "查询内容"
                        }
                    },
                    "required": ["message"]
                }
            }
        }
    ]
    
    # 构建请求数据
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "tools": tools,
        "tool_choice": "auto"
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
        tool_calls = []
        
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
                                        # 检查content是否包含工具调用格式
                                        content_stripped = content.strip()
                                        if (content_stripped.startswith('{') and 
                                            ('id' in content_stripped.lower() or '"id"' in content_stripped) and 
                                            ('type' in content_stripped.lower() or '"type"' in content_stripped) and 
                                            ('function' in content_stripped.lower() or '"function"' in content_stripped)):
                                            # 这是工具调用格式，不输出给用户，只添加到tool_calls
                                            try:
                                                tool_call = json.loads(content)
                                                if "function" in tool_call:
                                                    tool_calls.append(tool_call)
                                            except json.JSONDecodeError:
                                                # 如果不是有效的JSON，就输出
                                                print(content, end="", flush=True)
                                                full_content += content
                                        else:
                                            print(content, end="", flush=True)
                                            full_content += content
                                    elif "tool_calls" in delta:
                                        tool_calls.extend(delta["tool_calls"])
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
                                        # 检查content是否包含工具调用格式
                                        content_stripped = content.strip()
                                        if (content_stripped.startswith('{') and 
                                            ('id' in content_stripped.lower() or '"id"' in content_stripped) and 
                                            ('type' in content_stripped.lower() or '"type"' in content_stripped) and 
                                            ('function' in content_stripped.lower() or '"function"' in content_stripped)):
                                            # 这是工具调用格式，不输出给用户，只添加到tool_calls
                                            try:
                                                tool_call = json.loads(content)
                                                if "function" in tool_call:
                                                    tool_calls.append(tool_call)
                                            except json.JSONDecodeError:
                                                # 如果不是有效的JSON，就输出
                                                print(content, end="", flush=True)
                                                full_content += content
                                        else:
                                            print(content, end="", flush=True)
                                            full_content += content
                                    elif "tool_calls" in delta:
                                        tool_calls.extend(delta["tool_calls"])
                            except json.JSONDecodeError:
                                pass
                    buffer = buffer[next_data_pos:]
        
        conn.close()
        
        # 检查完整的content是否是工具调用格式
        if full_content.strip():
            content_stripped = full_content.strip()
            if (content_stripped.startswith('{') and 
                ('id' in content_stripped.lower() or '"id"' in content_stripped) and 
                ('type' in content_stripped.lower() or '"type"' in content_stripped) and 
                ('function' in content_stripped.lower() or '"function"' in content_stripped)):
                # 这是工具调用格式，尝试解析为JSON
                try:
                    tool_call = json.loads(full_content)
                    if "function" in tool_call:
                        # 清空full_content，不输出给用户
                        full_content = ""
                        # 执行工具调用
                        try:
                            # 生成默认的tool_call_id
                            tool_call_id = tool_call.get("id", f"tool_{int(time.time() * 1000)}")
                            function_name = tool_call["function"]["name"]
                            
                            tool_result = execute_tool(tool_call)
                            # 检查工具执行结果
                            if tool_result.get("status") == "error":
                                error_message = tool_result.get("message", "工具执行失败")
                                print(f"\n助手: {error_message}")
                                return error_message
                            
                            # 工具执行成功，将结果添加到消息历史
                            messages.append({
                                "role": "assistant",
                                "tool_calls": [tool_call]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "name": function_name,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                            # 再次调用 LLM 获取最终响应
                            print("\n等待 LLM 处理工具执行结果...")
                            full_content = call_llm_stream(
                                api_key, base_url, model, temperature, max_tokens, messages, timeout
                            )
                            return full_content
                        except Exception as e:
                            print(f"处理工具调用时出错: {e}")
                            import traceback
                            traceback.print_exc()
                            print("\n助手: 处理工具调用时出错，请重新尝试。")
                            return ""
                except json.JSONDecodeError:
                    # 如果不是有效的JSON，就输出
                    pass
        
        # 处理工具调用
        if tool_calls:
            for tool_call in tool_calls:
                try:
                    # 生成默认的tool_call_id
                    tool_call_id = tool_call.get("id", f"tool_{int(time.time() * 1000)}")
                    function_name = tool_call["function"]["name"]
                    
                    tool_result = execute_tool(tool_call)
                    # 检查工具执行结果
                    if tool_result.get("status") == "error":
                        error_message = tool_result.get("message", "工具执行失败")
                        print(f"\n助手: {error_message}")
                        return error_message
                    
                    # 工具执行成功，将结果添加到消息历史
                    messages.append({
                        "role": "assistant",
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": function_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                    # 再次调用 LLM 获取最终响应
                    print("\n等待 LLM 处理工具执行结果...")
                    full_content = call_llm_stream(
                        api_key, base_url, model, temperature, max_tokens, messages, timeout
                    )
                    return full_content
                except Exception as e:
                    print(f"处理工具调用时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    print("\n助手: 处理工具调用时出错，请重新尝试。")
                    return ""
        
        return full_content
        
    except Exception as e:
        print(f"\n错误: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()
        return None

def main():
    print("=== LLM 聊天客户端（支持工具调用）===")
    print("按 Ctrl+C 退出聊天")
    print("=====================================")
    
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
    system_prompt = """你是一个智能助手，能够使用以下工具来执行各种操作：

工具列表：
1. curl(url, method="GET", headers=None, data=None): 网络访问功能，模拟curl命令访问网页并返回内容
2. anythingllm_query(message): 查询AnythingLLM文档仓库，获取文档信息

当用户请求与网络访问相关的任务时，请使用curl工具来完成。
当用户提到"文档仓库"、"文件仓库"、"数据仓库"、"仓库"等词汇时，请使用anythingllm_query工具来查询文档仓库中的信息。

请严格按照以下格式生成工具调用：
{
  "id": "tool_call_1",
  "type": "function",
  "function": {
    "name": "工具名称",
    "arguments": {
      "参数名": "参数值"
    }
  }
}

重要提示：
- 提取URL时，请只提取实际的URL部分，不要包含"url"、"URL"等前缀
- 清理URL中的特殊字符，如空格、引号、花括号等
- 确保URL格式正确，包含协议（http://或https://）
- 对于天气查询，请使用wttr.in或tianqi.com等可靠的天气网站
- 对于文档仓库查询，请使用anythingllm_query工具，并在message参数中包含完整的查询内容

示例：
- 用户问"通过访问 http://wttr.in/青城山，帮我查看明天的天气"，你应该生成：
{
  "id": "tool_call_1",
  "type": "function",
  "function": {
    "name": "curl",
    "arguments": {
      "url": "http://wttr.in/青城山"
    }
  }
}
- 用户问"文档仓库中有什么内容"，你应该生成：
{
  "id": "tool_call_1",
  "type": "function",
  "function": {
    "name": "anythingllm_query",
    "arguments": {
      "message": "文档仓库中有什么内容"
    }
  }
}
- 用户问"仓库里的文件都有哪些"，你应该生成：
{
  "id": "tool_call_1",
  "type": "function",
  "function": {
    "name": "anythingllm_query",
    "arguments": {
      "message": "仓库里的文件都有哪些"
    }
  }
}
- 用户问"数据仓库中上传了什么内容"，你应该生成：
{
  "id": "tool_call_1",
  "type": "function",
  "function": {
    "name": "anythingllm_query",
    "arguments": {
      "message": "数据仓库中上传了什么内容"
    }
  }
}

请确保工具调用的参数格式正确，特别是curl工具的url参数必须是完整的URL，anythingllm_query工具的message参数必须是完整的查询内容。"""

    chat_history.append({"role": "system", "content": system_prompt})
    
    try:
        while True:
            # 获取用户输入
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            
            chat_history.append({"role": "user", "content": user_input})
            
            if len(chat_history) > 15:
                chat_history = chat_history[-15:]
            
            print("助手: ", end="", flush=True)
            
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
