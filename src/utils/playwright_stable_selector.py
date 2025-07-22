"""
基于真实验证的Twitter选择器
使用已在test_real_interactions.py中验证有效的data-testid和上下文识别策略
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)

class PlaywrightStableSelector:
    """基于真实验证的Twitter元素选择器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.default_timeout = 10000
    
    async def wait_for_tweets_loaded(self, max_wait_seconds: int = 15) -> bool:
        """等待推文加载完成 - 基于验证发现需要7-8秒"""
        logger.info("等待推文内容加载...")
        
        for second in range(max_wait_seconds):
            try:
                tweet_count = await self.page.locator('article[data-testid="tweet"]').count()
                if tweet_count > 0:
                    logger.info(f"第{second+1}秒: 发现 {tweet_count} 个推文")
                    # 再等2秒确保稳定
                    await asyncio.sleep(2)
                    return True
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"等待推文时出错: {e}")
                await asyncio.sleep(1)
        
        logger.warning(f"{max_wait_seconds}秒内未发现推文")
        return False

    async def find_tweet_containers(self, limit: int = 10) -> List[Locator]:
        """查找推文容器 - 使用验证有效的选择器"""
        try:
            # 基于验证，article[data-testid="tweet"] 是最可靠的
            containers = await self.page.locator('article[data-testid="tweet"]').all()
            if containers:
                logger.info(f"找到 {len(containers)} 个推文容器")
                return containers[:limit]
            else:
                logger.warning("未找到推文容器")
                return []
        except Exception as e:
            logger.error(f"查找推文容器失败: {e}")
            return []

    async def find_reply_button(self, tweet_container: Optional[Locator] = None) -> Optional[Locator]:
        """查找回复按钮 - 使用验证有效的方法"""
        base = tweet_container or self.page
        
        try:
            # 验证最有效的选择器: [data-testid="reply"]
            reply_button = base.locator('[data-testid="reply"]').first
            
            if await reply_button.is_visible():
                logger.debug("通过data-testid找到回复按钮")
                return reply_button
            else:
                logger.warning("回复按钮不可见")
                return None
                
        except Exception as e:
            logger.error(f"查找回复按钮失败: {e}")
            return None

    async def find_like_button(self, tweet_container: Optional[Locator] = None) -> Optional[Locator]:
        """查找点赞按钮 - 使用验证有效的方法"""
        base = tweet_container or self.page
        
        try:
            # 验证最有效的选择器: [data-testid="like"]
            like_button = base.locator('[data-testid="like"]').first
            
            if await like_button.is_visible():
                logger.debug("通过data-testid找到点赞按钮")
                return like_button
            else:
                logger.warning("点赞按钮不可见")
                return None
                
        except Exception as e:
            logger.error(f"查找点赞按钮失败: {e}")
            return None

    async def find_retweet_button(self, tweet_container: Optional[Locator] = None) -> Optional[Locator]:
        """查找转推按钮 - 使用验证有效的方法"""
        base = tweet_container or self.page
        
        try:
            # 验证有效的选择器: [data-testid="retweet"]
            retweet_button = base.locator('[data-testid="retweet"]').first
            
            if await retweet_button.is_visible():
                logger.debug("通过data-testid找到转推按钮")
                return retweet_button
            else:
                logger.warning("转推按钮不可见")
                return None
                
        except Exception as e:
            logger.error(f"查找转推按钮失败: {e}")
            return None

    async def safe_click_element(self, element: Locator, element_name: str = "元素") -> bool:
        """安全点击元素 - 基于验证的最佳实践"""
        if not element:
            logger.warning(f"{element_name}为空，无法点击")
            return False
        
        try:
            # 1. 滚动到可见位置
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # 2. 确认元素可见和可用
            if not await element.is_visible():
                logger.warning(f"{element_name}不可见")
                return False
            
            if not await element.is_enabled():
                logger.warning(f"{element_name}不可用")
                return False
            
            # 3. 执行点击
            await element.click()
            logger.info(f"{element_name}点击成功")
            return True
            
        except Exception as e:
            logger.error(f"{element_name}点击失败: {e}")
            return False

    async def perform_like_action(self, tweet_index: int = 0) -> bool:
        """执行点赞操作 - 完整流程"""
        try:
            # 1. 等待推文加载
            if not await self.wait_for_tweets_loaded():
                logger.error("推文加载失败")
                return False
            
            # 2. 获取推文容器
            tweets = await self.find_tweet_containers()
            if not tweets or len(tweets) <= tweet_index:
                logger.error(f"未找到第{tweet_index + 1}个推文")
                return False
            
            # 3. 查找点赞按钮
            tweet = tweets[tweet_index]
            like_button = await self.find_like_button(tweet)
            if not like_button:
                logger.error("未找到点赞按钮")
                return False
            
            # 4. 获取点赞前状态
            before_aria = await like_button.get_attribute("aria-label") or ""
            logger.info(f"点赞前状态: {before_aria}")
            
            # 5. 执行点赞
            success = await self.safe_click_element(like_button, "点赞按钮")
            if success:
                # 等待状态更新
                await asyncio.sleep(1.5)
                after_aria = await like_button.get_attribute("aria-label") or ""
                logger.info(f"点赞后状态: {after_aria}")
            
            return success
            
        except Exception as e:
            logger.error(f"点赞操作失败: {e}")
            return False

    async def perform_comment_action(self, tweet_index: int = 0, comment_text: str = "m") -> bool:
        """执行评论操作 - 基于验证的完整流程"""
        try:
            # 1. 等待推文加载
            if not await self.wait_for_tweets_loaded():
                logger.error("推文加载失败")
                return False
            
            # 2. 获取推文容器
            tweets = await self.find_tweet_containers()
            if not tweets or len(tweets) <= tweet_index:
                logger.error(f"未找到第{tweet_index + 1}个推文")
                return False
            
            # 3. 查找并点击回复按钮
            tweet = tweets[tweet_index]
            reply_button = await self.find_reply_button(tweet)
            if not reply_button:
                logger.error("未找到回复按钮")
                return False
            
            logger.info("点击回复按钮...")
            if not await self.safe_click_element(reply_button, "回复按钮"):
                return False
            
            # 4. 等待模态框出现
            await asyncio.sleep(2)
            
            # 5. 检查模态框 - 验证有效的方法
            dialogs = await self.page.locator('[role="dialog"]').all()
            if not dialogs:
                logger.error("回复模态框未出现")
                return False
            
            logger.info(f"发现 {len(dialogs)} 个模态框")
            dialog = dialogs[-1]  # 最新的模态框
            
            # 6. 查找输入框 - 验证有效的选择器
            input_selectors = [
                '[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    elements = await dialog.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            input_element = elem
                            logger.info(f"找到输入框: {selector}")
                            break
                    if input_element:
                        break
                except:
                    continue
            
            if not input_element:
                logger.error("未找到输入框")
                return False
            
            # 7. 输入评论内容
            logger.info(f"输入评论内容: '{comment_text}'")
            await input_element.click()
            await asyncio.sleep(0.5)
            await input_element.fill(comment_text)
            await asyncio.sleep(1)
            
            # 8. 查找发布按钮 - 验证有效的选择器
            post_selectors = [
                'button[data-testid="tweetButton"]',
                'button[data-testid="tweetButtonInline"]',
                'button:has-text("Post")',
                'button:has-text("Reply")'
            ]
            
            post_button = None
            for selector in post_selectors:
                try:
                    elements = await dialog.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible() and await elem.is_enabled():
                            post_button = elem
                            logger.info(f"找到发布按钮: {selector}")
                            break
                    if post_button:
                        break
                except:
                    continue
            
            if not post_button:
                logger.error("未找到发布按钮")
                return False
            
            # 9. 发布评论
            logger.info("发布评论...")
            await post_button.click()
            await asyncio.sleep(3)
            
            logger.info("评论发布完成")
            return True
            
        except Exception as e:
            logger.error(f"评论操作失败: {e}")
            return False

    async def find_tweet_input_area(self) -> Optional[Locator]:
        """查找推文输入区域 - 验证有效的方法"""
        selectors = [
            '[data-testid="tweetTextarea_0"]',  # 验证最有效
            'div[contenteditable="true"]',
            'div[role="textbox"]'
        ]
        
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible():
                    logger.debug(f"找到输入区域: {selector}")
                    return element
            except:
                continue
        
        logger.warning("未找到推文输入区域")
        return None

    async def find_post_button(self) -> Optional[Locator]:
        """查找发布按钮 - 验证有效的方法"""
        selectors = [
            'button[data-testid="tweetButtonInline"]',
            'button[data-testid="tweetButton"]',
            'button:has-text("Post")',
            'button:has-text("Tweet")'
        ]
        
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible() and await element.is_enabled():
                    logger.debug(f"找到发布按钮: {selector}")
                    return element
            except:
                continue
        
        logger.warning("未找到发布按钮")
        return None 