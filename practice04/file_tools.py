#!/usr/bin/env python3
"""
文件操作工具模块
提供以下功能：
1. 列出目录下的文件及属性
2. 修改文件名字
3. 删除文件
4. 新建文件并写入内容
5. 读取文件内容
6. 网络访问（curl功能）
"""

import os
import time
import http.client
from urllib.parse import urlparse


def list_files(directory):
    """
    列出指定目录下的所有文件及其属性
    
    Args:
        directory (str): 目录路径
    
    Returns:
        dict: 包含文件信息的字典，格式如下：
        {
            "status": "success" 或 "error",
            "message": 成功或错误信息,
            "files": [
                {
                    "name": 文件名,
                    "path": 文件完整路径,
                    "size": 文件大小（字节）,
                    "mtime": 最后修改时间（时间戳）,
                    "is_file": 是否为文件
                },
                ...
            ]
        }
    """
    try:
        if not os.path.exists(directory):
            return {
                "status": "error",
                "message": f"目录不存在: {directory}",
                "files": []
            }
        
        if not os.path.isdir(directory):
            return {
                "status": "error",
                "message": f"路径不是目录: {directory}",
                "files": []
            }
        
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            item_info = {
                "name": item,
                "path": item_path,
                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0,
                "mtime": os.path.getmtime(item_path),
                "is_file": os.path.isfile(item_path)
            }
            files.append(item_info)
        
        return {
            "status": "success",
            "message": f"成功列出目录 {directory} 下的文件",
            "files": files
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"操作失败: {str(e)}",
            "files": []
        }


def rename_file(directory, old_name, new_name):
    """
    修改指定目录下的文件名字
    
    Args:
        directory (str): 目录路径
        old_name (str): 原文件名
        new_name (str): 新文件名
    
    Returns:
        dict: 操作结果，格式如下：
        {
            "status": "success" 或 "error",
            "message": 成功或错误信息
        }
    """
    try:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        
        if not os.path.exists(old_path):
            return {
                "status": "error",
                "message": f"文件不存在: {old_path}"
            }
        
        if os.path.exists(new_path):
            return {
                "status": "error",
                "message": f"新文件名已存在: {new_path}"
            }
        
        os.rename(old_path, new_path)
        return {
            "status": "success",
            "message": f"成功将文件 {old_name} 重命名为 {new_name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"操作失败: {str(e)}"
        }


def delete_file(directory, file_name):
    """
    删除指定目录下的文件
    
    Args:
        directory (str): 目录路径
        file_name (str): 文件名
    
    Returns:
        dict: 操作结果，格式如下：
        {
            "status": "success" 或 "error",
            "message": 成功或错误信息
        }
    """
    try:
        file_path = os.path.join(directory, file_name)
        
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"文件不存在: {file_path}"
            }
        
        if not os.path.isfile(file_path):
            return {
                "status": "error",
                "message": f"路径不是文件: {file_path}"
            }
        
        os.remove(file_path)
        return {
            "status": "success",
            "message": f"成功删除文件 {file_name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"操作失败: {str(e)}"
        }


def create_file(directory, file_name, content):
    """
    在指定目录下新建文件并写入内容
    
    Args:
        directory (str): 目录路径
        file_name (str): 文件名
        content (str): 文件内容
    
    Returns:
        dict: 操作结果，格式如下：
        {
            "status": "success" 或 "error",
            "message": 成功或错误信息
        }
    """
    try:
        if not os.path.exists(directory):
            return {
                "status": "error",
                "message": f"目录不存在: {directory}"
            }
        
        if not os.path.isdir(directory):
            return {
                "status": "error",
                "message": f"路径不是目录: {directory}"
            }
        
        file_path = os.path.join(directory, file_name)
        
        if os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"文件已存在: {file_path}"
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "status": "success",
            "message": f"成功创建文件 {file_name} 并写入内容"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"操作失败: {str(e)}"
        }


def read_file(directory, file_name):
    """
    读取指定目录下的文件内容
    
    Args:
        directory (str): 目录路径
        file_name (str): 文件名
    
    Returns:
        dict: 操作结果，格式如下：
        {
            "status": "success" 或 "error",
            "message": 成功或错误信息,
            "content": 文件内容（成功时）
        }
    """
    try:
        file_path = os.path.join(directory, file_name)
        
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"文件不存在: {file_path}"
            }
        
        if not os.path.isfile(file_path):
            return {
                "status": "error",
                "message": f"路径不是文件: {file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "success",
            "message": f"成功读取文件 {file_name} 的内容",
            "content": content
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"操作失败: {str(e)}",
            "content": ""
        }


def curl(url, method="GET", headers=None, data=None):
    """
    网络访问功能，模拟curl命令访问网页并返回内容
    
    Args:
        url (str): 要访问的URL
        method (str): HTTP方法，默认为"GET"
        headers (dict): HTTP请求头，默认为None
        data (str): HTTP请求体数据，默认为None
    
    Returns:
        dict: 操作结果，格式如下：
        {
            "status": "success" 或 "error",
            "message": 成功或错误信息,
            "status_code": HTTP状态码（成功时）,
            "content": 网页内容（成功时）,
            "headers": 响应头（成功时）
        }
    """
    try:
        # 解析URL
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        if not host:
            return {
                "status": "error",
                "message": f"无效的URL: {url}"
            }
        
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
        path = parsed_url.path or "/"
        
        # 对路径中的中文字符进行URL编码
        from urllib.parse import quote
        path_parts = path.split('/')
        encoded_path_parts = []
        for part in path_parts:
            if part:
                encoded_part = quote(part, encoding='utf-8')
                encoded_path_parts.append(encoded_part)
            else:
                encoded_path_parts.append(part)
        path = '/'.join(encoded_path_parts)
        
        if parsed_url.query:
            path += f"?{parsed_url.query}"
        
        # 构建请求头
        request_headers = headers or {}
        # 添加默认请求头，模拟浏览器访问
        if "User-Agent" not in request_headers:
            request_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        if "Accept" not in request_headers:
            request_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        if "Accept-Language" not in request_headers:
            request_headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
        if "Connection" not in request_headers:
            request_headers["Connection"] = "keep-alive"
        if data and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        # 创建连接
        if parsed_url.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=30)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=30)
        
        # 发送请求
        conn.request(method, path, body=data, headers=request_headers)
        response = conn.getresponse()
        
        # 读取响应
        status_code = response.status
        content = response.read().decode('utf-8', errors='ignore')
        response_headers = dict(response.getheaders())
        
        conn.close()
        
        return {
            "status": "success",
            "message": f"成功访问URL: {url}",
            "status_code": status_code,
            "content": content,
            "headers": response_headers
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"操作失败: {str(e)}"
        }
