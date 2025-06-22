#!/usr/bin/env python3
"""
多账号管理工具
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.account.manager import AccountConfig, account_manager

def add_account():
    """添加账号"""
    print("添加新账号")
    print("=" * 40)
    
    account_id = input("账号ID (唯一标识): ").strip()
    if not account_id:
        print("❌ 账号ID不能为空")
        return False
    
    username = input("Twitter用户名: ").strip()
    display_name = input("显示名称: ").strip()
    email = input("邮箱: ").strip()
    password = input("密码: ").strip()
    
    # cookies文件路径
    cookies_file = f"data/cookies/cookies_{account_id}.json"
    print(f"Cookies文件路径: {cookies_file}")
    
    notes = input("备注 (可选): ").strip()
    
    account = AccountConfig(
        account_id=account_id,
        username=username,
        display_name=display_name,
        email=email,
        password=password,
        cookies_file=cookies_file,
        notes=notes
    )
    
    if account_manager.add_account(account):
        print(f"✅ 账号 {account_id} 添加成功!")
        print(f"请手动登录获取cookies并保存到: {cookies_file}")
        return True
    else:
        print(f"❌ 账号 {account_id} 添加失败!")
        return False

def list_accounts():
    """列出所有账号"""
    accounts = account_manager.list_accounts()
    
    if not accounts:
        print("❌ 未找到任何账号配置")
        return
    
    print(f"📋 账号列表 (共 {len(accounts)} 个)")
    print("=" * 80)
    
    for account in accounts:
        status = "🟢 活跃" if account.is_active else "🔴 禁用"
        
        # 检查可用性
        available = "✅ 可用" if account.is_available() else "⏰ 冷却中"
        
        # 最后使用时间
        last_used = "从未使用"
        if account.last_used:
            try:
                last_time = datetime.fromisoformat(account.last_used)
                last_used = last_time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                last_used = account.last_used
        
        # 冷却结束时间
        cooldown_info = ""
        if account.cooldown_until:
            try:
                cooldown_time = datetime.fromisoformat(account.cooldown_until)
                if datetime.now() < cooldown_time:
                    cooldown_info = f" (冷却至: {cooldown_time.strftime('%H:%M:%S')})"
            except:
                cooldown_info = f" (冷却至: {account.cooldown_until})"
        
        print(f"📱 {account.account_id} (@{account.username})")
        print(f"   状态: {status} | {available}{cooldown_info}")
        print(f"   显示名: {account.display_name}")
        print(f"   邮箱: {account.email}")
        print(f"   使用次数: {account.usage_count} | 最后使用: {last_used}")
        print(f"   Cookies: {account.cookies_file}")
        if account.notes:
            print(f"   备注: {account.notes}")
        print()

def show_stats():
    """显示统计信息"""
    stats = account_manager.get_account_stats()
    
    print("📊 账号统计")
    print("=" * 30)
    print(f"总账号数: {stats['total']}")
    print(f"活跃账号: {stats['active']}")
    print(f"可用账号: {stats['available']}")
    print(f"冷却中账号: {stats['in_cooldown']}")

def toggle_account_status():
    """切换账号状态"""
    account_id = input("请输入账号ID: ").strip()
    if not account_id:
        print("❌ 账号ID不能为空")
        return
    
    account = account_manager.get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        return
    
    new_status = not account.is_active
    account_manager.set_account_status(account_id, new_status)
    
    status_text = "激活" if new_status else "禁用"
    print(f"✅ 账号 {account_id} 已{status_text}")

def clear_cooldowns():
    """清除所有冷却"""
    confirm = input("确认清除所有账号的冷却时间? (y/N): ").strip().lower()
    if confirm == 'y':
        account_manager.clear_cooldowns()
        print("✅ 已清除所有账号的冷却时间")
    else:
        print("❌ 操作已取消")

def remove_account():
    """删除账号"""
    account_id = input("请输入要删除的账号ID: ").strip()
    if not account_id:
        print("❌ 账号ID不能为空")
        return
    
    account = account_manager.get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        return
    
    print(f"账号信息: {account.account_id} (@{account.username})")
    confirm = input("确认删除此账号? (y/N): ").strip().lower()
    if confirm == 'y':
        if account_manager.remove_account(account_id):
            print(f"✅ 账号 {account_id} 删除成功")
        else:
            print(f"❌ 账号 {account_id} 删除失败")
    else:
        print("❌ 操作已取消")

def interactive_menu():
    """交互式菜单"""
    while True:
        print("\n🔧 多账号管理工具")
        print("=" * 30)
        print("1. 添加账号")
        print("2. 列出账号")
        print("3. 显示统计")
        print("4. 切换账号状态")
        print("5. 清除冷却时间")
        print("6. 删除账号")
        print("0. 退出")
        print()
        
        choice = input("请选择操作 (0-6): ").strip()
        
        if choice == '1':
            add_account()
        elif choice == '2':
            list_accounts()
        elif choice == '3':
            show_stats()
        elif choice == '4':
            toggle_account_status()
        elif choice == '5':
            clear_cooldowns()
        elif choice == '6':
            remove_account()
        elif choice == '0':
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重试")
        
        input("\n按Enter键继续...")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多账号管理工具")
    parser.add_argument("--list", action="store_true", help="列出所有账号")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--add", action="store_true", help="添加账号")
    parser.add_argument("--clear-cooldowns", action="store_true", help="清除所有冷却")
    
    args = parser.parse_args()
    
    if args.list:
        list_accounts()
    elif args.stats:
        show_stats()
    elif args.add:
        add_account()
    elif args.clear_cooldowns:
        clear_cooldowns()
    else:
        # 启动交互式菜单
        interactive_menu()

if __name__ == "__main__":
    main() 