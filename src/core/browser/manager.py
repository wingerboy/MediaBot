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
        self.user_data_dir = storage.get_data_dir() / "browser_data"
        self.logger = log  # 使用全局logger
    
    async def start(self, headless: bool = True, width: int = 1920, height: int = 1080):
        """启动浏览器"""
        try:
            # 启动playwright
            self.playwright = await async_playwright().start()
            
            # 确保用户数据目录存在
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 清理残留的锁文件
            self._cleanup_browser_files()
            
            # 获取随机User-Agent
            user_agent = self._get_random_user_agent()
            
            # 配置浏览器启动参数 - 最小化反检测
            args = [
                '--no-sandbox',
                '--no-first-run',
                '--no-default-browser-check',
                '--password-store=basic',
                '--use-mock-keychain',
                '--start-maximized',
                f'--window-size={width},{height}',
                f'--user-agent={user_agent}'
            ]
            
            # 如果是headless模式，避免检测
            if headless:
                args.extend([
                    '--headless=new',  # 使用新的headless模式
                ])
            
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=headless,
                args=args,
                viewport={'width': width, 'height': height},
                user_agent=user_agent,
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # 创建新页面
            self.page = await self.context.new_page()
            
            # 设置页面配置
            await self.page.set_viewport_size({'width': width, 'height': height})
            
            # 基本的反检测脚本
            await self.page.add_init_script("""
                // 隐藏webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            

            
            self.logger.info("Browser started successfully with enhanced stealth mode")
            
            # 添加Cookie弹窗处理器
            await self._setup_cookie_handler()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            return False
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                # 保存cookies
                try:
                    await self._save_cookies()
                except Exception as e:
                    log.warning(f"保存cookies失败: {e}")
                
                try:
                    await self.context.close()
                except Exception as e:
                    log.warning(f"关闭浏览器上下文失败: {e}")
            
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    log.warning(f"关闭浏览器失败: {e}")
            
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    log.warning(f"停止playwright失败: {e}")
            
            # 清理锁文件
            self._cleanup_browser_files()
                
            log.info("浏览器已关闭")
            
        except Exception as e:
            log.error(f"关闭浏览器失败: {e}")
    
    def _cleanup_browser_files(self):
        """清理浏览器相关文件"""
        try:
            import os
            import shutil
            from pathlib import Path
            
            # 清理SingletonLock文件
            singleton_lock = self.user_data_dir / "SingletonLock"
            if singleton_lock.exists():
                try:
                    singleton_lock.unlink()
                    log.debug("已清理SingletonLock文件")
                except Exception as e:
                    log.debug(f"清理SingletonLock文件失败: {e}")
            
            # 清理其他临时文件
            temp_files = [
                "SingletonCookie",
                "SingletonSocket",
                ".com.google.Chrome.XXXXXX"
            ]
            
            for temp_file in temp_files:
                temp_path = self.user_data_dir / temp_file
                if temp_path.exists():
                    try:
                        if temp_path.is_file():
                            temp_path.unlink()
                        elif temp_path.is_dir():
                            shutil.rmtree(temp_path)
                        log.debug(f"已清理临时文件: {temp_file}")
                    except Exception as e:
                        log.debug(f"清理临时文件失败 {temp_file}: {e}")
                        
        except Exception as e:
            log.debug(f"清理浏览器文件失败: {e}")
    
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
    
    async def simulate_human_behavior(self):
        """模拟人类行为"""
        try:
            if not self.page:
                return
            
            # 随机鼠标移动
            await self._simulate_mouse_movement()
            
            # 随机滚动
            if random.random() < 0.3:  # 30%概率
                await self._simulate_random_scroll()
            
            # 随机短暂停留
            if random.random() < 0.2:  # 20%概率
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        except Exception as e:
            log.debug(f"模拟人类行为失败: {e}")
    
    async def _simulate_mouse_movement(self):
        """模拟真实的鼠标移动"""
        try:
            viewport = await self.page.viewport_size()
            if not viewport:
                return
            
            # 生成随机鼠标路径
            start_x = random.randint(50, viewport['width'] - 50)
            start_y = random.randint(50, viewport['height'] - 50)
            end_x = random.randint(50, viewport['width'] - 50)
            end_y = random.randint(50, viewport['height'] - 50)
            
            # 分步移动，模拟真实鼠标轨迹
            steps = random.randint(5, 15)
            for i in range(steps):
                progress = i / steps
                current_x = start_x + (end_x - start_x) * progress
                current_y = start_y + (end_y - start_y) * progress
                
                # 添加随机抖动
                jitter_x = random.uniform(-5, 5)
                jitter_y = random.uniform(-5, 5)
                
                await self.page.mouse.move(
                    current_x + jitter_x, 
                    current_y + jitter_y
                )
                await asyncio.sleep(random.uniform(0.01, 0.05))
                
        except Exception as e:
            log.debug(f"模拟鼠标移动失败: {e}")
    
    async def _simulate_random_scroll(self):
        """模拟随机滚动"""
        try:
            # 随机滚动方向和距离
            scroll_delta = random.randint(-300, 300)
            await self.page.mouse.wheel(0, scroll_delta)
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
        except Exception as e:
            log.debug(f"模拟滚动失败: {e}")
    
    async def safe_click(self, selector: str, timeout: int = 5000):
        """安全点击，包含人类行为模拟"""
        try:
            # 先模拟人类行为
            await self.simulate_human_behavior()
            
            # 等待元素可见
            await self.page.wait_for_selector(selector, timeout=timeout)
            
            # 获取元素位置
            element = self.page.locator(selector)
            box = await element.bounding_box()
            
            if box:
                # 在元素范围内随机点击位置
                click_x = box['x'] + random.uniform(0.3, 0.7) * box['width']
                click_y = box['y'] + random.uniform(0.3, 0.7) * box['height']
                
                # 先移动鼠标到目标位置
                await self.page.mouse.move(click_x, click_y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # 执行点击
                await self.page.mouse.click(click_x, click_y)
                
                # 点击后随机延迟
                await asyncio.sleep(random.uniform(0.2, 0.8))
                
                return True
            else:
                # 降级到普通点击
                await element.click()
                return True
                
        except Exception as e:
            log.debug(f"安全点击失败: {e}")
            return False
    
    async def safe_type(self, selector: str, text: str, timeout: int = 5000):
        """安全输入，模拟真实打字速度"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            element = self.page.locator(selector)
            
            # 清空现有内容
            await element.click()
            await self.page.keyboard.press('Control+a')
            
            # 模拟真实打字速度
            for char in text:
                await self.page.keyboard.type(char)
                # 随机打字间隔
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # 打字完成后的随机延迟
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            return True
            
        except Exception as e:
            log.debug(f"安全输入失败: {e}")
            return False
    
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
    
    async def load_cookies(self, cookies_file: str):
        """从指定文件加载cookies"""
        try:
            import json
            from pathlib import Path
            
            cookies_path = Path(cookies_file)
            if cookies_path.exists():
                with open(cookies_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                if self.context and cookies:
                    await self.context.add_cookies(cookies)
                    log.info(f"已从 {cookies_file} 加载cookies")
                    return True
            else:
                log.warning(f"Cookies文件不存在: {cookies_file}")
                return False
        except Exception as e:
            log.warning(f"从文件加载cookies失败: {e}")
            return False
    
    async def save_cookies(self, cookies_file: str):
        """保存cookies到指定文件"""
        try:
            import json
            from pathlib import Path
            
            if self.context:
                cookies = await self.context.cookies()
                
                # 确保目录存在
                cookies_path = Path(cookies_file)
                cookies_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(cookies_path, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, indent=2, ensure_ascii=False)
                
                log.info(f"已保存cookies到 {cookies_file}")
                return True
        except Exception as e:
            log.warning(f"保存cookies到文件失败: {e}")
            return False
    
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
    
    async def _setup_cookie_handler(self):
        """设置Cookie弹窗自动处理器"""
        try:
            # 监听页面加载完成事件
            self.page.on("domcontentloaded", self._handle_cookie_popup)
            self.logger.info("Cookie弹窗处理器已设置")
        except Exception as e:
            self.logger.warning(f"设置Cookie弹窗处理器失败: {e}")
    
    async def _handle_cookie_popup(self, page):
        """处理Cookie同意弹窗"""
        try:
            # 等待一小段时间让弹窗完全加载
            await asyncio.sleep(1)
            
            # 检查是否存在Cookie同意遮罩层
            cookie_mask = page.locator('[data-testid="twc-cc-mask"]')
            if await cookie_mask.count() > 0:
                self.logger.info("检测到Cookie同意弹窗，尝试处理...")
                
                # 尝试多种方式关闭Cookie弹窗
                success = await self._dismiss_cookie_popup(page)
                
                if success:
                    self.logger.info("✅ Cookie弹窗已成功关闭")
                    # 再等待一下确保弹窗完全消失
                    await asyncio.sleep(2)
                else:
                    self.logger.warning("❌ 无法关闭Cookie弹窗，可能影响后续操作")
                    
        except Exception as e:
            self.logger.debug(f"处理Cookie弹窗时出错: {e}")
    
    async def _dismiss_cookie_popup(self, page) -> bool:
        """尝试关闭Cookie弹窗的多种方法"""
        methods = [
            self._method_accept_all_cookies,
            self._method_close_button,
            self._method_escape_key,
            self._method_click_outside,
            self._method_remove_mask
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                self.logger.debug(f"尝试方法 {i}: {method.__name__}")
                success = await method(page)
                if success:
                    return True
                await asyncio.sleep(1)  # 方法间间隔
            except Exception as e:
                self.logger.debug(f"方法 {i} 失败: {e}")
                continue
        
        return False
    
    async def _method_accept_all_cookies(self, page) -> bool:
        """方法1：点击接受所有Cookie按钮"""
        selectors = [
            '[data-testid="BottomBar"] button:has-text("Accept all cookies")',
            '[data-testid="BottomBar"] button:has-text("接受所有Cookie")',
            'button:has-text("Accept all cookies")',
            'button:has-text("接受所有Cookie")',
            'button:has-text("Accept")',
            'button:has-text("接受")',
            '[data-testid="BottomBar"] button[role="button"]',
        ]
        
        for selector in selectors:
            try:
                button = page.locator(selector)
                if await button.count() > 0:
                    await button.first.click(timeout=3000)
                    await asyncio.sleep(1)
                    # 检查遮罩是否消失
                    if await page.locator('[data-testid="twc-cc-mask"]').count() == 0:
                        return True
            except Exception as e:
                self.logger.debug(f"接受Cookie按钮点击失败 {selector}: {e}")
                continue
        return False
    
    async def _method_close_button(self, page) -> bool:
        """方法2：点击关闭按钮"""
        selectors = [
            '[data-testid="BottomBar"] button[aria-label*="close"]',
            '[data-testid="BottomBar"] button[aria-label*="关闭"]',
            '[data-testid="BottomBar"] svg[data-testid="icon-x"]',
            'button[aria-label="Close"]',
            'button[aria-label="关闭"]'
        ]
        
        for selector in selectors:
            try:
                button = page.locator(selector)
                if await button.count() > 0:
                    await button.first.click(timeout=3000)
                    await asyncio.sleep(1)
                    if await page.locator('[data-testid="twc-cc-mask"]').count() == 0:
                        return True
            except Exception as e:
                self.logger.debug(f"关闭按钮点击失败 {selector}: {e}")
                continue
        return False
    
    async def _method_escape_key(self, page) -> bool:
        """方法3：按ESC键"""
        try:
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            return await page.locator('[data-testid="twc-cc-mask"]').count() == 0
        except Exception as e:
            self.logger.debug(f"ESC键失败: {e}")
            return False
    
    async def _method_click_outside(self, page) -> bool:
        """方法4：点击遮罩外部区域"""
        try:
            # 点击页面左上角
            await page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
            await asyncio.sleep(1)
            return await page.locator('[data-testid="twc-cc-mask"]').count() == 0
        except Exception as e:
            self.logger.debug(f"点击外部区域失败: {e}")
            return False
    
    async def _method_remove_mask(self, page) -> bool:
        """方法5：直接移除遮罩层（最后手段）"""
        try:
            await page.evaluate("""
                const masks = document.querySelectorAll('[data-testid="twc-cc-mask"]');
                masks.forEach(mask => mask.remove());
                
                const layers = document.querySelectorAll('#layers > div');
                layers.forEach(layer => {
                    if (layer.style.position === 'fixed' || 
                        layer.classList.contains('r-1pi2tsx') ||
                        layer.classList.contains('r-1d2f490')) {
                        layer.remove();
                    }
                });
            """)
            await asyncio.sleep(1)
            return await page.locator('[data-testid="twc-cc-mask"]').count() == 0
        except Exception as e:
            self.logger.debug(f"移除遮罩失败: {e}")
            return False 