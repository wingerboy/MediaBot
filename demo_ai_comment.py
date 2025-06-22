#!/usr/bin/env python3
"""
AI评论功能演示脚本
展示如何使用AI生成智能评论
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.config.task_config import SessionConfig, config_manager
from autox import AutoXSession
from config.settings import settings

def display_ai_comment_info():
    """显示AI评论功能信息"""
    print("🤖 MediaBot AI评论功能演示")
    print("=" * 60)
    print()
    
    print("📋 功能特点:")
    print("   • 基于DeepSeek大模型的智能评论生成")
    print("   • 自动分析推文内容和语境")
    print("   • 根据推文语言自动选择回复语言")
    print("   • 支持中英文智能回复")
    print("   • AI失败时自动使用模板备用")
    print()
    
    print("⚙️  配置要求:")
    print("   • 在.env文件中设置DEEPSEEK_API_KEY")
    print("   • 在任务配置中启用use_ai_comment")
    print("   • 设置ai_comment_fallback备用机制")
    print()
    
    # 检查API密钥配置
    if settings.DEEPSEEK_API_KEY:
        print(f"✅ DeepSeek API密钥已配置: {settings.DEEPSEEK_API_KEY[:10]}...")
        print(f"   模型: {settings.DEEPSEEK_MODEL}")
        print(f"   温度: {settings.DEEPSEEK_TEMPERATURE}")
        print(f"   最大tokens: {settings.DEEPSEEK_MAX_TOKENS}")
    else:
        print("❌ 未配置DeepSeek API密钥")
        print("   请在.env文件中设置DEEPSEEK_API_KEY")
    print()

def display_config_info():
    """显示配置信息"""
    print("📁 AI评论演示配置 (ai_comment_demo)")
    print("-" * 40)
    
    try:
        config = config_manager.load_config("ai_comment_demo")
        if config:
            print(f"任务名称: {config.name}")
            print(f"描述: {config.description}")
            print(f"最大时长: {config.max_duration_minutes}分钟")
            print(f"最大行为数: {config.max_total_actions}")
            print()
            
            print("行为配置:")
            for action in config.actions:
                print(f"  • {action.action_type.value}: {action.count}次")
                if action.action_type.value == "comment":
                    print(f"    - AI评论: {'启用' if action.use_ai_comment else '禁用'}")
                    print(f"    - 备用机制: {'启用' if action.ai_comment_fallback else '禁用'}")
                    print(f"    - 模板数量: {len(action.comment_templates)}")
                    if action.conditions:
                        print(f"    - 条件数量: {len(action.conditions)}")
            print()
        else:
            print("❌ 配置文件不存在，请先创建ai_comment_demo配置")
            return False
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return False
    
    return True

async def run_ai_comment_demo():
    """运行AI评论演示"""
    print("🚀 启动AI评论演示任务...")
    print("-" * 40)
    
    try:
        # 加载配置
        config = config_manager.load_config("ai_comment_demo")
        if not config:
            print("❌ 无法加载ai_comment_demo配置")
            return
        
        # 创建会话
        session = AutoXSession(config)
        
        # 启动并运行
        await session.start()
        await session.run_task()
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断任务")
    except Exception as e:
        print(f"❌ 任务执行失败: {e}")

def main():
    """主函数"""
    print()
    display_ai_comment_info()
    
    # 显示配置信息
    if not display_config_info():
        return
    
    print("🎯 使用选项:")
    print("1. 测试AI评论服务: python test_ai_comment.py")
    print("2. 运行演示任务: 选择下面的选项")
    print("3. 自定义配置: 编辑config/tasks/ai_comment_demo.json")
    print()
    
    # 询问是否运行演示
    try:
        choice = input("是否现在运行AI评论演示任务？(y/N): ").strip().lower()
        
        if choice in ['y', 'yes']:
            print()
            asyncio.run(run_ai_comment_demo())
        else:
            print("\n💡 提示:")
            print("   运行演示: python demo_ai_comment.py")
            print("   直接使用: python autox.py --config ai_comment_demo")
            print()
    
    except KeyboardInterrupt:
        print("\n👋 再见！")

if __name__ == "__main__":
    main() 