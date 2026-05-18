import os
import json
import time
import http.client
from urllib.parse import urlparse

# 读取.env文件
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"')
    return env_vars

# 主函数
def main():
    # 加载环境变量
    env = load_env()
    base_url = env.get('BASE_URL', 'https://api.openai.com/v1')
    model = env.get('MODEL', 'gpt-4o')
    api_key = env.get('API_KEY', '')
    temperature = float(env.get('TEMPERATURE', '0.7'))
    max_tokens = int(env.get('MAX_TOKENS', '1000'))
    
    if not api_key:
        print("Error: API_KEY not found in .env file")
        return
    
    # 解析URL
    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path or '/'
    
    # 构建请求数据
    prompt = "Write a short paragraph about AI agents"
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 创建HTTP连接
        conn = http.client.HTTPSConnection(host, timeout=30)
        
        # 构建请求头
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # 发送请求
        conn.request('POST', f"{path}/chat/completions", json.dumps(data), headers)
        
        # 获取响应
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        conn.close()
        
        # 计算耗时
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 解析响应
        result = json.loads(response_data)
        
        if 'error' in result:
            print(f"Error: {result['error']['message']}")
            return
        
        # 提取token消耗
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        # 提取响应内容
        content = result['choices'][0]['message']['content']
        
        # 计算token速度
        token_speed = total_tokens / elapsed_time if elapsed_time > 0 else 0
        
        # 输出结果
        print("=== LLM API Response ===")
        print(f"Model: {model}")
        print(f"Prompt: {prompt}")
        print(f"Response: {content}")
        print("\n=== Statistics ===")
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Total tokens: {total_tokens}")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        print(f"Token speed: {token_speed:.2f} tokens/second")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()