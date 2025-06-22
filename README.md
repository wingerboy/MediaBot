# MediaBot - Twitter自动化机器人

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/Playwright-Latest-orange.svg)](https://playwright.dev/)

MediaBot是一个基于Playwright的Twitter自动化机器人，支持智能互动、条件判断和可配置的任务执行。

## 🌟 主要特性

### 🤖 智能互动
- **自动点赞**: 根据条件智能点赞推文
- **智能关注**: 基于用户质量进行关注
- **智能评论**: 支持模板和AI生成评论
- **自动转发**: 选择性转发高质量内容

### 🎯 精准控制
- **条件判断**: 基于点赞数、转发数、回复数、浏览量等指标
- **内容过滤**: 支持关键词、语言、媒体类型过滤
- **用户筛选**: 验证状态、粉丝数等条件
- **时间控制**: 发布时间限制和会话时长管理

### ⚙️ 高度可配置
- **JSON配置**: 灵活的任务配置系统
- **多任务支持**: 同时执行多种类型的行为
- **安全间隔**: 随机化操作间隔，模拟人工行为
- **会话管理**: 完整的会话记录和统计

### 🛡️ 安全保障
- **反检测**: 基于Playwright Stealth的反检测技术
- **速率限制**: 遵守平台限制，避免封号风险
- **错误处理**: 完善的异常处理和恢复机制
- **日志记录**: 详细的操作日志和调试信息

## 📦 安装指南

### 环境要求
- Python 3.11+
- 支持的操作系统: Windows, macOS, Linux

### 1. 克隆项目
```bash
git clone https://github.com/your-username/MediaBot.git
cd MediaBot
```

### 2. 安装依赖
```bash
# 使用Poetry (推荐)
pip install poetry
poetry install

# 或使用pip
pip install -r requirements.txt
```

### 3. 安装浏览器
```bash
# 安装Playwright浏览器
poetry run playwright install chromium
# 或
playwright install chromium
```

### 4. 配置环境变量
```bash
# 复制环境变量模板
cp env.example .env

# 编辑.env文件，填入你的Twitter账号信息
nano .env
```

#### 环境变量配置
```bash
# Twitter账号信息
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
TWITTER_EMAIL=your_email@example.com

# 浏览器设置
HEADLESS=False
BROWSER_TYPE=chromium

# 行为设置
MIN_DELAY=2.0
MAX_DELAY=5.0
```

## 🚀 快速开始

### 1. 查看可用配置
```bash
python autox.py --list-configs
```

### 2. 创建示例配置
```bash
python autox.py --create-config --name "我的第一个任务"
```

### 3. 运行任务
```bash
# 使用默认配置
python autox.py

# 使用指定配置
python autox.py --config conditional_engagement

# 使用搜索关键词
python autox.py --search "AI" "机器学习" --config my_task
```

### 4. 基础使用示例
```bash
# 运行条件化互动任务
python autox.py --config conditional_engagement

# 自定义会话ID
python autox.py --config my_task --session-id my_session_001
```

## ⚙️ 配置说明

### 任务配置结构
```json
{
  "session_id": "task_name",
  "name": "任务显示名称",
  "description": "任务描述",
  "actions": [
    {
      "action_type": "like",
      "count": 20,
      "min_interval": 3.0,
      "max_interval": 8.0,
      "enabled": true,
      "conditions": {
        "min_like_count": 10,
        "max_like_count": 5000,
        "min_view_count": 100
      }
    }
  ],
  "target": {
    "keywords": ["AI", "机器学习"],
    "hashtags": ["#AI", "#ML"],
    "languages": ["en", "zh"]
  },
  "max_duration_minutes": 60,
  "max_total_actions": 100
}
```

### 支持的行为类型
- `like`: 点赞
- `follow`: 关注
- `comment`: 评论
- `retweet`: 转发
- `browse`: 浏览

### 🎯 条件判断系统

MediaBot的核心特性是智能条件判断，每个行为都可以设置精确的执行条件：

#### 支持的条件类型
```json
"conditions": {
  // 互动数据条件
  "min_like_count": 10,           // 最小点赞数
  "max_like_count": 5000,         // 最大点赞数
  "min_retweet_count": 5,         // 最小转发数
  "max_retweet_count": 1000,      // 最大转发数
  "min_reply_count": 2,           // 最小回复数
  "max_reply_count": 100,         // 最大回复数
  "min_view_count": 100,          // 最小浏览量
  "max_view_count": 50000,        // 最大浏览量
  
  // 用户条件
  "verified_only": null,          // 仅验证用户 (true/false/null)
  "exclude_verified": false,      // 排除验证用户 (true/false/null)
  "min_follower_count": 100,      // 最小粉丝数
  "max_follower_count": 100000,   // 最大粉丝数
  
  // 内容条件
  "min_content_length": 20,       // 最小内容长度
  "max_content_length": 280,      // 最大内容长度
  "has_media": null,              // 是否包含媒体 (true/false/null)
  "media_types": ["image", "video"], // 特定媒体类型
  
  // 时间条件
  "max_age_hours": 24            // 最大发布时间（小时）
}
```

#### 条件值说明
- **数字条件**: 设置具体数值，不设置或设为 `null` 表示不限制
- **布尔条件**: 
  - `true`: 必须满足条件
  - `false`: 必须不满足条件  
  - `null`: 不限制
- **数组条件**: 列表形式，如 `["image", "video"]`

## 📊 使用示例

### 示例1: 精准点赞任务
```json
{
  "session_id": "precise_like",
  "name": "精准点赞任务",
  "actions": [
    {
      "action_type": "like",
      "count": 30,
      "conditions": {
        "min_like_count": 5,        // 至少5个赞
        "max_like_count": 1000,     // 最多1000个赞
        "min_view_count": 50,       // 至少50次浏览
        "min_content_length": 20,   // 内容至少20字符
        "has_media": null           // 不限制是否有媒体
      }
    }
  ]
}
```

### 示例2: 高质量关注任务
```json
{
  "session_id": "quality_follow",
  "name": "高质量关注",
  "actions": [
    {
      "action_type": "follow",
      "count": 10,
      "conditions": {
        "min_like_count": 100,      // 高互动内容的作者
        "min_view_count": 500,      // 高曝光内容
        "min_content_length": 50,   // 有实质内容
        "verified_only": false,     // 不限制仅验证用户
        "exclude_verified": false,  // 不排除验证用户
        "has_media": true          // 有媒体内容的推文
      }
    }
  ]
}
```

### 示例3: 智能评论任务
```json
{
  "session_id": "smart_comment",
  "name": "智能评论",
  "actions": [
    {
      "action_type": "comment",
      "count": 5,
      "comment_templates": [
        "很有见地的观点！👍",
        "感谢分享 🙏",
        "Great insights! 🚀"
      ],
      "conditions": {
        "min_like_count": 20,       // 有一定热度
        "max_like_count": 2000,     // 避免过热话题
        "min_reply_count": 2,       // 已有讨论
        "max_reply_count": 50,      // 讨论不过于激烈
        "min_content_length": 30,   // 有实质内容
        "has_media": false          // 优先纯文本内容
      }
    }
  ]
}
```

### 示例4: 选择性转发任务
```json
{
  "session_id": "selective_retweet",
  "name": "选择性转发",
  "actions": [
    {
      "action_type": "retweet",
      "count": 3,
      "conditions": {
        "min_like_count": 200,      // 高质量内容
        "min_retweet_count": 20,    // 已有转发
        "min_view_count": 1000,     // 高曝光
        "verified_only": true,      // 仅验证用户
        "has_media": true,          // 包含媒体
        "media_types": ["image", "video"]  // 特定媒体类型
      }
    }
  ]
}
```

### 示例5: 无条件执行（默认行为）
```json
{
  "session_id": "no_conditions",
  "name": "无条件执行",
  "actions": [
    {
      "action_type": "like",
      "count": 15,
      "conditions": {}  // 空条件对象，按默认方式执行
    }
  ]
}
```

## 📁 项目结构

```
MediaBot/
├── src/                          # 源代码
│   ├── config/                   # 配置管理
│   ├── core/                     # 核心功能
│   │   ├── browser/              # 浏览器管理
│   │   └── twitter/              # Twitter客户端
│   ├── features/                 # 功能模块
│   │   ├── actions/              # 行为执行器
│   │   └── browse/               # 浏览功能
│   └── utils/                    # 工具函数
├── config/                       # 配置文件
│   ├── settings.py               # 基础设置
│   └── tasks/                    # 任务配置
├── docs/                         # 文档
├── logs/                         # 日志文件 (git忽略)
├── autox.py                      # 主程序入口
├── main.py                       # 基础功能演示
└── pyproject.toml                # 项目配置
```

## 🔧 高级功能

### 条件判断系统
支持基于多种指标的智能条件判断：
- 互动数据: 点赞、转发、回复、浏览量
- 用户条件: 验证状态、粉丝数
- 内容条件: 媒体类型、内容长度
- 时间条件: 发布时间限制

### 会话管理
- 自动生成唯一会话ID
- 完整的操作记录和统计
- 实时日志输出
- 会话数据持久化

### 安全特性
- 随机化操作间隔
- 智能反检测机制
- 速率限制遵守
- 异常恢复处理

## 📝 日志和调试

### 日志位置
```
logs/
├── sessions/                     # 会话日志
│   └── [session_id]/
│       └── [session_id]_[timestamp].log
└── system.log                    # 系统日志
```

### 调试模式
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python autox.py --config my_task
```

### 条件调试
查看条件判断详情：
```bash
# 运行任务并查看条件判断日志
python autox.py --config conditional_engagement
```

日志示例：
```
条件检查失败 [like] @username - 赞:8 转:1 回:0 看:45 长度:15 验证:false
条件检查成功 [like] @username - 赞:25 转:3 回:2 看:150 长度:45 验证:false
```

## 📚 相关文档

- [条件判断详细指南](docs/CONDITIONS_GUIDE.md) - 深入了解条件配置
- [配置示例集合](config/tasks/) - 各种场景的配置模板
- [贡献指南](CONTRIBUTING.md) - 如何参与项目开发

## ⚠️ 注意事项

### 使用须知
1. **遵守平台规则**: 请确保使用符合Twitter服务条款
2. **适度使用**: 建议设置合理的操作频率和数量
3. **账号安全**: 使用小号测试，避免主账号风险
4. **网络环境**: 建议使用稳定的网络环境

### 条件设置建议
- **新手**: 使用较宽松的条件，如 `basic_engagement` 配置
- **进阶**: 使用中等条件，如 `conditional_engagement` 配置
- **专家**: 自定义严格条件，精确控制互动质量

### 风险提示
- 自动化操作可能违反平台规则
- 过度使用可能导致账号限制
- 请在了解风险的前提下使用

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持与反馈

- 📧 邮箱: [your-email@example.com]
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-username/MediaBot/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-username/MediaBot/discussions)

## 🔄 更新日志

### v1.0.0 (Latest)
- ✅ 基础自动化功能
- ✅ 智能条件判断系统
- ✅ 配置化任务管理
- ✅ 会话记录和统计
- ✅ 反检测机制
- ✅ 完整的日志系统

---

**免责声明**: 本工具仅供学习和研究目的。使用者需自行承担使用风险，遵守相关平台的服务条款。 