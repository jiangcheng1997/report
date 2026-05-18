#!/usr/bin/env python3
"""
AnythingLLM 查询功能
功能：
1. 使用 subprocess 模块调用curl命令访问AnythingLLM的聊天API接口
2. 支持中文编码
3. 使用 message 字段发送查询
4. 使用密钥进行认证
5. 从.env文件读取ANYTHINGLLM_API_KEY、ANYTHINGLLM_WORKSPACE_SLUG变量
6. 支持错误处理
"""

import os
import subprocess
import json

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
            "ANYTHINGLLM_API_KEY": "",
            "ANYTHINGLLM_WORKSPACE_SLUG": ""
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
            "ANYTHINGLLM_API_KEY": "",
            "ANYTHINGLLM_WORKSPACE_SLUG": ""
        }
    return env_vars

def query_anythingllm(message):
    """查询AnythingLLM"""
    # 加载环境变量
    env = load_dotenv()
    
    # 获取配置
    api_key = env.get("ANYTHINGLLM_API_KEY", "")
    workspace_slug = env.get("ANYTHINGLLM_WORKSPACE_SLUG", "")
    
    # 检查必要的配置
    if not api_key:
        print("错误：请配置 .env 中的 ANYTHINGLLM_API_KEY")
        return None
    if not workspace_slug:
        print("错误：请配置 .env 中的 ANYTHINGLLM_WORKSPACE_SLUG")
        return None
    
    # 构建API URL
    api_url = f"http://localhost:3001/api/v1/workspace/{workspace_slug}/chat"
    
    # 构建请求数据
    payload = {
        "message": message
    }
    
    # 构建curl命令
    curl_command = [
        "curl",
        "-X", "POST",
        api_url,
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload, ensure_ascii=False)
    ]
    
    print(f"\n[调试] 执行命令: {' '.join(curl_command)}")
    
    try:
        # 执行curl命令，注意设置编码为utf-8
        result = subprocess.run(
            curl_command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30
        )
        
        # 检查返回码
        if result.returncode != 0:
            print(f"[错误] curl命令执行失败，返回码: {result.returncode}")
            print(f"[错误] 标准错误: {result.stderr}")
            return None
        
        # 解析响应
        try:
            response = json.loads(result.stdout)
            print(f"[调试] 响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
            # 为了保持一致性，将textResponse映射到response字段
            if "textResponse" in response:
                response["response"] = response["textResponse"]
            return response
        except json.JSONDecodeError as e:
            print(f"[错误] 解析响应失败: {e}")
            print(f"[错误] 原始响应: {result.stdout}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[错误] 请求超时")
        return None
    except Exception as e:
        print(f"[错误] 执行curl命令时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=== AnythingLLM 查询工具 ===")
    print("按 Ctrl+C 退出")
    print("==========================")
    
    try:
        while True:
            # 获取用户输入
            user_input = input("\n请输入查询内容: ").strip()
            if not user_input:
                continue
            
            # 调用AnythingLLM
            print("[正在查询...]")
            response = query_anythingllm(user_input)
            
            if response:
                # 显示响应结果
                if "response" in response:
                    print(f"\n[响应]: {response['response']}")
                elif "textResponse" in response:
                    print(f"\n[响应]: {response['textResponse']}")
                else:
                    print("\n[响应]: 未收到有效响应")
            else:
                print("\n[错误]: 查询失败")
    except KeyboardInterrupt:
        print("\n\n退出查询工具...")

if __name__ == "__main__":
    main()
