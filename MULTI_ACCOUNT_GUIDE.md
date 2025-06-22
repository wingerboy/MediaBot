# MediaBot 多账号使用指南

## 概述

MediaBot现在支持多账号管理，可以使用多个Twitter账号按顺序执行相同任务，有效降低单账号风控风险。

## 功能特性

- **多账号配置管理**：支持添加、删除、启用/禁用多个账号
- **智能冷却机制**：账号使用后自动冷却2小时，避免频繁操作
- **风控规避**：账号间随机等待5-15分钟，模拟真实用户行为
- **状态跟踪**：记录每个账号的使用次数、最后使用时间等信息
- **Cookie管理**：支持为每个账号独立保存和加载cookies

## 快速开始

### 1. 账号管理

使用账号管理工具添加和管理多个账号：

```bash
# 启动账号管理界面
python manage_accounts.py

# 或者使用命令行参数
python manage_accounts.py --add    # 添加账号
python manage_accounts.py --list   # 列出账号
python manage_accounts.py --stats  # 显示统计
```

### 2. 添加账号

在交互式界面中选择"添加账号"，然后输入：

- **账号ID**：唯一标识符（如：main_account, backup_account）
- **Twitter用户名**：@后面的用户名
- **显示名称**：便于识别的名称
- **邮箱**：登录邮箱
- **密码**：登录密码
- **备注**：可选的备注信息

### 3. 获取Cookies

对于每个账号，你需要：

1. 手动在浏览器中登录该Twitter账号
2. 使用浏览器扩展或开发者工具导出cookies
3. 保存为JSON格式到指定路径：`data/cookies/cookies_{账号ID}.json`

或者让系统自动保存cookies：
- 首次运行时，系统会尝试登录并自动保存cookies
- 后续运行将使用保存的cookies跳过登录步骤

## 使用方法

### 多账号模式

使用所有可用账号按顺序执行任务：

```bash
python autox.py --config config/tasks/multi_account_demo.json --multi-account
```

### 指定账号模式

使用特定账号执行任务：

```bash
python autox.py --config config/tasks/multi_account_demo.json --account-id main_account
```

### 单账号模式（环境变量）

使用.env文件配置的默认账号：

```bash
python autox.py --config config/tasks/multi_account_demo.json
```

## 配置文件

多账号模式使用与单账号相同的配置文件格式。系统会为每个账号执行相同的任务配置。

示例配置：`config/tasks/multi_account_demo.json`

```json
{
  "name": "多账号智能评论与关注",
  "max_duration_minutes": 30,
  "max_total_actions": 20,
  "actions": [
    {
      "action_type": "comment",
      "count": 8,
      "use_ai_comment": true
    },
    {
      "action_type": "follow", 
      "count": 5
    }
  ]
}
```

## 冷却机制

- **自动冷却**：每个账号使用后自动冷却2小时
- **状态检查**：系统只使用可用状态的账号
- **手动管理**：可以手动清除冷却或禁用账号

```bash
# 清除所有账号冷却
python manage_accounts.py --clear-cooldowns

# 或在交互式界面中选择相应选项
```

## 风控规避策略

1. **时间间隔**：账号间随机等待5-15分钟
2. **行为随机化**：启用随机行为间隔
3. **冷却时间**：强制2小时冷却期
4. **独立Cookies**：每个账号使用独立的cookies文件
5. **失败处理**：失败的账号也会被设置冷却，避免频繁重试

## 账号状态管理

### 查看账号状态

```bash
python manage_accounts.py --list
```

输出示例：
```
📱 main_account (@user1)
   状态: 🟢 活跃 | ✅ 可用
   使用次数: 5 | 最后使用: 2024-01-15 14:30:25

📱 backup_account (@user2)  
   状态: 🟢 活跃 | ⏰ 冷却中 (冷却至: 16:30:25)
   使用次数: 3 | 最后使用: 2024-01-15 14:15:10
```

### 账号操作

- **禁用账号**：临时停用某个账号
- **启用账号**：重新启用禁用的账号
- **删除账号**：永久删除账号配置
- **清除冷却**：立即让所有账号变为可用状态

## 日志与监控

每个账号的执行都会生成独立的日志：

```
logs/
├── autox_20240115_143025_abc123.log  # 主会话日志
├── accounts/
│   ├── main_account_actions.log      # 账号操作日志
│   └── backup_account_actions.log
```

## 最佳实践

1. **账号准备**：
   - 使用不同IP注册的账号
   - 账号有一定的活跃历史
   - 避免批量注册的新账号

2. **使用策略**：
   - 控制每个账号的日常操作量
   - 设置合理的行为间隔
   - 定期检查账号状态

3. **风险控制**：
   - 监控账号是否被限制
   - 及时调整操作频率
   - 保持账号的多样性操作

4. **配置优化**：
   - 根据账号类型调整参数
   - 使用AI评论增加自然度
   - 设置合适的条件过滤

## 故障排除

### 常见问题

1. **账号不可用**
   - 检查是否在冷却期
   - 确认账号状态是否启用
   - 验证cookies文件是否存在

2. **登录失败**
   - 检查账号密码是否正确
   - 确认账号未被冻结
   - 尝试手动登录获取新cookies

3. **执行中断**
   - 检查网络连接
   - 查看日志错误信息
   - 确认配置文件格式正确

### 调试命令

```bash
# 查看账号统计
python manage_accounts.py --stats

# 测试单个账号
python autox.py --config your_config.json --account-id test_account

# 查看日志
tail -f logs/autox_*.log
```

## 安全建议

1. **账号安全**：
   - 定期更新密码
   - 启用两步验证
   - 监控账号异常活动

2. **数据保护**：
   - 保护cookies文件安全
   - 定期备份账号配置
   - 避免在公共网络使用

3. **合规使用**：
   - 遵守Twitter服务条款
   - 避免恶意或垃圾行为
   - 尊重其他用户权益

通过合理使用多账号功能，可以在降低风控风险的同时，提高自动化任务的执行效率和成功率。 