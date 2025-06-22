# 贡献指南

感谢您对MediaBot项目的关注！我们欢迎所有形式的贡献。

## 🤝 如何贡献

### 报告问题
- 使用[GitHub Issues](https://github.com/your-username/MediaBot/issues)报告bug
- 提供详细的错误信息和复现步骤
- 包含系统环境信息（操作系统、Python版本等）

### 提交功能请求
- 在Issues中提交功能请求
- 详细描述功能需求和使用场景
- 讨论实现方案

### 代码贡献

#### 开发环境设置
```bash
# 1. Fork并克隆项目
git clone https://github.com/your-username/MediaBot.git
cd MediaBot

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 4. 创建开发分支
git checkout -b feature/your-feature-name
```

#### 代码规范
- 使用Python 3.11+
- 遵循PEP 8代码风格
- 添加适当的注释和文档字符串
- 保持代码简洁易读

#### 提交流程
1. 确保代码通过所有测试
2. 添加必要的测试用例
3. 更新相关文档
4. 提交commit（使用清晰的commit message）
5. 推送到您的fork
6. 创建Pull Request

#### Commit Message 格式
```
类型(范围): 简短描述

详细说明（可选）

相关Issue: #123
```

类型:
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

#### 测试
```bash
# 运行测试
pytest

# 代码格式检查
black src/
flake8 src/
```

## 📋 开发指南

### 项目架构
```
src/
├── config/          # 配置管理
├── core/           # 核心功能
├── features/       # 功能模块
└── utils/          # 工具函数
```

### 添加新功能
1. 在适当的模块中添加代码
2. 编写测试用例
3. 更新配置示例
4. 更新文档

### 代码审查
- 所有PR都需要代码审查
- 确保功能完整且稳定
- 检查代码质量和性能
- 验证文档更新

## 🛡️ 安全考虑

### 敏感信息
- 不要提交真实的API密钥或凭证
- 使用环境变量管理敏感配置
- 确保.gitignore正确配置

### 合规性
- 确保功能符合Twitter服务条款
- 添加适当的使用警告
- 提供安全使用建议

## 📝 文档贡献

### 文档类型
- README.md: 项目概述和快速开始
- API文档: 代码接口说明
- 使用指南: 详细使用教程
- 配置说明: 配置选项解释

### 文档规范
- 使用清晰的标题结构
- 提供代码示例
- 包含截图说明（如需要）
- 保持内容更新

## 🎯 优先级任务

### 高优先级
- [ ] 性能优化
- [ ] 错误处理改进
- [ ] 测试覆盖率提升
- [ ] 文档完善

### 中优先级
- [ ] 新功能开发
- [ ] UI/UX改进
- [ ] 代码重构
- [ ] 国际化支持

### 低优先级
- [ ] 实验性功能
- [ ] 代码优化
- [ ] 工具改进

## 🤔 需要帮助？

- 查看[文档](docs/)
- 搜索[已有Issues](https://github.com/your-username/MediaBot/issues)
- 参与[讨论](https://github.com/your-username/MediaBot/discussions)
- 联系维护者

## 📜 行为准则

### 我们的承诺
- 创建开放友好的社区环境
- 尊重不同观点和经验
- 接受建设性批评
- 关注社区最佳利益

### 不当行为
- 使用性化的语言或图像
- 人身攻击或政治攻击
- 公开或私下骚扰
- 发布他人私人信息

### 执行
不当行为可能导致：
- 警告
- 临时禁止参与
- 永久禁止参与

## 📄 许可证

通过贡献代码，您同意您的贡献将在MIT许可证下授权。

---

再次感谢您的贡献！🎉 