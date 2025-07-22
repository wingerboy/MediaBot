#!/usr/bin/env python3
"""
获取Twitter账号Cookies工具
同时作为账号管理的主要入口
"""
import asyncio
import argparse
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.browser.manager import BrowserManager
from src.core.twitter.client import TwitterClient
from src.core.account.manager import AccountManager, AccountConfig

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def get_and_save_cookies(account_id: str, force_relogin: bool = False):
    """获取指定账号的cookies并保存"""
    browser_manager = None
    twitter_client = None
    account_manager = AccountManager()
    
    try:
        print(f"🚀 开始获取账号 {account_id} 的cookies...")
        
        # 创建或获取账号配置
        account = account_manager.get_account(account_id)
        if not account:
            print(f"📝 创建新账号配置: {account_id}")
            account = account_manager.add_or_update_account(account_id)
        
        # 启动浏览器
        print("🚀 启动浏览器...")
        browser_manager = BrowserManager()
        success = await browser_manager.start(headless=False)
        if not success:
            print("❌ 浏览器启动失败")
            return False
        
        # 创建Twitter客户端
        twitter_client = TwitterClient(browser_manager.page)
        
        # 预热浏览器 - 模拟真实用户行为
        print("🔄 预热浏览器...")
        try:
            # 先访问一个无关网站，建立正常的浏览记录
            await browser_manager.page.goto("https://www.google.com", timeout=30000)
            await browser_manager.page.wait_for_load_state("domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            
            # 模拟一些鼠标移动
            await browser_manager.simulate_human_behavior()
            await asyncio.sleep(1)
            
            print("✅ 浏览器预热完成")
        except Exception as e:
            print(f"⚠️  浏览器预热失败，继续执行: {e}")
        
        # 检查登录状态
        need_login = True
        
        if not force_relogin:
            print("🔍 检查登录状态...")
            is_logged_in = await twitter_client.check_login_status()
            
            if is_logged_in:
                print("✅ 检测到已登录状态")
                response = input("是否要重新登录以获取最新cookie？(y/N): ").strip().lower()
                if response in ['y', 'yes']:
                    need_login = True
                    print("🔄 将执行重新登录...")
                else:
                    need_login = False
                    print("✅ 使用现有登录状态")
        else:
            print("🔄 强制重新登录模式...")
            need_login = True
        
        if need_login:
            print("📝 需要登录，请在浏览器中完成登录...")
            
            # 先清除现有cookie以确保重新登录
            if force_relogin:
                print("🧹 清除现有cookie...")
                await browser_manager.page.context.clear_cookies()
            
            # 导航到登录页面
            await browser_manager.page.goto("https://x.com/i/flow/login")
            await browser_manager.page.wait_for_load_state("domcontentloaded", timeout=10000)
            
            print("⚠️  完成登录后请按Enter键继续...")
            input("请在浏览器中完成登录，然后按Enter键继续...")
            
            # 再次检查登录状态
            is_logged_in = await twitter_client.check_login_status()
            
            if not is_logged_in:
                print("❌ 登录验证失败")
                return False
            
            print("✅ 登录状态验证成功")
        else:
            print("✅ 跳过登录，使用现有状态")
        
        # 获取用户信息
        try:
            print("📋 获取用户信息...")
            await browser_manager.page.goto("https://x.com/home", timeout=15000)
            await browser_manager.page.wait_for_load_state("domcontentloaded", timeout=10000)
            
            # 尝试获取用户名和显示名
            username = ""
            display_name = ""
            email = ""
            
            try:
                # 尝试多种方式获取用户信息
                selectors = [
                    '[data-testid="SideNav_AccountSwitcher_Button"] [dir="ltr"]',
                    '[data-testid="SideNav_AccountSwitcher_Button"] span:not([dir])',
                    '[data-testid="AppTabBar_Profile_Link"] span',
                    'a[href*="/"] span[dir="ltr"]'
                ]
                
                for selector in selectors:
                    try:
                        elements = await browser_manager.page.query_selector_all(selector)
                        for element in elements:
                            text = await element.text_content()
                            if text and text.strip() and not text.startswith('@') and len(text) > 1:
                                if not display_name:
                                    display_name = text.strip()
                                break
                        if display_name:
                            break
                    except:
                        continue
                
                # 获取用户名（@xxx格式）
                username_selectors = [
                    '[data-testid="SideNav_AccountSwitcher_Button"] [dir="ltr"]',
                    'a[href^="/"][href!="/home"][href!="/explore"] span'
                ]
                
                for selector in username_selectors:
                    try:
                        elements = await browser_manager.page.query_selector_all(selector)
                        for element in elements:
                            text = await element.text_content()
                            if text and text.startswith('@'):
                                username = text.strip()[1:]  # 去掉@符号
                                break
                        if username:
                            break
                    except:
                        continue
                
                # 如果没有获取到，使用默认值
                if not username:
                    username = account_id
                if not display_name:
                    display_name = account_id
                
                print(f"👤 用户名: {username}")
                print(f"📝 显示名: {display_name}")
                
            except Exception as e:
                print(f"⚠️  获取用户信息失败，使用默认值: {e}")
                username = account_id
                display_name = account_id
            
        except Exception as e:
            print(f"⚠️  获取用户信息失败: {e}")
            username = account_id
            display_name = account_id
        
        # 保存cookies
        cookies_file = f"data/cookies/cookies_{account_id}.json"
        print(f"💾 保存cookies到: {cookies_file}")
        
        success = await browser_manager.save_cookies(cookies_file)
        if not success:
            print("❌ cookies保存失败")
            return False
        
        print("✅ cookies保存成功")
        
        # 更新账号信息
        print("📝 更新账号信息...")
        account_manager.add_or_update_account(
            account_id=account_id,
            username=username,
            display_name=display_name,
            email=email,
            cookies_file=cookies_file
        )
        
        print(f"✅ 账号 {account_id} 设置完成!")
        print(f"   用户名: @{username}")
        print(f"   显示名: {display_name}")
        print(f"   Cookies: {cookies_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取cookies失败: {e}")
        return False
        
    finally:
        if browser_manager:
            print("🔄 关闭浏览器...")
            await browser_manager.close()

def list_accounts():
    """列出所有账号"""
    account_manager = AccountManager()
    accounts = account_manager.list_accounts()
    
    if not accounts:
        print("❌ 未找到任何账号配置")
        return
    
    print(f"📋 账号列表 (共 {len(accounts)} 个)")
    print("=" * 60)
    
    for account in accounts:
        status = "🟢 活跃" if account.is_active else "🔴 禁用"
        cookies_status = "✅" if Path(account.cookies_file).exists() else "❌"
        
        print(f"📱 {account.account_id}")
        print(f"   用户名: @{account.username}")
        print(f"   显示名: {account.display_name}")
        print(f"   状态: {status}")
        print(f"   Cookies: {cookies_status} {account.cookies_file}")
        print(f"   使用次数: {account.usage_count}")
        print()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Twitter账号Cookie获取工具")
    parser.add_argument("account_id", nargs="?", help="账号ID")
    parser.add_argument("--list", action="store_true", help="列出所有账号")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新登录，清除现有cookie")
    
    args = parser.parse_args()
    
    if args.list:
        list_accounts()
        return
    
    if not args.account_id:
        print("使用方法:")
        print("  python get_cookies.py <account_id>         # 获取指定账号的cookies")
        print("  python get_cookies.py <account_id> --force # 强制重新登录获取cookies")
        print("  python get_cookies.py --list               # 列出所有账号")
        return
    
    success = await get_and_save_cookies(args.account_id, force_relogin=args.force)
    if success:
        print("🎉 操作完成!")
    else:
        print("💥 操作失败!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 