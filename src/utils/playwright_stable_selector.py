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
        """安全点击元素 - 使用真实用户行为绕过遮挡层"""
        if not element:
            logger.warning(f"{element_name}为空，无法点击")
            return False
        
        try:
            # 1. 滚动到元素可见位置
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            
            # 2. 确认元素可见和可用
            if not await element.is_visible():
                logger.warning(f"{element_name}不可见")
                return False
            
            if not await element.is_enabled():
                logger.warning(f"{element_name}不可用")
                return False
            
            # 3. 模拟真实用户行为 - hover触发状态变化
            try:
                await element.hover()
                await asyncio.sleep(0.2)  # 等待hover效果
                logger.debug(f"已hover到{element_name}")
            except Exception as e:
                logger.debug(f"hover失败: {e}")
            
            # 4. 多种点击策略 - 从温和到强制
            click_strategies = [
                ("普通点击", lambda: element.click()),
                ("左上角点击", self._click_position_offset(element, 0.1, 0.1)),
                ("右上角点击", self._click_position_offset(element, 0.9, 0.1)),
                ("左下角点击", self._click_position_offset(element, 0.1, 0.9)),
                ("右下角点击", self._click_position_offset(element, 0.9, 0.9)),
                ("强制点击", lambda: element.click(force=True)),
                ("JavaScript点击", lambda: element.evaluate("el => el.click()"))
            ]
            
            for strategy_name, click_func in click_strategies:
                try:
                    await click_func()
                    logger.info(f"{element_name}{strategy_name}成功")
                    return True
                except Exception as e:
                    logger.debug(f"{element_name}{strategy_name}失败: {e}")
                    # 短暂等待后尝试下一种策略
                    await asyncio.sleep(0.1)
                    continue
            
            logger.error(f"{element_name}所有点击策略都失败了")
            return False
            
        except Exception as e:
            logger.error(f"{element_name}点击过程异常: {e}")
            return False
    
    def _click_position_offset(self, element: Locator, x_ratio: float, y_ratio: float):
        """返回指定位置点击的函数"""
        async def click_at_position():
            try:
                # 获取元素边界框 - 增加重试机制
                box = None
                for attempt in range(3):
                    try:
                        box = await element.bounding_box(timeout=2000)
                        if box:
                            break
                    except:
                        await asyncio.sleep(0.2)
                        continue
                
                if not box:
                    raise Exception("无法获取元素边界框")
                
                # 计算点击位置 (x_ratio=0.1表示左边10%, y_ratio=0.1表示上边10%)
                x = box['x'] + box['width'] * x_ratio
                y = box['y'] + box['height'] * y_ratio
                
                # 确保坐标有效
                if x <= 0 or y <= 0:
                    raise Exception(f"无效的点击坐标: ({x}, {y})")
                
                # 在指定位置点击
                await self.page.mouse.click(x, y)
                
            except Exception as e:
                logger.debug(f"位置点击失败: {e}")
                raise
            
        return click_at_position

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
        """执行评论操作 - 基于验证的完整流程，包含模态框管理"""
        try:
            # 1. 预防检测：确保页面干净
            await self.ensure_clean_page_state()
            
            # 2. 等待推文加载
            if not await self.wait_for_tweets_loaded():
                logger.error("推文加载失败")
                return False
            
            # 3. 获取推文容器
            tweets = await self.find_tweet_containers()
            if not tweets or len(tweets) <= tweet_index:
                logger.error(f"未找到第{tweet_index + 1}个推文")
                return False
            
            # 4. 查找并点击回复按钮
            tweet = tweets[tweet_index]
            reply_button = await self.find_reply_button(tweet)
            if not reply_button:
                logger.error("未找到回复按钮")
                return False
            
            logger.info("点击回复按钮...")
            if not await self.safe_click_element(reply_button, "回复按钮"):
                return False
            
            # 5. 等待模态框出现
            await asyncio.sleep(2)
            
            # 6. 检查模态框 - 验证有效的方法
            dialogs = await self.page.locator('[role="dialog"]').all()
            if not dialogs:
                logger.error("回复模态框未出现")
                return False
            
            logger.info(f"发现 {len(dialogs)} 个模态框")
            dialog = dialogs[-1]  # 最新的模态框
            
            # 7. 查找输入框 - 验证有效的选择器
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
            
            # 8. 输入评论内容
            logger.info(f"输入评论内容: '{comment_text}'")
            await input_element.click()
            await asyncio.sleep(0.5)
            await input_element.fill(comment_text)
            await asyncio.sleep(1)
            
            # 9. 查找发布按钮 - 验证有效的选择器
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
            
            # 10. 发布评论
            logger.info("发布评论...")
            await post_button.click()
            await asyncio.sleep(3)
            
            # 11. 主动清理：确保评论模态框已关闭
            success = await self.ensure_comment_modal_closed()
            if success:
                logger.info("✅ 评论发布完成，模态框已确认关闭")
            else:
                logger.warning("⚠️ 评论发布完成，但模态框关闭状态不确定")
            
            return True
            
        except Exception as e:
            logger.error(f"评论操作失败: {e}")
            # 异常恢复：清理可能存在的模态框
            await self.force_close_modals()
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

    async def ensure_clean_page_state(self) -> bool:
        """预防检测：确保页面状态干净，没有残留的模态框"""
        try:
            logger.debug("🔍 检测页面状态...")
            
            # 检查是否存在模态框
            dialogs = await self.page.locator('[role="dialog"]').all()
            
            if not dialogs:
                logger.debug("✅ 页面状态干净，无模态框")
                return True
            
            logger.info(f"🧹 发现 {len(dialogs)} 个残留模态框，开始清理...")
            
            # 尝试关闭所有模态框
            success = await self._close_all_modals(dialogs)
            
            if success:
                logger.info("✅ 页面状态已清理干净")
                return True
            else:
                logger.warning("⚠️ 部分模态框可能仍然存在")
                return False
                
        except Exception as e:
            logger.debug(f"页面状态检测失败: {e}")
            return True  # 假设页面是干净的，继续执行

    async def ensure_comment_modal_closed(self) -> bool:
        """主动清理：确保评论模态框已关闭"""
        try:
            logger.debug("🔍 验证评论模态框是否已关闭...")
            
            # 等待一下让模态框有时间消失
            await asyncio.sleep(1)
            
            # 多次检测确保模态框真正关闭
            for attempt in range(5):
                dialogs = await self.page.locator('[role="dialog"]').all()
                
                if not dialogs:
                    logger.debug("✅ 确认无模态框存在")
                    return True
                
                # 检查是否是评论相关的模态框
                comment_modal_exists = False
                for dialog in dialogs:
                    try:
                        # 检查是否包含评论输入框
                        text_areas = await dialog.locator('[data-testid="tweetTextarea_0"], div[contenteditable="true"]').all()
                        if text_areas:
                            comment_modal_exists = True
                            logger.debug(f"发现评论模态框，第{attempt+1}次尝试关闭...")
                            break
                    except:
                        continue
                
                if not comment_modal_exists:
                    logger.debug("✅ 无评论模态框，可能是其他类型的模态框")
                    return True
                
                # 尝试关闭评论模态框
                if attempt < 4:  # 前4次尝试温和关闭
                    await self._close_all_modals(dialogs)
                    await asyncio.sleep(0.5)
                else:  # 最后一次强制关闭
                    await self.force_close_modals()
                    break
            
            # 最终确认
            final_dialogs = await self.page.locator('[role="dialog"]').all()
            if not final_dialogs:
                logger.info("✅ 评论模态框已成功关闭")
                return True
            else:
                logger.warning(f"⚠️ 仍有 {len(final_dialogs)} 个模态框存在")
                return False
                
        except Exception as e:
            logger.debug(f"评论模态框关闭检测失败: {e}")
            return False

    async def force_close_modals(self) -> bool:
        """异常恢复：强制关闭所有模态框"""
        try:
            logger.info("🚨 强制关闭模态框...")
            
            # 策略1: 按ESC键多次
            for _ in range(3):
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.3)
            
            await asyncio.sleep(0.5)
            
            # 检查是否还有模态框
            dialogs = await self.page.locator('[role="dialog"]').all()
            if not dialogs:
                logger.info("✅ ESC键成功关闭所有模态框")
                return True
            
            # 策略2: 点击关闭按钮
            logger.debug("尝试点击关闭按钮...")
            await self._close_all_modals(dialogs)
            await asyncio.sleep(0.5)
            
            # 策略3: 点击模态框外部区域
            logger.debug("尝试点击模态框外部...")
            await self.page.mouse.click(100, 100)  # 点击左上角
            await asyncio.sleep(0.5)
            
            # 策略4: 刷新页面（最后手段）
            final_dialogs = await self.page.locator('[role="dialog"]').all()
            if final_dialogs:
                logger.warning("🔄 所有方法失败，可能需要页面刷新")
                return False
            
            logger.info("✅ 强制关闭成功")
            return True
            
        except Exception as e:
            logger.error(f"强制关闭模态框失败: {e}")
            return False

    async def _close_all_modals(self, dialogs) -> bool:
        """关闭所有给定的模态框"""
        success_count = 0
        
        for i, dialog in enumerate(dialogs):
            try:
                # 寻找各种关闭按钮
                close_selectors = [
                    # X关闭按钮
                    '[aria-label*="Close"]',
                    '[aria-label*="关闭"]',
                    'button[aria-label*="Close"]',
                    'button[aria-label*="关闭"]',
                    
                    # X图标路径
                    'svg[viewBox="0 0 24 24"]:has(path[d*="18.36"])',
                    'svg[viewBox="0 0 24 24"]:has(path[d*="6.4 6.4"])',
                    
                    # 通用关闭按钮
                    'button:has(svg):first-child',  # 通常第一个按钮是关闭
                    '[role="button"]:has(svg):first-child'
                ]
                
                closed = False
                for selector in close_selectors:
                    try:
                        close_buttons = await dialog.locator(selector).all()
                        for btn in close_buttons:
                            if await btn.is_visible():
                                await btn.click()
                                await asyncio.sleep(0.3)
                                logger.debug(f"点击关闭按钮: {selector}")
                                closed = True
                                break
                        if closed:
                            break
                    except:
                        continue
                
                if closed:
                    success_count += 1
                else:
                    logger.debug(f"模态框{i+1}未找到关闭按钮")
                    
            except Exception as e:
                logger.debug(f"关闭模态框{i+1}失败: {e}")
                continue
        
        logger.debug(f"成功关闭 {success_count}/{len(dialogs)} 个模态框")
        return success_count > 0 