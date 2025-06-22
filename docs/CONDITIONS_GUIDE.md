# 条件判断功能使用指南

AutoX现在支持为每种行为类型配置执行条件，让您可以精确控制何时执行like、follow、comment等操作。

## 功能概述

### 支持的条件类型

#### 1. 互动数据条件
- `min_like_count` / `max_like_count`: 点赞数范围
- `min_retweet_count` / `max_retweet_count`: 转发数范围  
- `min_reply_count` / `max_reply_count`: 回复数范围
- `min_view_count` / `max_view_count`: 浏览量范围

#### 2. 用户条件
- `verified_only`: 仅对验证用户执行 (true/false/null)
- `exclude_verified`: 排除验证用户 (true/false/null)
- `min_follower_count` / `max_follower_count`: 粉丝数范围（如果可获取）

#### 3. 内容条件
- `has_media`: 是否包含媒体 (true/false/null)
- `media_types`: 特定媒体类型 ["image", "video", "gif"]
- `min_content_length` / `max_content_length`: 内容长度范围

#### 4. 时间条件
- `max_age_hours`: 推文最大年龄（小时）

## 配置示例

### 基础点赞条件
```json
{
  "action_type": "like",
  "count": 20,
  "conditions": {
    "min_like_count": 10,        // 至少10个赞
    "max_like_count": 5000,      // 最多5000个赞
    "min_view_count": 200,       // 至少200浏览量
    "min_content_length": 20     // 至少20字符
  }
}
```

### 高质量关注条件
```json
{
  "action_type": "follow",
  "count": 5,
  "conditions": {
    "min_like_count": 100,       // 高质量内容
    "min_view_count": 1000,      // 高浏览量
    "verified_only": false,      // 不限制验证状态
    "has_media": true,           // 包含媒体
    "media_types": ["image", "video"]  // 图片或视频
  }
}
```

### 精准评论条件
```json
{
  "action_type": "comment",
  "count": 3,
  "conditions": {
    "min_like_count": 50,        // 有一定热度
    "max_like_count": 2000,      // 避免过热内容
    "min_reply_count": 3,        // 已有讨论
    "max_reply_count": 50,       // 讨论不过热
    "has_media": false,          // 纯文本内容
    "min_content_length": 40,    // 有实质内容
    "max_content_length": 300    // 不过长
  }
}
```

### 转发条件（仅高质量内容）
```json
{
  "action_type": "retweet", 
  "count": 2,
  "conditions": {
    "min_like_count": 200,       // 高热度
    "min_retweet_count": 20,     // 已有转发
    "min_view_count": 2000,      // 高浏览量
    "verified_only": true,       // 仅验证用户
    "max_content_length": 280    // 不超过推文长度限制
  }
}
```

## 实际使用场景

### 场景1: 保守点赞策略
只对中等热度、有实质内容的推文点赞：
```json
"conditions": {
  "min_like_count": 10,
  "max_like_count": 1000,
  "min_view_count": 100,
  "min_content_length": 30,
  "has_media": null
}
```

### 场景2: 质量关注策略
只关注发布高质量媒体内容的活跃用户：
```json
"conditions": {
  "min_like_count": 50,
  "min_view_count": 500,
  "has_media": true,
  "media_types": ["image", "video"],
  "min_content_length": 50
}
```

### 场景3: 精准评论策略
只在有意义的讨论中参与评论：
```json
"conditions": {
  "min_like_count": 20,
  "max_like_count": 5000,
  "min_reply_count": 2,
  "max_reply_count": 100,
  "has_media": false,
  "min_content_length": 40
}
```

### 场景4: 病毒内容转发
只转发已经开始病毒传播的高质量内容：
```json
"conditions": {
  "min_like_count": 500,
  "min_retweet_count": 100,
  "min_view_count": 5000,
  "verified_only": false,
  "max_content_length": 200
}
```

## 条件逻辑说明

### 条件组合
- 所有设置的条件必须**同时满足**才会执行行为
- 设置为`null`的条件将被忽略
- 未设置的条件默认为`null`（不限制）

### 数值解析
- 系统会自动解析数字格式：`"1.2K"` → `1200`
- 支持逗号分隔：`"1,234"` → `1234`
- 无效数字默认为`0`

### 布尔值处理
- `true`: 必须满足条件
- `false`: 必须不满足条件  
- `null`: 不限制

## 调试和监控

### 日志输出
当条件不满足时，系统会记录详细信息：
```
条件检查失败 [like] @username - 赞:15 转:2 回:1 看:150 长度:25 验证:false
```

### 统计信息
会话结束后可以查看：
- 总检查次数
- 条件满足次数
- 各条件的过滤统计

## 最佳实践

### 1. 渐进式调整
- 开始时设置宽松条件
- 根据结果逐步收紧条件
- 监控执行成功率

### 2. 平衡策略
- 避免条件过于严格导致无法执行
- 考虑不同时间段的内容特点
- 为不同行为类型设置不同标准

### 3. 安全考虑
- 设置合理的上限避免参与过热话题
- 使用内容长度过滤垃圾信息
- 考虑验证状态平衡可信度和多样性

### 4. 效果优化
- 定期分析会话数据
- 调整条件参数优化效果
- A/B测试不同条件组合

## 配置模板

### 新手友好配置
```json
"conditions": {
  "min_like_count": 5,
  "min_view_count": 50,
  "min_content_length": 15
}
```

### 中等选择性配置
```json
"conditions": {
  "min_like_count": 20,
  "max_like_count": 2000,
  "min_view_count": 200,
  "min_content_length": 30,
  "max_content_length": 500
}
```

### 高选择性配置
```json
"conditions": {
  "min_like_count": 100,
  "max_like_count": 10000,
  "min_retweet_count": 10,
  "min_view_count": 1000,
  "min_content_length": 50,
  "has_media": true,
  "verified_only": false
}
```

## 故障排除

### 常见问题

1. **没有内容被执行**
   - 检查条件是否过于严格
   - 降低数值阈值
   - 查看调试日志了解过滤原因

2. **条件不生效**
   - 确认JSON格式正确
   - 检查字段名拼写
   - 验证数据类型匹配

3. **执行率过低**
   - 分析日志找出主要过滤原因
   - 调整最严格的条件
   - 考虑时间段和内容类型因素

### 调试技巧
- 使用`null`临时禁用某个条件
- 逐个添加条件测试影响
- 对比不同配置的执行效果 