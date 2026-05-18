#!/usr/bin/env python3
"""
测试文件操作工具
"""

from file_tools import list_files, rename_file, delete_file, create_file, read_file

# 测试目录
TEST_DIR = "."

print("=== 测试文件操作工具 ===")
print()

# 测试1: 列出目录下的文件
print("1. 测试列出目录下的文件:")
result = list_files(TEST_DIR)
print(f"状态: {result['status']}")
print(f"消息: {result['message']}")
print(f"文件数量: {len(result['files'])}")
for file in result['files']:
    print(f"  - {file['name']} (大小: {file['size']} 字节)")
print()

# 测试2: 创建新文件
print("2. 测试创建新文件:")
test_file_name = "test_file.txt"
test_content = "这是一个测试文件内容\nHello, World!"
result = create_file(TEST_DIR, test_file_name, test_content)
print(f"状态: {result['status']}")
print(f"消息: {result['message']}")
print()

# 测试3: 读取文件内容
print("3. 测试读取文件内容:")
result = read_file(TEST_DIR, test_file_name)
print(f"状态: {result['status']}")
print(f"消息: {result['message']}")
if result['status'] == "success":
    print(f"内容: {result['content']}")
print()

# 测试4: 重命名文件
print("4. 测试重命名文件:")
new_file_name = "renamed_test_file.txt"
result = rename_file(TEST_DIR, test_file_name, new_file_name)
print(f"状态: {result['status']}")
print(f"消息: {result['message']}")
print()

# 测试5: 删除文件
print("5. 测试删除文件:")
result = delete_file(TEST_DIR, new_file_name)
print(f"状态: {result['status']}")
print(f"消息: {result['message']}")
print()

print("=== 测试完成 ===")
