# 条件判断功能使用指南

MediaBot的条件判断系统允许你为每个行为类型设置精确的执行条件，实现智能化的内容筛选和互动。

## 🎯 功能概述

### 支持的条件类型

#### 1. 互动数据条件
- `min_like_count` / `max_like_count`: 点赞数范围
- `min_retweet_count` / `max_retweet_count`: 转发数范围  
- `min_reply_count` / `max_reply_count`: 回复数范围
- `min_view_count` / `max_view_count`: 浏览量范围

#### 2. 用户条件
- `verified_only`: 仅对验证用户执行 (true/false/null)
- `exclude_verified`: 排除验证用户 (true/false/null)
- `min_follower_count` / `max_follower_count`: 粉丝数范围

#### 3. 内容条件
- `min_content_length` / `max_content_length`: 内容长度范围
- `has_media`: 是否包含媒体 (true/false/null)
- `media_types`: 特定媒体类型 ["image", "video", "gif"]

#### 4. 时间条件
- `max_age_hours`: 最大发布时间（小时）

## 📝 配置语法

### 基本结构
```json
{
  "action_type": "like",
  "count": 20,
  "conditions": {
    "min_like_count": 10,
    "max_like_count": 5000,
    "min_view_count": 100,
    "verified_only": null,
    "has_media": false
  }
}
```

### 条件值说明
- **数字条件**: 设置具体数值，`null` 表示不限制
- **布尔条件**: 
  - `true`: 必须满足条件
  - `false`: 必须不满足条件  
  - `null`: 不限制
- **数组条件**: 列表形式，如 `["image", "video"]`

## 🚀 使用示例

### 示例1: 精准点赞
```json
{
  "action_type": "like",
  "count": 30,
  "conditions": {
    "min_like_count": 5,        // 至少5个赞
    "max_like_count": 1000,     // 最多1000个赞
    "min_view_count": 50,       // 至少50次浏览
    "min_content_length": 20,   // 内容至少20字符
    "has_media": null,          // 不限制是否有媒体
    "verified_only": null       // 不限制验证状态
  }
}
```

### 示例2: 高质量关注
```json
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
```

### 示例3: 谨慎评论
```json
{
  "action_type": "comment",
  "count": 5,
  "conditions": {
    "min_like_count": 20,       // 有一定热度
    "max_like_count": 2000,     // 避免过热话题
    "min_reply_count": 2,       // 已有讨论
    "max_reply_count": 50,      // 讨论不过于激烈
    "min_content_length": 30,   // 有实质内容
    "has_media": false,         // 优先纯文本内容
    "verified_only": null       // 不限制验证状态
  },
  "comment_templates": [
    "很有见地的观点！👍",
    "感谢分享 🙏"
  ]
}
```

### 示例4: 选择性转发
```json
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
```

## 🎨 高级配置

### 组合条件示例
```json
{
  "action_type": "like",
  "conditions": {
    // 互动数据筛选
    "min_like_count": 10,
    "max_like_count": 5000,
    "min_view_count": 100,
    
    // 内容质量筛选
    "min_content_length": 25,
    "max_content_length": 280,
    
    // 用户类型筛选
    "verified_only": null,
    "exclude_verified": false,
    
    // 媒体类型筛选
    "has_media": null,
    "media_types": []
  }
}
```

### 不同行为类型的推荐配置

#### 点赞 (Like) - 宽松条件
```json
"conditions": {
  "min_like_count": 2,
  "max_like_count": 10000,
  "min_view_count": 20,
  "min_content_length": 10
}
```

#### 关注 (Follow) - 中等条件
```json
"conditions": {
  "min_like_count": 50,
  "min_view_count": 200,
  "min_content_length": 30,
  "verified_only": false
}
```

#### 评论 (Comment) - 严格条件
```json
"conditions": {
  "min_like_count": 20,
  "max_like_count": 3000,
  "min_reply_count": 2,
  "max_reply_count": 100,
  "min_content_length": 25,
  "has_media": false
}
```

#### 转发 (Retweet) - 最严格条件
```json
"conditions": {
  "min_like_count": 100,
  "min_retweet_count": 10,
  "min_view_count": 500,
  "verified_only": null,
  "has_media": true
}
```

## 🔧 条件调试

### 查看条件判断日志
启用详细日志模式查看条件判断过程：
```bash
export LOG_LEVEL=DEBUG
python autox.py --config your_config
```

### 常见条件不满足的原因
1. **点赞数过低**: 降低 `min_like_count` 值
2. **内容太短**: 降低 `min_content_length` 值
3. **浏览量不足**: 降低 `min_view_count` 值
4. **媒体条件**: 检查 `has_media` 和 `media_types` 设置

### 条件优化建议
- **新账号**: 使用较宽松的条件
- **成熟账号**: 可以设置更严格的条件
- **特定领域**: 根据领域特点调整条件
- **安全优先**: 设置上限避免过热内容

## 📊 条件效果分析

### 查看执行统计
每次会话结束后查看日志了解：
- 总共发现的目标数量
- 满足条件的目标数量
- 各类型行为的成功率
- 条件过滤的效果

### 配置优化流程
1. **初始配置**: 使用较宽松的条件
2. **观察效果**: 查看执行结果和质量
3. **调整条件**: 根据需求收紧或放宽条件
4. **持续优化**: 定期调整以适应平台变化

## ⚠️ 注意事项

### 条件设置原则
1. **逐步收紧**: 从宽松条件开始，逐步优化
2. **平衡数量与质量**: 条件太严格可能导致执行数量不足
3. **考虑平台特性**: 不同时间段的内容质量可能不同
4. **定期调整**: 根据平台算法变化调整条件

### 常见错误
- 条件设置过于严格导致无法找到合适目标
- 忽略 `null` 值的含义导致意外行为
- 数值范围设置不合理（如最小值大于最大值）

### 安全建议
- 设置合理的上限避免与过热内容互动
- 避免与争议性内容互动
- 定期检查和调整条件以适应平台变化

---

通过合理配置条件判断，你可以实现精准的内容筛选和高质量的自动化互动！ 