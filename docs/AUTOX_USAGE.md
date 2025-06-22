# AutoX 使用指南

AutoX是一个可配置的Twitter自动化任务系统，支持自定义行为、时间间隔和目标领域。

## 功能特性

### 支持的行为类型
- **点赞 (like)**: 自动点赞推文
- **关注 (follow)**: 自动关注用户  
- **评论 (comment)**: 自动回复推文
- **转发 (retweet)**: 自动转发推文
- **浏览 (browse)**: 浏览内容但不互动

### 会话管理
- 每次运行使用独立的Session ID
- 日志按session分离 (`logs/sessions/{session_id}/`)
- 数据记录按session分离 (`data/sessions/{session_id}/`)
- 支持会话配置保存和复用

### 智能过滤
- 关键词过滤（包含/排除）
- 最小点赞数过滤
- 语言检测过滤
- 内容年龄过滤

## 基本使用

### 1. 快速开始（使用默认配置）
```bash
python autox.py
```

### 2. 使用预设配置
```bash
# 查看可用配置
python autox.py --list-configs

# 使用AI领域配置
python autox.py --config ai_engagement

# 使用轻度浏览配置
python autox.py --config light_browsing
```

### 3. 创建自定义配置
```bash
# 创建新配置
python autox.py --create-config --name "我的AI任务" --session-id my_ai_task

# 编辑配置文件
# config/tasks/my_ai_task.json

# 使用配置运行
python autox.py --config my_ai_task
```

### 4. 使用搜索关键词限制
```bash
# 只在特定关键词搜索结果中执行
python autox.py --search "ChatGPT" "OpenAI" "机器学习"

# 结合配置使用
python autox.py --config ai_engagement --search "深度学习" "神经网络"
```

## 高级用法

### 命令行参数详解

```bash
python autox.py [选项]

选项:
  --config CONFIG       配置文件ID或路径
  --name NAME          任务名称 (默认: "AutoX Task")
  --search KEYWORD...  搜索关键词限制
  --create-config      创建示例配置
  --list-configs       列出可用配置
  --session-id ID      自定义会话ID
```

### 配置文件结构

```json
{
  "session_id": "任务标识符",
  "name": "任务名称",
  "description": "任务描述",
  
  "actions": [
    {
      "action_type": "like|follow|comment|retweet|browse",
      "count": 执行次数,
      "min_interval": 最小间隔秒数,
      "max_interval": 最大间隔秒数,
      "enabled": true,
      "comment_templates": ["评论模板1", "评论模板2"],
      "follow_back_ratio": 0.3
    }
  ],
  
  "target": {
    "keywords": ["目标关键词"],
    "hashtags": ["#标签"],
    "users": ["@用户名"],
    "languages": ["en", "zh"],
    "min_likes": 最小点赞数,
    "max_age_hours": 内容最大年龄小时,
    "exclude_keywords": ["排除关键词"]
  },
  
  "max_duration_minutes": 最大执行时间分钟,
  "max_total_actions": 最大总行为数,
  "randomize_intervals": true,
  "respect_rate_limits": true
}
```

## 使用场景示例

### 场景1: AI研究者互动
```bash
python autox.py --config ai_engagement --search "GPT-4" "Transformer" "BERT"
```

### 场景2: 轻度日常浏览
```bash
python autox.py --config light_browsing
```

### 场景3: 特定用户关注
创建配置文件，在target.users中指定目标用户：
```json
{
  "target": {
    "users": ["@elonmusk", "@sama", "@karpathy"],
    "min_likes": 100
  }
}
```

### 场景4: 中文科技内容
```json
{
  "target": {
    "keywords": ["人工智能", "机器学习", "深度学习"],
    "languages": ["zh"],
    "min_likes": 10
  }
}
```

## 数据和日志

### 日志文件位置
```
logs/sessions/{session_id}/{session_id}_{timestamp}.log
```

### 数据文件位置
```
data/sessions/{session_id}/
├── actions_{timestamp}.json      # 行为记录
├── stats_{timestamp}.json        # 统计信息
├── targets_{timestamp}.json      # 发现的目标
└── session_summary.json          # 会话摘要
```

### 查看会话结果
每次会话结束后，会在控制台输出摘要：
- 总行为数
- 成功率
- 各类型行为统计
- 结果分布

## 安全注意事项

### 速率限制
- 系统自动遵守Twitter的速率限制
- 建议使用随机化间隔避免检测
- 不要设置过高的行为频率

### 内容过滤
- 使用exclude_keywords避免敏感内容
- 设置合理的min_likes过滤低质量内容
- 启用语言过滤确保内容相关性

### 账号安全
- 使用环境变量管理登录凭据
- 避免在短时间内执行大量操作
- 定期检查账号状态

## 故障排除

### 常见问题

1. **登录失败**
   - 检查.env文件中的凭据
   - 确认账号没有被限制
   - 可能需要手动登录一次

2. **找不到内容**
   - 调整关键词设置
   - 降低min_likes阈值
   - 检查语言过滤设置

3. **操作失败**
   - 检查页面元素是否更新
   - 降低操作频率
   - 查看详细日志错误信息

### 调试模式
修改config/settings.py：
```python
LOG_LEVEL = "DEBUG"
HEADLESS = False  # 显示浏览器窗口
```

## 扩展开发

### 添加新的行为类型
1. 在`src/config/task_config.py`中添加新的ActionType
2. 在`src/features/actions/executor.py`中实现对应方法
3. 更新配置文件模板

### 自定义内容过滤器
扩展`ContentFilter`类添加新的过滤逻辑：
```python
def custom_filter(self, content_info: Dict[str, Any]) -> bool:
    # 自定义过滤逻辑
    return True
```

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的Twitter操作
- 实现会话管理和数据记录
- 提供配置化任务系统 