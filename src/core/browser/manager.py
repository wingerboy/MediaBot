"""
浏览器管理器
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

from ...utils.logger import log
from ...utils.storage import storage
from config.settings import settings

class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def start(self):
        """启动浏览器"""
        try:
            log.info("正在启动浏览器...")
            
            self.playwright = await async_playwright().start()
            
            # 选择浏览器类型
            if settings.BROWSER_TYPE == "firefox":
                browser_type = self.playwright.firefox
            elif settings.BROWSER_TYPE == "webkit":
                browser_type = self.playwright.webkit
            else:
                browser_type = self.playwright.chromium
            
            # 启动浏览器
            self.browser = await browser_type.launch(
                headless=settings.HEADLESS,
                args=[
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-ipc-flooding-protection',
                    '--disable-hang-monitor',
                    '--disable-client-side-phishing-detection',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--disable-translate',
                    '--disable-extensions',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-background-networking',
                    '--disable-default-apps',
                    '--disable-component-extensions-with-background-pages'
                ]
            )
            
            # 创建上下文
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': settings.USER_AGENT or self._get_random_user_agent(),
                'java_script_enabled': True,
                'accept_downloads': True,
                'ignore_https_errors': True,
                'permissions': ['geolocation', 'notifications'],
                'color_scheme': 'light',
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'max-age=0',
                }
            }
            
            self.context = await self.browser.new_context(**context_options)
            
            # 加载cookies
            await self._load_cookies()
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 应用反检测
            if settings.ENABLE_STEALTH:
                stealth = Stealth()
                await stealth.apply_stealth_async(self.page)
            
            # 设置页面超时
            self.page.set_default_timeout(settings.PAGE_LOAD_TIMEOUT)
            
            log.info("浏览器启动成功")
            
        except Exception as e:
            log.error(f"启动浏览器失败: {e}")
            await self.close()
            raise
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                # 保存cookies
                await self._save_cookies()
                await self.context.close()
            
            if self.browser:
                await self.browser.close()
            
            if self.playwright:
                await self.playwright.stop()
                
            log.info("浏览器已关闭")
            
        except Exception as e:
            log.error(f"关闭浏览器失败: {e}")
    
    async def new_page(self) -> Page:
        """创建新页面"""
        if not self.context:
            raise Exception("浏览器未启动")
        
        page = await self.context.new_page()
        if settings.ENABLE_STEALTH:
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
        
        return page
    
    async def random_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None):
        """随机延迟"""
        min_delay = min_delay or settings.MIN_DELAY
        max_delay = max_delay or settings.MAX_DELAY
        
        delay = random.uniform(min_delay, max_delay)
        log.debug(f"随机延迟 {delay:.2f} 秒")
        await asyncio.sleep(delay)
    
    async def _load_cookies(self):
        """加载cookies"""
        try:
            cookies = storage.load_cookies("twitter_cookies")
            if cookies:
                await self.context.add_cookies(cookies)
                log.info("已加载保存的cookies")
        except Exception as e:
            log.warning(f"加载cookies失败: {e}")
    
    async def _save_cookies(self):
        """保存cookies"""
        try:
            if self.context:
                cookies = await self.context.cookies()
                storage.save_cookies(cookies, "twitter_cookies")
                log.info("已保存cookies")
        except Exception as e:
            log.warning(f"保存cookies失败: {e}")
    
    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
        ]
        return random.choice(user_agents)
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 