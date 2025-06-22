#!/usr/bin/env python3
"""
MediaBot - Twitter 自动化机器人
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.browser.manager import BrowserManager
from src.features.browse.timeline import TimelineBrowser
from src.utils.logger import log
from config.settings import settings

class MediaBot:
    """MediaBot 主类"""
    
    def __init__(self):
        self.browser_manager = None
        self.timeline_browser = None
    
    async def start(self):
        """启动机器人"""
        try:
            log.info("=== MediaBot 启动 ===")
            
            # 启动浏览器
            self.browser_manager = BrowserManager()
            await self.browser_manager.start()
            
            # 初始化功能模块
            self.timeline_browser = TimelineBrowser(self.browser_manager)
            
            log.info("MediaBot 启动成功")
            
        except Exception as e:
            log.error(f"启动失败: {e}")
            await self.close()
            raise
    
    async def close(self):
        """关闭机器人"""
        try:
            if self.browser_manager:
                await self.browser_manager.close()
            
            log.info("=== MediaBot 已关闭 ===")
            
        except Exception as e:
            log.error(f"关闭失败: {e}")
    
    async def browse_timeline(self, auto_interact: bool = False) -> list:
        """浏览时间线"""
        if not self.timeline_browser:
            raise Exception("未初始化时间线浏览器")
        
        return await self.timeline_browser.start_browsing(auto_interact=auto_interact)
    
    async def search_tweets(self, query: str, count: int = 10) -> list:
        """搜索推文"""
        if not self.timeline_browser:
            raise Exception("未初始化时间线浏览器")
        
        return await self.timeline_browser.search_tweets(query, count)
    
    async def run_test_mode(self):
        """运行测试模式 - 不直接访问X.com"""
        try:
            await self.start()
            
            log.info("=== 测试模式：验证基础功能 ===")
            
            # 测试1：访问普通网站验证浏览器功能
            log.info("测试1：验证浏览器基础功能")
            await self.browser_manager.page.goto("https://httpbin.org/headers")
            await self.browser_manager.page.wait_for_load_state("networkidle")
            
            content = await self.browser_manager.page.content()
            if "User-Agent" in content:
                log.info("✅ 浏览器基础功能正常")
            
            # 测试2：验证反检测功能
            log.info("测试2：验证反检测功能")
            await self.browser_manager.page.goto("https://bot.sannysoft.com/")
            await self.browser_manager.page.wait_for_load_state("networkidle")
            await self.browser_manager.page.screenshot(path="antibot_test.png")
            log.info("已保存反检测测试截图: antibot_test.png")
            
            # 测试3：验证stealth功能
            log.info("测试3：检查webdriver检测")
            webdriver_detected = await self.browser_manager.page.evaluate("() => navigator.webdriver")
            log.info(f"WebDriver检测结果: {webdriver_detected}")
            
            if webdriver_detected is None:
                log.info("✅ WebDriver标识已成功隐藏")
            else:
                log.warning("⚠️ WebDriver标识仍然可见")
            
            # 测试4：简单访问Twitter看状态
            log.info("测试4：尝试访问Twitter登录页")
            try:
                await self.browser_manager.page.goto("https://twitter.com/i/flow/login", timeout=15000)
                await self.browser_manager.page.wait_for_load_state("networkidle", timeout=10000)
                
                page_url = self.browser_manager.page.url
                page_title = await self.browser_manager.page.title()
                
                log.info(f"访问结果 - URL: {page_url}")
                log.info(f"访问结果 - 标题: {page_title}")
                
                if "login" in page_url.lower() or "log in" in page_title.lower():
                    log.info("✅ 成功访问Twitter登录页")
                else:
                    log.warning("⚠️ 可能被重定向或拦截")
                
                await self.browser_manager.page.screenshot(path="twitter_test.png")
                log.info("已保存Twitter访问截图: twitter_test.png")
                
            except Exception as e:
                log.error(f"访问Twitter失败: {e}")
            
            await self.close()
            
        except Exception as e:
            log.error(f"测试失败: {e}")
            if 'self' in locals():
                await self.close()

    async def run_demo(self):
        """运行演示"""
        try:
            await self.start()
            
            log.info("=== 实际使用建议 ===")
            log.info("由于X.com的严格反机器人检测，建议:")
            log.info("1. 手动登录一次，保存cookies")
            log.info("2. 使用已登录状态进行后续操作")
            log.info("3. 降低操作频率，模拟人工行为")
            log.info("4. 考虑使用代理IP轮换")
            log.info("开始演示：智能访问策略")
            
            # 第二步：访问Twitter主页
            log.info("第二步：访问Twitter主页")
            await self.browser_manager.page.goto("https://x.com")
            await self.browser_manager.page.wait_for_load_state("networkidle")
            await self.browser_manager.random_delay(3, 5)
            
            log.info(f"当前URL: {self.browser_manager.page.url}")
            log.info(f"页面标题: {await self.browser_manager.page.title()}")
            
            # 检查是否需要处理cookie同意
            try:
                cookie_button = self.browser_manager.page.locator('div[data-testid="BottomBar"] button')
                if await cookie_button.is_visible(timeout=3000):
                    await cookie_button.click()
                    log.info("已处理cookie同意弹窗")
            except:
                pass
            
            # 第三步：尝试访问主页
            log.info("第三步：尝试访问x.com主页")
            await self.browser_manager.page.goto("https://x.com/home")
            await self.browser_manager.page.wait_for_load_state("networkidle")
            
            log.info(f"最终URL: {self.browser_manager.page.url}")
            log.info(f"最终标题: {await self.browser_manager.page.title()}")
            
            # 截图调试
            await self.browser_manager.page.screenshot(path="debug_final.png")
            log.info("已保存最终截图: debug_final.png")
            
            # 检查页面内容
            page_content = await self.browser_manager.page.content()
            if "Something went wrong" in page_content:
                log.error("仍然被反机器人检测，需要更高级的策略")
                
                # 尝试手动等待和刷新
                log.info("尝试等待30秒后刷新页面")
                await self.browser_manager.random_delay(30, 35)
                await self.browser_manager.page.reload()
                await self.browser_manager.page.wait_for_load_state("networkidle")
                
                page_content2 = await self.browser_manager.page.content()
                if "Something went wrong" not in page_content2:
                    log.info("刷新后页面正常了")
                else:
                    log.error("刷新后仍有问题，可能需要人工验证")
            else:
                log.info("页面访问成功，开始获取推文")
                tweets = await self.timeline_browser.start_browsing()
                log.info(f"获取到 {len(tweets)} 条推文")
                
                for tweet in tweets[:3]:  # 显示前3条
                    log.info(f"推文: {tweet.get('username', 'Unknown')} - {tweet.get('content', '')[:50]}...")
            
            await self.close()
            
        except Exception as e:
            log.error(f"演示失败: {e}")
            if 'self' in locals():
                await self.close()

async def run_test_mode():
    """运行测试模式 - 不直接访问X.com"""
    try:
        app = MediaBot()
        await app.run_test_mode()
    except Exception as e:
        log.error(f"测试失败: {e}")

async def run_demo():
    """运行演示"""
    try:
        app = MediaBot()
        await app.run_demo()
    except Exception as e:
        log.error(f"演示失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(run_demo())
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(run_test_mode())
    else:
        print("使用方法:")
        print("  python main.py demo  - 运行演示")
        print("  python main.py test  - 运行测试模式") 