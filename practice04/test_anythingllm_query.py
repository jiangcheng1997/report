#!/usr/bin/env python3
"""
测试AnythingLLM查询功能
"""

from anythingllm_query import query_anythingllm

def test_query():
    """测试查询功能"""
    print("=== 测试 AnythingLLM 查询功能 ===")
    
    # 测试用例1：简单查询
    print("\n测试用例1：简单查询")
    response = query_anythingllm("你好，AnythingLLM")
    print(f"响应: {response}")
    
    # 测试用例2：中文查询
    print("\n测试用例2：中文查询")
    response = query_anythingllm("请介绍一下你自己")
    print(f"响应: {response}")
    
    # 测试用例3：复杂查询
    print("\n测试用例3：复杂查询")
    response = query_anythingllm("什么是人工智能？请详细解释")
    print(f"响应: {response}")

if __name__ == "__main__":
    test_query()
