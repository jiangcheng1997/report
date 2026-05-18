# LLM 聊天客户端（支持链式工具调用）

## 项目简介

本项目是一个基于 OpenAI 兼容协议的 LLM 聊天客户端，实现了**链式工具调用（Chained Tool Calls）**功能。该功能允许 LLM 根据前一个工具的输出结果自主决定下一步操作，实现多步骤任务的自动化执行。

## 功能特性

### 核心功能
1. **链式工具调用**：支持前一个工具的输出作为后一个工具的输入参数
2. **流式输出**：逐字显示 LLM 响应，提升用户体验
3. **历史记录管理**：自动维护聊天上下文
4. **意图识别**：自动检测通知请求并调用 LLM 智能生成

### 支持的工具
| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `list_files` | 列出目录下所有文件 | `directory` |
| `read_file` | 读取文件内容 | `directory`, `file_name` |
| `create_file` | 创建新文件 | `directory`, `file_name`, `content` |
| `delete_file` | 删除文件 | `directory`, `file_name` |
| `rename_file` | 重命名文件 | `directory`, `old_name`, `new_name` |
| `curl` | 网络访问 | `url`, `method`, `headers`, `data` |
| `anythingllm_query` | 查询文档仓库 | `message` |
| `load_skill_content` | 加载技能内容 | `skill_name` |

## 链式调用实现

### ChainedCallContext 类
用于管理链式调用的上下文状态：
- 记录每一步的工具调用和结果
- 存储中间变量供后续步骤使用
- 设置最大迭代次数防止无限循环

### execute_chained_tool_call 函数
实现链式工具调用的完整流程：
1. 初始化消息历史（包含 system prompt）
2. 循环最多 `max_iterations` 次（默认10次）
3. 构建分析提示词（包含用户请求和已执行步骤历史）
4. 调用 LLM 决定下一步操作
5. 解析 LLM 响应（支持 JSON 格式）
6. 根据决策执行工具或返回最终回答

### LLM 决策输出格式

**任务完成时：**
```json
{"done": true, "answer": "最终回答内容"}
```

**继续调用工具时：**
```json
{"done": false, "tool_call": {"name": "工具名称", "arguments": {"参数名": "参数值"}}}
```

## 安装与配置

### 环境要求
- Python 3.7+

### 配置文件

在项目根目录创建 `.env` 文件：

```env
BASE_URL=http://localhost:1234/v1
MODEL=Qwen3.5-4b
API_KEY=lm-studio
TEMPERATURE=0.7
MAX_TOKENS=4096
TIMEOUT=30
```

### 运行方式

```bash
python skill_client.py
```

## 测试用例

### 测试1：文件搜索链式调用
```
请查找 practice05 目录下所有包含'def'关键词的文件，并总结这些文件的主要内容
```

### 测试2：技能查询链式调用
```
我想了解 notice 技能的详细规则
```

### 测试3：网页处理链式调用
```
访问 https://www.nsu.edu.cn/HTML/news/2024/06/article_3974.html 并总结页面内容，保存到 practice06/summary.txt
```

运行测试：
```bash
python skill_client.py
# 输入 'test' 运行所有测试用例
```

## 链式调用工作流程

```
用户请求 → 构建分析提示词 → 调用LLM → 解析决策 → 执行工具 → 更新上下文 → 循环直到完成
```

## 注意事项

1. **JSON 解析**：LLM 可能返回包含 markdown 代码块标记的内容，系统会自动提取 JSON 部分
2. **响应格式**：支持标准 JSON 格式输出
3. **错误处理**：处理 LLM 响应为 None、JSON 解析失败、工具执行异常等情况
4. **防止无限循环**：设置 `max_iterations=10` 限制最大迭代次数

## 项目结构

```
practice06/
├── skill_client.py      # 主客户端（含链式调用实现）
├── file_tools.py        # 文件操作工具模块
├── anythingllm_query.py # AnythingLLM 查询模块
└── README.md            # 项目文档
```