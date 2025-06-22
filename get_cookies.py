#!/usr/bin/env python3
"""
Twitter账号登录并获取cookies的工具
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.browser.manager import BrowserManager
from src.core.twitter.client import TwitterClient
from src.core.account.manager import account_manager

async def login_and_save_cookies(account_id: str):
    """登录指定账号并保存cookies"""
    
    # 获取账号配置
    account = account_manager.get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        print("使用 'python manage_accounts.py --list' 查看可用账号")
        return False
    
    print(f"🔐 开始为账号 {account.account_id} (@{account.username}) 获取cookies...")
    print(f"邮箱: {account.email}")
    print(f"显示名: {account.display_name}")
    
    browser_manager = None
    try:
        # 启动浏览器
        print("🚀 启动浏览器...")
        browser_manager = BrowserManager()
        await browser_manager.start()
        
        # 创建Twitter客户端
        twitter_client = TwitterClient(browser_manager.page)
        
        # 检查是否已经登录
        print("🔍 检查登录状态...")
        if await twitter_client.check_login_status():
            print("✅ 检测到已登录状态")
            
            # 验证当前登录的账号是否是目标账号
            print("🔍 验证当前登录账号...")
            current_user = await twitter_client.get_current_user_info()
            
            if current_user and (current_user.get('username') or current_user.get('user_id')):
                current_username = current_user.get('username', '')
                current_user_id = current_user.get('user_id', '')
                
                print(f"当前登录账号: @{current_username}")
                if current_user_id:
                    print(f"当前账号ID: {current_user_id}")
                
                # 确定期望的用户名
                # 如果account_id看起来像用户名（不是纯数字），则优先使用account_id
                expected_username = account.account_id if not account.account_id.isdigit() else account.username
                
                print(f"期望账号: @{expected_username}")
                if account.account_id != expected_username:
                    print(f"配置账号ID: {account.account_id}")
                    print(f"配置用户名: @{account.username}")
                
                # 检查账号是否匹配
                username_match = current_username.lower() == expected_username.lower()
                
                if not username_match:
                    print(f"❌ 账号不匹配！")
                    print(f"   当前: @{current_username}")
                    if current_user_id:
                        print(f"   当前ID: {current_user_id}")
                    print(f"   期望: @{expected_username}")
                    
                    print("🔄 需要切换到目标账号，先登出当前账号...")
                    
                    # 强制登出当前账号
                    try:
                        await twitter_client.logout()
                        print("✅ 已登出当前账号")
                        await asyncio.sleep(3)  # 等待登出完成
                    except Exception as e:
                        print(f"⚠️  登出失败: {e}，继续尝试登录目标账号")
                    
                    # 重新登录目标账号
                    # 如果expected_username和配置的username不同，说明可能配置有误
                    if expected_username != account.username:
                        print(f"⚠️  检测到配置可能有误：account_id({account.account_id}) vs username({account.username})")
                        print(f"🔑 尝试以 @{expected_username} 身份登录...")
                        
                        # 尝试用expected_username作为用户名登录
                        success = await twitter_client.login(
                            username=expected_username,
                            password=account.password,
                            email=account.email
                        )
                        
                        if not success:
                            print(f"❌ 以 @{expected_username} 登录失败，尝试用配置的用户名 @{account.username} 登录...")
                            success = await twitter_client.login(
                                username=account.username,
                                password=account.password,
                                email=account.email
                            )
                    else:
                        print(f"🔑 开始登录目标账号 @{expected_username}...")
                        success = await twitter_client.login(
                            username=expected_username,
                            password=account.password,
                            email=account.email
                        )
                    
                    if not success:
                        print("❌ 登录目标账号失败")
                        return False
                        
                    print("✅ 成功登录目标账号")
                    final_username = expected_username
                else:
                    print("✅ 当前登录账号与期望账号匹配")
                    final_username = current_username
            else:
                print("⚠️  无法获取当前登录账号信息")
                
                # 确定期望的用户名
                expected_username = account.account_id if not account.account_id.isdigit() else account.username
                
                # 直接尝试重新登录目标账号
                print(f"🔄 无法验证账号，直接尝试登录期望账号 @{expected_username}...")
                try:
                    await twitter_client.logout()
                    print("✅ 已登出")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"⚠️  登出失败: {e}")
                
                # 重新登录
                success = await twitter_client.login(
                    username=expected_username,
                    password=account.password,
                    email=account.email
                )
                
                if not success and expected_username != account.username:
                    print(f"❌ 以 @{expected_username} 登录失败，尝试用配置的用户名 @{account.username}...")
                    success = await twitter_client.login(
                        username=account.username,
                        password=account.password,
                        email=account.email
                    )
                
                if not success:
                    print("❌ 登录失败")
                    return False
                
                # 设置最终用户名
                final_username = expected_username
        else:
            # 执行登录
            print("📝 开始登录流程...")
            print("⚠️  如果遇到验证码或其他人工验证，请在浏览器中手动完成")
            
            # 确定期望的用户名
            expected_username = account.account_id if not account.account_id.isdigit() else account.username
            
            success = await twitter_client.login(
                username=expected_username,
                password=account.password,
                email=account.email
            )
            
            if not success and expected_username != account.username:
                print(f"❌ 以 @{expected_username} 登录失败，尝试用配置的用户名 @{account.username}...")
                success = await twitter_client.login(
                    username=account.username,
                    password=account.password,
                    email=account.email
                )
            
            if not success:
                print("❌ 登录失败")
                return False
            
            final_username = expected_username
        
        # 最终验证：确保当前登录的是正确的账号
        print("🔍 最终验证登录账号...")
        final_user = await twitter_client.get_current_user_info()
        
        # 确定期望的用户名（与之前逻辑保持一致）
        expected_username = account.account_id if not account.account_id.isdigit() else account.username
        
        if final_user and final_user.get('username'):
            final_username = final_user['username']
            final_user_id = final_user.get('user_id', '')
            
            print(f"最终登录账号: @{final_username}")
            if final_user_id:
                print(f"最终账号ID: {final_user_id}")
            
            # 最终验证账号匹配
            final_username_match = final_username.lower() == expected_username.lower()
            
            if not final_username_match:
                print(f"❌ 最终验证失败：登录账号与期望账号不匹配")
                print(f"   当前: @{final_username}")
                if final_user_id:
                    print(f"   当前ID: {final_user_id}")
                print(f"   期望: @{expected_username}")
                
                # 如果期望的是account_id，但实际登录的不匹配，询问是否更新配置
                if expected_username == account.account_id and expected_username != account.username:
                    print(f"检测到可能的配置问题：")
                    print(f"  账号ID: {account.account_id}")
                    print(f"  配置用户名: @{account.username}")
                    print(f"  实际登录: @{final_username}")
                    
                    response = input(f"是否更新账号配置，将 {account.account_id} 的用户名从 @{account.username} 更新为 @{final_username}? (y/N): ").strip().lower()
                    if response == 'y':
                        # 更新账号配置
                        account.username = final_username
                        account.display_name = final_username
                        
                        # 保存更新后的配置
                        if account_manager.add_account(account):
                            print(f"✅ 账号配置已更新: {account.account_id} -> @{final_username}")
                            final_username = final_username  # 已经是正确的
                        else:
                            print("❌ 更新账号配置失败")
                            response = input("配置更新失败，是否仍要保存此账号的cookies? (y/N): ").strip().lower()
                            if response != 'y':
                                print("❌ 用户取消保存")
                                return False
                    else:
                        response = input("账号不匹配，是否仍要保存此账号的cookies? (y/N): ").strip().lower()
                        if response != 'y':
                            print("❌ 用户取消保存")
                            return False
                        else:
                            print("⚠️  用户选择继续保存，尽管账号不匹配")
                else:
                    response = input("账号不匹配，是否仍要保存此账号的cookies? (y/N): ").strip().lower()
                    if response != 'y':
                        print("❌ 用户取消保存")
                        return False
                    else:
                        print("⚠️  用户选择继续保存，尽管账号不匹配")
            else:
                print("✅ 最终账号验证通过")
        else:
            print("⚠️  无法获取最终登录账号信息，但将继续保存cookies")
            final_username = expected_username  # 使用期望的用户名
        
        # 确保cookies目录存在
        cookies_path = Path(account.cookies_file)
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存cookies
        print(f"💾 保存cookies到: {account.cookies_file}")
        success = await browser_manager.save_cookies(account.cookies_file)
        
        if success:
            print(f"✅ cookies保存成功！")
            print(f"📁 文件位置: {account.cookies_file}")
            print(f"🎯 已验证为账号: @{final_username}")
            
            # 验证cookies是否有效
            await asyncio.sleep(2)
            await browser_manager.page.goto("https://x.com/home", timeout=30000)
            await asyncio.sleep(3)
            
            # 再次验证登录状态和账号匹配
            if await twitter_client.check_login_status():
                verify_user = await twitter_client.get_current_user_info()
                if verify_user and verify_user.get('username', '').lower() == account.username.lower():
                    print("✅ cookies验证有效且账号匹配")
                    return True
                else:
                    print("⚠️  cookies可能有效但账号不匹配")
                    return False
            else:
                print("⚠️  cookies可能无效，请检查登录状态")
                return False
        else:
            print("❌ cookies保存失败")
            return False
            
    except Exception as e:
        print(f"❌ 获取cookies失败: {e}")
        return False
    finally:
        if browser_manager:
            print("🔄 关闭浏览器...")
            await browser_manager.close()

async def login_all_accounts():
    """为所有账号获取cookies"""
    accounts = account_manager.list_accounts()
    if not accounts:
        print("❌ 没有找到任何账号配置")
        print("请先使用 'python manage_accounts.py' 添加账号")
        return
    
    print(f"📋 找到 {len(accounts)} 个账号")
    
    for i, account in enumerate(accounts, 1):
        print(f"\n{'='*50}")
        print(f"处理账号 {i}/{len(accounts)}: {account.account_id}")
        
        success = await login_and_save_cookies(account.account_id)
        
        if success:
            print(f"✅ 账号 {account.account_id} 处理完成")
        else:
            print(f"❌ 账号 {account.account_id} 处理失败")
        
        # 账号间等待
        if i < len(accounts):
            print("⏰ 等待5秒后处理下一个账号...")
            await asyncio.sleep(5)
    
    print(f"\n🎉 所有账号处理完成！")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Twitter账号登录并获取cookies")
    parser.add_argument("--account-id", help="指定账号ID")
    parser.add_argument("--all", action="store_true", help="为所有账号获取cookies")
    parser.add_argument("--list", action="store_true", help="列出可用账号")
    
    args = parser.parse_args()
    
    if args.list:
        accounts = account_manager.list_accounts()
        if accounts:
            print("📋 可用账号:")
            for account in accounts:
                print(f"  - {account.account_id} (@{account.username})")
        else:
            print("❌ 没有找到任何账号配置")
        return
    
    if args.all:
        print("🔄 为所有账号获取cookies...")
        asyncio.run(login_all_accounts())
    elif args.account_id:
        print(f"🔄 为账号 {args.account_id} 获取cookies...")
        asyncio.run(login_and_save_cookies(args.account_id))
    else:
        # 交互式选择
        accounts = account_manager.list_accounts()
        if not accounts:
            print("❌ 没有找到任何账号配置")
            print("请先使用 'python manage_accounts.py' 添加账号")
            return
        
        print("📋 可用账号:")
        for i, account in enumerate(accounts, 1):
            print(f"  {i}. {account.account_id} (@{account.username})")
        
        while True:
            try:
                choice = input(f"\n请选择账号 (1-{len(accounts)}, 0=全部): ").strip()
                
                if choice == "0":
                    asyncio.run(login_all_accounts())
                    break
                elif choice.isdigit() and 1 <= int(choice) <= len(accounts):
                    account = accounts[int(choice) - 1]
                    asyncio.run(login_and_save_cookies(account.account_id))
                    break
                else:
                    print("❌ 无效选择，请重试")
            except KeyboardInterrupt:
                print("\n👋 再见!")
                break

if __name__ == "__main__":
    main() 