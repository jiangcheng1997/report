#!/usr/bin/env python3
"""
OpenAI 兼容协议 LLM 聊天客户端（支持技能调用）
功能：
1. 终端界面输入聊天内容
2. 支持流式输出（逐字显示）
3. 支持历史聊天记录自动添加到上下文
4. 支持工具调用功能（文件操作、网络访问和AnythingLLM查询）
5. 支持技能读取和加载功能
6. 直到用户按 Ctrl+C 退出终端
7. 支持意图识别，自动触发技能加载
"""

import os
import json
import http.client
import time
import re
from datetime import datetime
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

def list_available_skills():
    """读取技能列表
    读取项目目录下 .agents/skills 目录下的所有一级子目录，
    读取每个子目录内SKILL.md文件的 YAML front matter，
    提取 name 和 description 字段。
    """
    # 获取项目根目录
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(script_dir)
    skills_dir = os.path.join(project_root, ".agents", "skills")
    
    skills = []
    
    if os.path.exists(skills_dir) and os.path.isdir(skills_dir):
        # 遍历所有一级子目录
        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name)
            if os.path.isdir(skill_path):
                # 检查SKILL.md文件是否存在
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    try:
                        with open(skill_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        # 提取YAML front matter
                        if content.startswith("---"):
                            end_index = content.find("---", 3)
                            if end_index != -1:
                                front_matter = content[3:end_index].strip()
                                # 解析YAML front matter
                                name = None
                                description = None
                                for line in front_matter.split("\n"):
                                    line = line.strip()
                                    if line.startswith("name:"):
                                        name = line.split(":", 1)[1].strip()
                                    elif line.startswith("description:"):
                                        description = line.split(":", 1)[1].strip()
                                if name:
                                    skills.append({"name": name, "description": description or ""})
                    except Exception as e:
                        print(f"读取技能 {skill_name} 出错: {e}")
    
    return skills

def load_skill_content(skill_name):
    """加载技能正文内容
    加载指定技能的SKILL.md文件正文内容（YAML front matter 之后的部分）
    """
    # 获取项目根目录
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(script_dir)
    skill_path = os.path.join(project_root, ".agents", "skills", skill_name)
    skill_file = os.path.join(skill_path, "SKILL.md")
    
    if os.path.exists(skill_file):
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
            # 提取正文内容（YAML front matter 之后的部分）
            if content.startswith("---"):
                end_index = content.find("---", 3)
                if end_index != -1:
                    return content[end_index+3:].strip()
            return content
        except Exception as e:
            print(f"加载技能 {skill_name} 内容出错: {e}")
            return ""
    else:
        print(f"技能 {skill_name} 不存在")
        return ""

def detect_intent_and_load_skill(user_input):
    """检测用户意图，自动加载相应技能
    返回: (skill_content, department) 或 (None, None)
    """
    user_input_lower = user_input.lower()
    
    # 检测通知相关意图
    notice_patterns = [
        r"撰写.*通知",
        r"写.*通知",
        r"起草.*通知",
        r"生成.*通知",
        r"关于.*放假.*通知",
        r"关于.*假期.*通知",
        r"放假通知",
        r"假期通知",
        r"通知.*撰写",
        r"通知.*写",
        r"帮我.*通知",
    ]
    
    for pattern in notice_patterns:
        if re.search(pattern, user_input_lower):
            # 提取部门信息
            department = None
            # 匹配 "我是XX部" 或 "XX部" 的模式
            dept_patterns = [
                r"我是['\"]?([^'\"的部]+部)",
                r"属于['\"]?([^'\"的部]+部)",
                r"([^我、，,\s]+部)",
            ]
            for dept_pattern in dept_patterns:
                match = re.search(dept_pattern, user_input)
                if match:
                    department = match.group(1).strip()
                    # 清理常见的干扰词
                    department = department.replace("我是", "").replace("属于", "").strip()
                    break
            
            # 如果没提取到部门，使用默认值
            if not department:
                department = "XX部"
            
            # 加载 notice 技能
            skill_content = load_skill_content("notice")
            if skill_content:
                return skill_content, department
    
    return None, None

def generate_notice_with_llm(skill_content, department, user_input, api_key, base_url, model_name, temperature, max_tokens, timeout=60):
    """使用 LLM API 生成通知（流式输出）"""
    # 提取用户需求中的具体内容
    content_detail = ""
    content_match = re.search(r"内容为(.+?)(?:。|$)", user_input)
    if not content_match:
        content_match = re.search(r"内容是(.+?)(?:。|$)", user_input)
    if content_match:
        content_detail = content_match.group(1).strip()
    
    # 如果没有提取到具体内容，使用默认描述
    if not content_detail:
        content_detail = "全体同学放假"
    
    # 获取当前日期
    today = datetime.now().strftime("%Y年%m月%d日")
    
    # 构建提示词，让 LLM 根据技能内容生成通知
    prompt = f"""请根据以下技能要求，生成一份正式的通知：

技能内容（模板和格式要求）：
{skill_content}

用户需求：
- 部门：{department}
- 通知主题：五一节放假
- 具体安排：{content_detail}
- 当前日期：{today}

请严格按照以下要求生成通知：
1. 通知必须以"{department}"开头，不能以"通知"二字开头
2. 必须包含：标题、正文、落款（部门名称和日期）
3. 正文需要包含：放假时间、具体安排、注意事项
4. 放假时间假设为2025年5月1日至5月5日
5. 格式规范、语言正式、条理清晰

请直接输出通知内容，不要添加"以下是通知"等额外说明："""
    
    # 临时创建消息历史来调用 LLM
    temp_messages = [
        {"role": "system", "content": "你是一个专业的通知撰写助手，严格按照格式要求输出正式、规范的通知内容。"},
        {"role": "user", "content": prompt}
    ]
    
    # 解析 URL
    parsed_url = urlparse(base_url)
    host = parsed_url.hostname
    if not host:
        return "错误: 无法解析主机名"
    
    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    path = parsed_url.path.rstrip("/") + "/chat/completions"
    
    # 构建请求数据（使用流式）
    payload = {
        "model": model_name,
        "messages": temp_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    print(f"正在连接 LLM API 生成通知...")
    
    try:
        if parsed_url.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        
        conn.request("POST", path, body=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
        response = conn.getresponse()
        
        if response.status != 200:
            error_msg = response.read().decode('utf-8')
            conn.close()
            print(f"\nAPI 返回错误状态码 {response.status}，使用模板生成...")
            return None  # 返回 None，让调用方使用模板
        
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
            
            # 处理 SSE 数据
            while "data:" in buffer:
                data_pos = buffer.find("data:")
                next_data_pos = buffer.find("data:", data_pos + 5)
                
                if next_data_pos == -1:
                    json_str = buffer[data_pos:]
                    if "[DONE]" in json_str:
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
                        # JSON 不完整，等待更多数据
                        break
                else:
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
        print()  # 换行
        
        if full_content.strip():
            return full_content
        else:
            print("LLM 返回空内容，使用模板生成...")
            return None
            
    except TimeoutError:
        print(f"\nLLM API 请求超时（{timeout}秒），使用模板生成...")
        return None
    except Exception as e:
        print(f"\n调用 LLM API 时出错: {e}，使用模板生成...")
        return None

def generate_notice_template(department, user_input):
    """快速生成通知模板（不调用LLM，作为备用方案）"""
    # 提取具体内容
    content_detail = ""
    content_match = re.search(r"内容为(.+?)(?:。|$)", user_input)
    if not content_match:
        content_match = re.search(r"内容是(.+?)(?:。|$)", user_input)
    if content_match:
        content_detail = content_match.group(1).strip()
    
    # 如果没有提取到具体内容，使用默认描述
    if not content_detail:
        content_detail = "全体同学放假"
    
    # 生成当前日期
    today = datetime.now().strftime("%Y年%m月%d日")
    
    notice = f"""{department}通知

根据五一节放假安排，现将有关事宜通知如下：

一、放假时间
   2025年5月1日至5月5日（共5天）

二、放假安排
   {content_detail}

三、注意事项
   1. 请各位同学注意假期安全
   2. 妥善保管个人物品
   3. 按时返校上课

特此通知

{department}
{today}"""
    
    return notice

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
        elif function_name == "load_skill_content":
            skill_name = arguments.get("skill_name")
            if not skill_name:
                return {
                    "status": "error",
                    "message": "缺少必要参数: skill_name"
                }
            content = load_skill_content(skill_name)
            result = {
                "status": "success",
                "message": "加载技能内容成功",
                "content": content
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
        },
        {
            "type": "function",
            "function": {
                "name": "load_skill_content",
                "description": "加载指定技能的内容，用于执行技能相关的任务",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "技能名称"
                        }
                    },
                    "required": ["skill_name"]
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
    print("=== LLM 聊天客户端（支持技能调用 + LLM智能生成通知）===")
    print("按 Ctrl+C 退出聊天")
    print("========================================================")
    
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
    print("已启用意图识别：自动检测通知请求并调用 LLM 智能生成")
    print()
    
    # 初始化聊天历史
    chat_history = []
    
    # 读取技能列表
    skills = list_available_skills()
    skills_json = json.dumps({"skills": skills}, ensure_ascii=False, indent=2)
    
    # 添加系统提示词
    system_prompt = f"""你是一个智能助手，能够使用以下工具来执行各种操作：

工具列表：
1. curl(url, method="GET", headers=None, data=None): 网络访问功能，模拟curl命令访问网页并返回内容
2. anythingllm_query(message): 查询AnythingLLM文档仓库，获取文档信息

可用技能：
{skills_json}

重要提示：
- 提取URL时，请只提取实际的URL部分，不要包含"url"、"URL"等前缀
- 清理URL中的特殊字符，如空格、引号、花括号等
- 确保URL格式正确，包含协议（http://或https://）
- 对于天气查询，请使用wttr.in或tianqi.com等可靠的天气网站
- 对于文档仓库查询，请使用anythingllm_query工具

请直接回答用户的问题。"""

    chat_history.append({"role": "system", "content": system_prompt})
    
    try:
        while True:
            # 获取用户输入
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            
            # === 意图识别：检测是否需要生成通知 ===
            skill_content, department = detect_intent_and_load_skill(user_input)
            
            if skill_content and department:
                # 需要生成通知，优先使用 LLM 生成，失败时降级到模板
                print("检测到通知请求，正在调用 LLM 智能生成通知...")
                print("\n助手: ", end="", flush=True)
                
                notice = generate_notice_with_llm(
                    skill_content, department, user_input,
                    api_key, base_url, model_name, temperature, max_tokens, timeout=60
                )
                
                if notice is None:
                    # LLM 生成失败，使用模板
                    print("\n使用备用模板生成通知...")
                    notice = generate_notice_template(department, user_input)
                    print(notice)
                else:
                    # notice 已经通过流式输出打印过了，不需要再打印
                    pass
                
                # 将对话添加到历史
                chat_history.append({"role": "user", "content": user_input})
                chat_history.append({"role": "assistant", "content": notice if notice else "通知生成失败"})
                
                # 限制历史长度
                if len(chat_history) > 15:
                    chat_history = [chat_history[0]] + chat_history[-14:]
                print()
                continue
            
            # === 正常聊天流程 ===
            # 每次用户提交输入时，重新读取技能列表
            skills = list_available_skills()
            skills_json = json.dumps({"skills": skills}, ensure_ascii=False, indent=2)
            
            # 更新系统提示词中的技能列表
            system_prompt = f"""你是一个智能助手，能够使用以下工具来执行各种操作：

工具列表：
1. curl(url, method="GET", headers=None, data=None): 网络访问功能，模拟curl命令访问网页并返回内容
2. anythingllm_query(message): 查询AnythingLLM文档仓库，获取文档信息

可用技能：
{skills_json}

重要提示：
- 提取URL时，请只提取实际的URL部分，不要包含"url"、"URL"等前缀
- 清理URL中的特殊字符，如空格、引号、花括号等
- 确保URL格式正确，包含协议（http://或https://）
- 对于天气查询，请使用wttr.in或tianqi.com等可靠的天气网站
- 对于文档仓库查询，请使用anythingllm_query工具

请直接回答用户的问题。"""
            
            # 更新聊天历史中的系统提示词
            chat_history[0] = {"role": "system", "content": system_prompt}
            chat_history.append({"role": "user", "content": user_input})
            
            if len(chat_history) > 15:
                chat_history = [chat_history[0]] + chat_history[-14:]
            
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