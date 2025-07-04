"""
行为执行器 - 实现具体的Twitter操作
"""
import random
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import Page

from ...utils.session_logger import get_session_logger
from ...utils.session_data import ActionResult
from src.config.task_config import ActionType, ActionConfig, ActionConditions
from src.services.ai_service import AIConfig, ai_service_manager

class ActionExecutor:
    """行为执行器"""
    
    def __init__(self, page: Page, session_id: str, ai_config: Optional[AIConfig] = None, browser_manager=None):
        self.page = page
        self.session_id = session_id
        self.logger = get_session_logger(session_id)
        self.ai_config = ai_config
        self.browser_manager = browser_manager
        
        # 初始化AI服务
        if self.ai_config:
            ai_service_manager.initialize(self.ai_config)
            self.logger.info("AI评论服务已初始化")
        
        # 评论模板缓存
        self._comment_templates = []
    
    async def execute_action(self, action_config: ActionConfig, target_element: Any, 
                           target_info: Dict[str, Any]) -> ActionResult:
        """执行单个行为"""
        action_type = action_config.action_type
        
        try:
            # 检查执行条件
            if not self._check_action_conditions(action_config, target_info):
                self.logger.debug(f"条件不满足，跳过 {action_type.value} 行为")
                return ActionResult.SKIPPED
            
            if action_type == ActionType.LIKE:
                return await self._execute_like(target_element, target_info)
            elif action_type == ActionType.FOLLOW:
                return await self._execute_follow(target_element, target_info)
            elif action_type == ActionType.COMMENT:
                return await self._execute_comment(target_element, target_info, action_config)
            elif action_type == ActionType.RETWEET:
                return await self._execute_retweet(target_element, target_info)
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                return ActionResult.SKIPPED
                
        except Exception as e:
            self.logger.error(f"Error executing {action_type.value}: {e}")
            return ActionResult.ERROR
    
    def _check_action_conditions(self, action_config: ActionConfig, target_info: Dict[str, Any]) -> bool:
        """检查行为执行条件"""
        # 如果没有配置条件或条件为空，默认允许执行
        if not action_config.conditions:
            self.logger.debug(f"无条件限制，允许执行 {action_config.action_type.value}")
            return True
        
        try:
            # 创建ActionConditions实例并检查
            conditions = ActionConditions.from_dict(action_config.conditions)
            result = conditions.check_conditions(target_info)
            
            if result:
                # 记录满足条件的详细信息
                self._log_condition_success(action_config, target_info, conditions)
            else:
                # 记录不满足的具体原因
                self._log_condition_failure(action_config, target_info, conditions)
            
            return result
            
        except Exception as e:
            self.logger.error(f"检查条件时出错: {e}")
            # 出错时默认不执行，保守策略
            return False
    
    def _log_condition_success(self, action_config: ActionConfig, target_info: Dict[str, Any], 
                              conditions: ActionConditions):
        """记录条件检查成功的详细信息"""
        action_type = action_config.action_type.value
        username = target_info.get('username', 'Unknown')
        
        # 获取实际数据
        like_count = conditions._parse_count(target_info.get('like_count', '0'))
        retweet_count = conditions._parse_count(target_info.get('retweet_count', '0'))
        reply_count = conditions._parse_count(target_info.get('reply_count', '0'))
        view_count = conditions._parse_count(target_info.get('view_count', '0'))
        content_length = len(target_info.get('content', ''))
        is_verified = target_info.get('is_verified', False)
        
        self.logger.info(
            f"条件检查成功 [{action_type}] @{username} - "
            f"赞:{like_count} 转:{retweet_count} 回:{reply_count} 看:{view_count} "
            f"长度:{content_length} 验证:{is_verified}"
        )
    
    def _log_condition_failure(self, action_config: ActionConfig, target_info: Dict[str, Any], 
                              conditions: ActionConditions):
        """记录条件检查失败的详细信息"""
        action_type = action_config.action_type.value
        username = target_info.get('username', 'Unknown')
        
        # 获取实际数据
        like_count = conditions._parse_count(target_info.get('like_count', '0'))
        retweet_count = conditions._parse_count(target_info.get('retweet_count', '0'))
        reply_count = conditions._parse_count(target_info.get('reply_count', '0'))
        view_count = conditions._parse_count(target_info.get('view_count', '0'))
        content_length = len(target_info.get('content', ''))
        is_verified = target_info.get('is_verified', False)
        
        # 分析具体哪些条件不满足
        failure_reasons = []
        
        # 检查点赞数条件
        if conditions.min_like_count is not None and like_count < conditions.min_like_count:
            failure_reasons.append(f"点赞数过低({like_count}<{conditions.min_like_count})")
        if conditions.max_like_count is not None and like_count > conditions.max_like_count:
            failure_reasons.append(f"点赞数过高({like_count}>{conditions.max_like_count})")
        
        # 检查转发数条件
        if conditions.min_retweet_count is not None and retweet_count < conditions.min_retweet_count:
            failure_reasons.append(f"转发数过低({retweet_count}<{conditions.min_retweet_count})")
        if conditions.max_retweet_count is not None and retweet_count > conditions.max_retweet_count:
            failure_reasons.append(f"转发数过高({retweet_count}>{conditions.max_retweet_count})")
        
        # 检查回复数条件
        if conditions.min_reply_count is not None and reply_count < conditions.min_reply_count:
            failure_reasons.append(f"回复数过低({reply_count}<{conditions.min_reply_count})")
        if conditions.max_reply_count is not None and reply_count > conditions.max_reply_count:
            failure_reasons.append(f"回复数过高({reply_count}>{conditions.max_reply_count})")
        
        # 检查浏览量条件
        if conditions.min_view_count is not None and view_count < conditions.min_view_count:
            failure_reasons.append(f"浏览量过低({view_count}<{conditions.min_view_count})")
        if conditions.max_view_count is not None and view_count > conditions.max_view_count:
            failure_reasons.append(f"浏览量过高({view_count}>{conditions.max_view_count})")
        
        # 检查内容长度条件
        if conditions.min_content_length is not None and content_length < conditions.min_content_length:
            failure_reasons.append(f"内容过短({content_length}<{conditions.min_content_length})")
        if conditions.max_content_length is not None and content_length > conditions.max_content_length:
            failure_reasons.append(f"内容过长({content_length}>{conditions.max_content_length})")
        
        # 检查验证状态条件
        if conditions.verified_only is True and not is_verified:
            failure_reasons.append("需要验证用户")
        if conditions.exclude_verified is True and is_verified:
            failure_reasons.append("排除验证用户")
        
        # 检查媒体条件
        has_any_media = any([
            target_info.get('has_images', False),
            target_info.get('has_video', False), 
            target_info.get('has_gif', False)
        ])
        if conditions.has_media is True and not has_any_media:
            failure_reasons.append("需要包含媒体")
        if conditions.has_media is False and has_any_media:
            failure_reasons.append("不能包含媒体")
        
        reason_str = "; ".join(failure_reasons) if failure_reasons else "未知原因"
        
        self.logger.debug(
            f"条件检查失败 [{action_type}] @{username} - "
            f"赞:{like_count} 转:{retweet_count} 回:{reply_count} 看:{view_count} "
            f"长度:{content_length} 验证:{is_verified} - 原因: {reason_str}"
        )
    
    async def _execute_like(self, tweet_element: Any, tweet_info: Dict[str, Any]) -> ActionResult:
        """执行点赞操作"""
        try:
            # 检查页面是否仍然可用
            if not await self._check_page_available():
                self.logger.error("页面不可用，跳过点赞操作")
                return ActionResult.ERROR
            
            # 主动清理遮罩层（使用温和的清理）
            await self._gentle_clear_blockers()
            await asyncio.sleep(0.3)  # 减少等待时间
            
            username = tweet_info.get('username', 'unknown')
            self.logger.debug(f"准备点赞推文: {username}")
            
            # 查找点赞按钮 - 增强选择器
            like_selectors = [
                # 标准选择器
                '[data-testid="like"]',
                'div[data-testid="like"]', 
                'button[data-testid="like"]',
                
                # aria-label选择器
                '[aria-label*="Like"]',
                '[aria-label*="点赞"]',
                '[aria-label*="like"]',
                '[aria-label*="heart"]',
                
                # 通过图标查找
                'svg[viewBox="0 0 24 24"] path[d*="20.884"]',  # 心形图标路径
                'svg[data-testid="heart"]',
                'svg[aria-label*="Like"]',
                
                # 通过容器结构查找
                'div[role="group"] > div:nth-child(4)',  # 通常点赞是第4个按钮
                'div[role="group"] > div:has(svg)',
                'div[role="group"] div:has([aria-label*="like"])',
                
                # 通过CSS类查找（Twitter经常用的类名模式）
                'div[class*="r-1777fci"]',  # Twitter常用的交互按钮类
                'div[class*="r-18u37iz"]',
                'div[class*="r-1awozwy"]',
                
                # 通过相对位置查找
                'article div[role="group"] > div:nth-of-type(4)',
                'article div[role="group"] > div:nth-of-type(3)',
                
                # 通用心形图标选择器
                'svg:has(path[d*="heart"])',
                'button:has(svg[viewBox="0 0 24 24"])',
                
                # 通过文本内容查找（有些情况下会显示数字）
                'div[role="button"]:has-text("♥")',
                'div[role="button"]:has([aria-label*="like"])',
                
                # 备用通用选择器
                'div[tabindex="0"][role="button"]:has(svg)',
                '[role="button"]:has(svg)',
                'div[data-testid*="like"]',
                
                # XPath风格的查找（通过相邻元素定位）
                'div:has(+ div[aria-label*="repost"], + div[aria-label*="share"])',
                
                # 最后的兜底选择器
                'button',
                'div[role="button"]'
            ]
            
            like_button = None
            for selector in like_selectors:
                try:
                    if selector in ['button', 'div[role="button"]']:
                        # 对于通用选择器，需要额外验证
                        buttons = tweet_element.locator(selector)
                        count = await buttons.count()
                        for i in range(count):
                            button = buttons.nth(i)
                            try:
                                # 检查aria-label
                                aria_label = await button.get_attribute("aria-label", timeout=1000)
                                if aria_label and any(word in aria_label.lower() for word in ['like', '点赞', 'heart']):
                                    self.logger.debug(f"通过aria-label找到点赞按钮: {aria_label}")
                                    like_button = button
                                    break
                                    
                                # 检查是否包含心形图标
                                svg_element = button.locator('svg')
                                if await svg_element.count() > 0:
                                    svg_aria = await svg_element.get_attribute("aria-label", timeout=500)
                                    if svg_aria and 'like' in svg_aria.lower():
                                        self.logger.debug(f"通过SVG aria-label找到点赞按钮: {svg_aria}")
                                        like_button = button
                                        break
                                    
                                    # 检查SVG路径是否包含心形特征
                                    path_elements = svg_element.locator('path')
                                    path_count = await path_elements.count()
                                    for j in range(path_count):
                                        path_d = await path_elements.nth(j).get_attribute('d', timeout=500)
                                        if path_d and any(pattern in path_d for pattern in ['20.884', '12 21.35', 'heart']):
                                            self.logger.debug(f"通过SVG路径找到点赞按钮: {path_d[:50]}")
                                            like_button = button
                                            break
                                    if like_button:
                                        break
                            except:
                                continue
                        if like_button:
                            break
                    else:
                        # 标准选择器直接尝试
                        button = tweet_element.locator(selector).first
                        if await button.count() > 0:
                            # 额外验证元素有效性
                            try:
                                is_visible = await button.is_visible()
                                if is_visible:
                                    self.logger.debug(f"找到点赞按钮，使用选择器: {selector}")
                                    like_button = button
                                    break
                            except:
                                pass
                except Exception as e:
                    self.logger.debug(f"点赞选择器失败 {selector}: {e}")
                    continue
            
            # 最后的智能查找尝试
            if not like_button:
                self.logger.debug("尝试使用智能查找方法查找点赞按钮...")
                like_button = await self._smart_find_element(tweet_element, "button", ["like", "点赞", "heart"])
            
            if not like_button:
                self.logger.warning(f"未找到点赞按钮 (@{username})")
                return ActionResult.FAILED
            
            # 检查是否已经点赞
            try:
                aria_label = await like_button.get_attribute("aria-label", timeout=2000)
                if aria_label and ("liked" in aria_label.lower() or "已点赞" in aria_label):
                    self.logger.info(f"已点赞过，跳过 (@{username})")
                    return ActionResult.SKIPPED
            except Exception as e:
                self.logger.debug(f"检查点赞状态失败: {e}")
            
            # 多重策略点击
            try:
                # 温和清理页面阻挡元素
                await self._gentle_clear_blockers()
                
                # 策略1: 使用safe_click
                if hasattr(self, 'browser_manager') and self.browser_manager:
                    for selector in like_selectors:
                        try:
                            if await tweet_element.locator(selector).count() > 0:
                                success = await self.browser_manager.safe_click(selector)
                                if success:
                                    self.logger.info(f"✅ 点赞成功 (@{tweet_info.get('username', 'Unknown')})")
                                    return ActionResult.SUCCESS
                        except Exception as e:
                            self.logger.debug(f"安全点击失败 {selector}: {e}")
                            continue
                
                # 策略2: 强制点击
                try:
                    await like_button.click(force=True, timeout=3000)
                    self.logger.info(f"✅ 点赞成功 (强制点击) (@{tweet_info.get('username', 'Unknown')})")
                    await self.random_delay(0.5, 2.0)
                    return ActionResult.SUCCESS
                except Exception as e:
                    self.logger.debug(f"强制点击失败: {e}")
                
                # 策略3: JavaScript点击
                try:
                    await like_button.evaluate("element => element.click()")
                    self.logger.info(f"✅ 点赞成功 (JS点击) (@{tweet_info.get('username', 'Unknown')})")
                    await self.random_delay(0.5, 2.0)
                    return ActionResult.SUCCESS
                except Exception as e:
                    self.logger.debug(f"JS点击失败: {e}")
                
                # 策略4: 普通点击（最后尝试）
                await like_button.click(timeout=5000)
                self.logger.info(f"✅ 点赞成功 (@{tweet_info.get('username', 'Unknown')})")
                
                # 随机延迟
                await self.random_delay(0.5, 2.0)
                
                return ActionResult.SUCCESS
                
            except Exception as e:
                self.logger.error(f"点击点赞按钮失败: {e}")
                return ActionResult.ERROR
            
        except Exception as e:
            self.logger.error(f"点赞操作失败: {e}")
            return ActionResult.ERROR
    
    async def _execute_follow(self, user_element: Any, user_info: Dict[str, Any]) -> ActionResult:
        """执行关注操作"""
        try:
            # 检查页面是否仍然可用
            if not await self._check_page_available():
                self.logger.error("页面不可用，跳过关注操作")
                return ActionResult.ERROR
            
            username = user_info.get('username', 'unknown')
            self.logger.debug(f"准备关注用户: {username}")
            
            # 直接导航到用户资料页面进行关注（推文页面通常没有关注按钮）
            try:
                profile_url = f"https://x.com/{username}"
                self.logger.debug(f"导航到用户资料页面: {profile_url}")
                
                # 保存当前页面URL以便稍后返回
                original_url = self.page.url
                
                await self.page.goto(profile_url, timeout=15000)
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                await asyncio.sleep(random.uniform(2.0, 3.0))
                
                # 在资料页面查找关注按钮
                follow_button = await self._find_follow_button_on_profile_page()
                
                if not follow_button:
                    self.logger.warning(f"未找到用户 {username} 的关注按钮")
                    # 返回原页面
                    try:
                        await self.page.goto(original_url, timeout=10000)
                        await asyncio.sleep(1)
                    except:
                        pass
                    return ActionResult.FAILED
                
                # 检查按钮状态
                try:
                    button_text = await follow_button.text_content(timeout=3000)
                    if button_text:
                        button_text_lower = button_text.lower()
                        # 如果已经关注，跳过
                        if any(word in button_text_lower for word in ['following', 'unfollow', '已关注', '取消关注']):
                            self.logger.info(f"已关注用户: {username}")
                            # 返回原页面
                            try:
                                await self.page.goto(original_url, timeout=10000)
                                await asyncio.sleep(1)
                            except:
                                pass
                            return ActionResult.SKIPPED
                        
                        self.logger.debug(f"关注按钮文本: {button_text}")
                except Exception as e:
                    self.logger.debug(f"检查关注状态失败: {e}")
                
                # 执行关注
                try:
                    await follow_button.click(timeout=5000)
                    self.logger.debug(f"关注按钮点击成功: {username}")
                except Exception as e:
                    self.logger.error(f"点击关注按钮失败: {e}")
                    # 返回原页面
                    try:
                        await self.page.goto(original_url, timeout=10000)
                        await asyncio.sleep(1)
                    except:
                        pass
                    return ActionResult.FAILED
                
                # 等待反馈确认
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                # 验证关注是否成功
                try:
                    # 重新查找按钮以获取最新状态
                    updated_button = await self._find_follow_button_on_profile_page()
                    if updated_button:
                        updated_text = await updated_button.text_content(timeout=2000)
                        if updated_text and any(word in updated_text.lower() for word in ['following', 'unfollow', '已关注']):
                            self.logger.info(f"✅ 关注成功: {username}")
                            # 返回原页面
                            try:
                                await self.page.goto(original_url, timeout=10000)
                                await asyncio.sleep(1)
                            except:
                                pass
                            return ActionResult.SUCCESS
                    
                    # 即使验证失败，也认为可能成功了
                    self.logger.info(f"关注操作完成: {username}")
                    # 返回原页面
                    try:
                        await self.page.goto(original_url, timeout=10000)
                        await asyncio.sleep(1)
                    except:
                        pass
                    return ActionResult.SUCCESS
                    
                except Exception as e:
                    self.logger.debug(f"验证关注状态失败: {e}")
                    self.logger.info(f"关注操作完成: {username}")
                    # 返回原页面
                    try:
                        await self.page.goto(original_url, timeout=10000)
                        await asyncio.sleep(1)
                    except:
                        pass
                    return ActionResult.SUCCESS
                
            except Exception as e:
                self.logger.error(f"导航到用户资料页面失败: {e}")
                return ActionResult.FAILED
            
        except Exception as e:
            self.logger.error(f"关注操作失败: {e}")
            return ActionResult.ERROR
    
    async def _find_follow_button_on_current_page(self, user_element: Any, username: str) -> Any:
        """在当前页面查找关注按钮"""
        try:
            # 在用户元素附近查找关注按钮
            follow_selectors = [
                # 在用户元素内查找
                'div[data-testid*="follow"]:not([data-testid*="unfollow"])',
                '[data-testid*="follow"]:not([data-testid*="unfollow"])',
                'button[data-testid*="follow"]:not([data-testid*="unfollow"])',
                'div[role="button"]:has-text("Follow")',
                'div[role="button"]:has-text("关注")',
                'button:has-text("Follow")',
                'button:has-text("关注")',
                
                # 在用户元素的父级容器中查找
                'xpath=ancestor::article//div[data-testid*="follow"]',
                'xpath=ancestor::div[contains(@class,"user")]//button[contains(text(),"Follow")]'
            ]
            
            for selector in follow_selectors:
                try:
                    if selector.startswith('xpath='):
                        # 使用xpath选择器
                        button = user_element.locator(selector)
                    else:
                        # 先在用户元素内查找
                        button = user_element.locator(selector).first
                        
                        # 如果用户元素内没有，在页面范围内查找
                        if await button.count() == 0:
                            button = self.page.locator(selector).first
                    
                    if await button.count() > 0:
                        self.logger.debug(f"在当前页面找到关注按钮，使用选择器: {selector}")
                        return button
                        
                except Exception as e:
                    self.logger.debug(f"关注选择器失败 {selector}: {e}")
                    continue
                    
            return None
            
        except Exception as e:
            self.logger.debug(f"在当前页面查找关注按钮失败: {e}")
            return None
    
    async def _find_follow_button_on_profile_page(self) -> Any:
        """在用户资料页面查找关注按钮"""
        try:
            # 资料页面的关注按钮选择器
            profile_follow_selectors = [
                'div[data-testid="follow"]',
                '[data-testid="follow"]',
                'button[data-testid="follow"]',
                'div[role="button"]:has-text("Follow")',
                'div[role="button"]:has-text("关注")',
                'button:has-text("Follow")',
                'button:has-text("关注")',
                'div[aria-label*="Follow"]',
                'button[aria-label*="Follow"]',
                
                # 更通用的选择器
                'div[role="button"][data-testid*="follow"]',
                'button[data-testid*="follow"]',
                'div:has-text("Follow")',
                'button:has-text("Follow")'
            ]
            
            for selector in profile_follow_selectors:
                try:
                    button = self.page.locator(selector).first
                    if await button.count() > 0:
                        # 验证这确实是关注按钮
                        try:
                            text = await button.text_content(timeout=2000)
                            if text and ('follow' in text.lower() or '关注' in text):
                                self.logger.debug(f"在资料页面找到关注按钮，使用选择器: {selector}, 文本: {text}")
                                return button
                        except Exception as e:
                            self.logger.debug(f"验证按钮文本失败: {e}")
                            continue
                            
                except Exception as e:
                    self.logger.debug(f"资料页面关注选择器失败 {selector}: {e}")
                    continue
                    
            return None
            
        except Exception as e:
            self.logger.debug(f"在资料页面查找关注按钮失败: {e}")
            return None
    
    async def _execute_comment(self, tweet_element: Any, tweet_info: Dict[str, Any], 
                             action_config: ActionConfig) -> ActionResult:
        """执行评论操作"""
        try:
            # 检查页面是否仍然可用
            if not await self._check_page_available():
                self.logger.error("页面不可用，跳过评论操作")
                return ActionResult.ERROR
            
            # 主动清理遮罩层（使用温和的清理）
            await self._gentle_clear_blockers()
            await asyncio.sleep(0.3)  # 减少等待时间
            
            username = tweet_info.get('username', 'unknown')
            self.logger.debug(f"准备评论推文: {username}")
            
            # 查找回复按钮 - 增强选择器
            reply_selectors = [
                # 标准Twitter选择器
                '[data-testid="reply"]',
                'div[data-testid="reply"]',
                'button[data-testid="reply"]',
                
                # 通过aria-label查找
                '[aria-label*="Reply"]',
                '[aria-label*="回复"]',
                '[aria-label*="reply"]',
                
                # 通过图标查找（回复图标通常是弯曲箭头）
                'svg[viewBox="0 0 24 24"] path[d*="1.751"]',  # 回复图标路径特征
                'svg[data-testid="reply"]',
                'svg[aria-label*="Reply"]',
                
                # 通过容器结构查找
                'div[role="group"] > div:nth-child(1)',  # 回复通常是第1个按钮
                'div[role="group"] > div:first-child',
                'article div[role="group"] > div:first-child',
                
                # 通过CSS类查找
                'div[class*="r-1777fci"]:first-child',  # Twitter常用的交互按钮类
                'div[class*="r-18u37iz"]:first-child',
                'div[class*="r-1awozwy"]:first-child',
                
                # 通过文本内容查找（某些情况下会显示"回复"文字）
                'div[role="button"]:has-text("Reply")',
                'div[role="button"]:has-text("回复")',
                'button:has-text("Reply")',
                'button:has-text("回复")',
                
                # 通过位置查找（回复按钮通常在推文底部的第一个位置）
                'article div[aria-label*="actions"] div:first-child',
                'div[data-testid*="tweet"] div[role="group"] > div:first-child',
                
                # 通用图标选择器
                'button:has(svg[viewBox="0 0 24 24"])',
                'div[role="button"]:has(svg)',
                
                # 备用选择器
                'div[tabindex="0"][role="button"]:has(svg)',
                '[role="button"]:has(svg)',
                
                # 最后的兜底选择器
                'button',
                'div[role="button"]'
            ]
            
            reply_button = None
            for selector in reply_selectors:
                try:
                    if selector in ['button', 'div[role="button"]']:
                        # 对于通用选择器，需要额外验证
                        buttons = tweet_element.locator(selector)
                        count = await buttons.count()
                        for i in range(count):
                            button = buttons.nth(i)
                            try:
                                # 检查aria-label
                                aria_label = await button.get_attribute("aria-label", timeout=1000)
                                if aria_label and any(word in aria_label.lower() for word in ['reply', '回复']):
                                    self.logger.debug(f"通过aria-label找到回复按钮: {aria_label}")
                                    reply_button = button
                                    break
                                    
                                # 检查是否包含回复图标
                                svg_element = button.locator('svg')
                                if await svg_element.count() > 0:
                                    svg_aria = await svg_element.get_attribute("aria-label", timeout=500)
                                    if svg_aria and 'reply' in svg_aria.lower():
                                        self.logger.debug(f"通过SVG aria-label找到回复按钮: {svg_aria}")
                                        reply_button = button
                                        break
                                    
                                    # 检查SVG路径是否包含回复特征
                                    path_elements = svg_element.locator('path')
                                    path_count = await path_elements.count()
                                    for j in range(path_count):
                                        path_d = await path_elements.nth(j).get_attribute('d', timeout=500)
                                        if path_d and any(pattern in path_d for pattern in ['1.751', '1.804', 'reply']):
                                            self.logger.debug(f"通过SVG路径找到回复按钮: {path_d[:50]}")
                                            reply_button = button
                                            break
                                    if reply_button:
                                        break
                                
                                # 检查文本内容
                                text = await button.text_content(timeout=500)
                                if text and any(word in text.lower() for word in ['reply', '回复']):
                                    self.logger.debug(f"通过文本找到回复按钮: {text}")
                                    reply_button = button
                                    break
                                    
                            except:
                                continue
                        if reply_button:
                            break
                    else:
                        # 标准选择器直接尝试
                        button = tweet_element.locator(selector).first
                        if await button.count() > 0:
                            # 额外验证元素有效性
                            try:
                                is_visible = await button.is_visible()
                                if is_visible:
                                    self.logger.debug(f"找到回复按钮，使用选择器: {selector}")
                                    reply_button = button
                                    break
                            except:
                                pass
                except Exception as e:
                    self.logger.debug(f"回复选择器失败 {selector}: {e}")
                    continue
            
            # 最后的智能查找尝试
            if not reply_button:
                self.logger.debug("尝试使用智能查找方法查找回复按钮...")
                reply_button = await self._smart_find_element(tweet_element, "button", ["reply", "回复"])
            
            if not reply_button:
                self.logger.warning(f"未找到回复按钮 (@{username})")
                return ActionResult.FAILED
            
            # 多重策略点击回复按钮
            try:
                # 温和清理阻挡元素
                await self._gentle_clear_blockers()
                
                # 策略1: 强制点击
                try:
                    await reply_button.click(force=True, timeout=3000)
                    self.logger.debug("回复按钮点击成功 (强制)")
                except Exception as e:
                    self.logger.debug(f"强制点击回复按钮失败: {e}")
                    
                    # 策略2: JavaScript点击
                    try:
                        await reply_button.evaluate("element => element.click()")
                        self.logger.debug("回复按钮点击成功 (JS)")
                    except Exception as e:
                        self.logger.debug(f"JS点击回复按钮失败: {e}")
                        
                        # 策略3: 普通点击
                        await reply_button.click(timeout=5000)
                        self.logger.debug("回复按钮点击成功")
                
            except Exception as e:
                self.logger.error(f"点击回复按钮失败: {e}")
                return ActionResult.ERROR
            
            # 等待评论框出现 - 增加等待时间
            await asyncio.sleep(random.uniform(3.0, 4.0))
            
            # 查找评论输入框 - 超强选择器
            comment_selectors = [
                # 标准Twitter选择器
                'div[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0"]',
                'div[data-testid*="tweetTextarea"]',
                '[data-testid*="tweetTextarea"]',
                
                # 通过role和属性查找
                'div[role="textbox"]',
                'div[contenteditable="true"]',
                'textarea[placeholder*="Tweet"]',
                'textarea[placeholder*="回复"]',
                
                # 通过编辑器容器查找
                '.DraftEditor-editorContainer div[contenteditable="true"]',
                '.DraftEditor-root div[contenteditable="true"]',
                '.notranslate[contenteditable="true"]',
                '.public-DraftEditor-content',
                
                # 通过aria-label查找
                'div[aria-label*="Tweet"]',
                'div[aria-label*="回复"]',
                'div[aria-label*="Reply"]',
                'div[aria-label*="compose"]',
                'div[aria-label*="编写"]',
                
                # 通过placeholder查找
                'div[placeholder*="Tweet"]',
                'div[placeholder*="回复"]',
                'div[placeholder*="Reply"]',
                'div[placeholder*="What"]',
                'div[placeholder*="写"]',
                
                # 通过CSS类查找（Twitter常用类）
                'div[class*="DraftEditor"]',
                'div[class*="r-1p0dtai"]',
                'div[class*="r-1d2f490"]',
                'div[class*="r-6koalj"]',
                'div[class*="r-16y2uox"]',
                
                # 通过data属性查找
                'div[data-slate-editor="true"]',
                'div[data-lexical-editor="true"]',
                'div[data-contents="true"]',
                
                # 通过层级结构查找
                'form div[contenteditable="true"]',
                'div[role="main"] div[contenteditable="true"]',
                'div[aria-expanded="true"] div[contenteditable="true"]',
                
                # 通过input类型查找
                'input[type="text"][placeholder*="Tweet"]',
                'textarea[aria-label*="Tweet"]',
                
                # 通用可编辑元素
                '[contenteditable="true"]',
                'textarea',
                'input[type="text"]'
            ]
            
            comment_box = None
            # 尝试等待评论框出现
            for attempt in range(5):  # 增加尝试次数
                for selector in comment_selectors:
                    try:
                        if selector in ['[contenteditable="true"]', 'textarea', 'input[type="text"]']:
                            # 对于通用选择器需要额外验证
                            elements = self.page.locator(selector)
                            element_count = await elements.count()
                            
                            for i in range(element_count):
                                element = elements.nth(i)
                                try:
                                    # 检查是否可见和可编辑
                                    is_visible = await element.is_visible()
                                    is_enabled = await element.is_enabled()
                                    if not (is_visible and is_enabled):
                                        continue
                                    
                                    # 检查aria-label或placeholder
                                    aria_label = await element.get_attribute("aria-label", timeout=500)
                                    placeholder = await element.get_attribute("placeholder", timeout=500)
                                    
                                    # 验证是否为评论框
                                    is_comment_box = False
                                    if aria_label:
                                        if any(word in aria_label.lower() for word in ['tweet', '回复', 'reply', 'compose', '编写']):
                                            is_comment_box = True
                                    if placeholder:
                                        if any(word in placeholder.lower() for word in ['tweet', '回复', 'reply', 'what', '写']):
                                            is_comment_box = True
                                    
                                    # 检查父容器是否与评论相关
                                    if not is_comment_box:
                                        parent_html = await element.evaluate("el => el.parentElement?.innerHTML || ''")
                                        if any(word in parent_html.lower() for word in ['tweet', 'reply', 'compose']):
                                            is_comment_box = True
                                    
                                    if is_comment_box:
                                        self.logger.debug(f"通过验证找到评论输入框: {selector}")
                                        comment_box = element
                                        break
                                except:
                                    continue
                            
                            if comment_box:
                                break
                        else:
                            # 标准选择器直接尝试
                            box = self.page.locator(selector).first
                            if await box.count() > 0:
                                # 验证元素是否可见和可编辑
                                try:
                                    is_visible = await box.is_visible()
                                    is_enabled = await box.is_enabled()
                                    if is_visible and is_enabled:
                                        self.logger.debug(f"找到评论输入框，使用选择器: {selector}")
                                        comment_box = box
                                        break
                                except:
                                    pass
                    except Exception as e:
                        self.logger.debug(f"评论框选择器失败 {selector}: {e}")
                        continue
                
                if comment_box:
                    break
                
                # 如果没找到，等待一会再试
                self.logger.debug(f"第{attempt+1}次未找到评论框，等待2秒后重试...")
                await asyncio.sleep(2)
                
                # 尝试重新点击回复按钮（可能对话框关闭了）
                if attempt < 4:
                    try:
                        reply_selectors = [
                            'div[data-testid="reply"]',
                            '[data-testid="reply"]',
                            'button[data-testid="reply"]'
                        ]
                        for reply_selector in reply_selectors:
                            reply_btn = tweet_element.locator(reply_selector).first
                            if await reply_btn.count() > 0:
                                await reply_btn.click(force=True, timeout=2000)
                                await asyncio.sleep(1)
                                break
                    except:
                        pass
            
            # 最后的智能查找尝试
            if not comment_box:
                self.logger.debug("尝试使用智能查找方法查找评论输入框...")
                comment_box = await self._smart_find_element(self.page, "input", ["tweet", "reply", "回复", "compose", "编写"])
            
            if not comment_box:
                self.logger.warning(f"未找到评论输入框 (@{username})")
                return ActionResult.FAILED
            
            # 生成评论内容
            comment_text = await self._generate_comment_text(tweet_info, action_config)
            if not comment_text:
                self.logger.warning(f"无法生成评论内容 (@{username})")
                return ActionResult.FAILED
            
            # 输入评论
            try:
                # 点击并聚焦输入框
                await comment_box.click()
                await asyncio.sleep(0.5)
                
                # 清空输入框
                await comment_box.fill("")
                await asyncio.sleep(0.3)
                
                # 安全输入评论
                await comment_box.type(comment_text, delay=random.randint(50, 150))
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                self.logger.debug(f"安全输入评论成功: {comment_text}")
                
            except Exception as e:
                self.logger.error(f"输入评论失败: {e}")
                return ActionResult.ERROR
            
            # 查找并点击发送按钮
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            send_selectors = [
                # 标准发送按钮选择器
                '[data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                'div[data-testid="tweetButton"]',
                'button[data-testid="tweetButton"]',
                
                # 通过文本内容查找
                'div[role="button"]:has-text("Reply")',
                'div[role="button"]:has-text("回复")',
                'button:has-text("Reply")',
                'button:has-text("回复")',
                'div[role="button"]:has-text("Tweet")',
                'button:has-text("Tweet")',
                'button:has-text("发推")',
                'button:has-text("Post")',
                'button:has-text("发送")',
                
                # 通过aria-label查找
                'button[aria-label*="Tweet"]',
                'button[aria-label*="Reply"]',
                'button[aria-label*="Post"]',
                'button[aria-label*="发送"]',
                'div[aria-label*="Tweet"]',
                'div[aria-label*="Reply"]',
                
                # 通过CSS类查找（发送按钮通常有特定样式）
                'button[class*="r-19yznuf"]',  # Twitter蓝色按钮
                'div[class*="r-19yznuf"]',
                'button[class*="r-1cwl3u0"]',
                
                # 通过type和位置查找
                'button[type="submit"]',
                'form button[type="button"]',
                'div[role="dialog"] button',
                
                # 通过相对位置查找（发送按钮通常在输入框附近）
                'div:has([contenteditable="true"]) + div button',
                'div:has([data-testid*="textarea"]) button',
                
                # 最后的通用选择器
                'button',
                'div[role="button"]'
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    if selector in ['button', 'div[role="button"]']:
                        # 对于通用选择器需要额外验证
                        buttons = self.page.locator(selector)
                        button_count = await buttons.count()
                        
                        for i in range(button_count):
                            button = buttons.nth(i)
                            try:
                                # 检查是否可见和启用
                                is_visible = await button.is_visible()
                                is_enabled = await button.is_enabled()
                                if not (is_visible and is_enabled):
                                    continue
                                
                                # 检查文本内容
                                text = await button.text_content(timeout=1000)
                                if text:
                                    text_lower = text.lower().strip()
                                    if any(word in text_lower for word in ["reply", "回复", "tweet", "发推", "post", "发送"]):
                                        self.logger.debug(f"通过文本找到发送按钮: {text}")
                                        send_button = button
                                        break
                                
                                # 检查aria-label
                                aria_label = await button.get_attribute("aria-label", timeout=500)
                                if aria_label:
                                    aria_lower = aria_label.lower()
                                    if any(word in aria_lower for word in ["tweet", "reply", "post", "发送", "回复"]):
                                        self.logger.debug(f"通过aria-label找到发送按钮: {aria_label}")
                                        send_button = button
                                        break
                                
                                # 检查按钮类型和样式（发送按钮通常是蓝色的主按钮）
                                button_type = await button.get_attribute("type", timeout=500)
                                if button_type == "submit":
                                    self.logger.debug(f"通过type=submit找到发送按钮")
                                    send_button = button
                                    break
                                    
                            except:
                                continue
                        
                        if send_button:
                            break
                    else:
                        # 标准选择器直接尝试
                        button = self.page.locator(selector).first
                        if await button.count() > 0:
                            # 验证按钮是否可用
                            try:
                                is_visible = await button.is_visible()
                                is_enabled = await button.is_enabled()
                                if is_visible and is_enabled:
                                    # 进一步验证文本内容
                                    text = await button.text_content(timeout=1000)
                                    if text and any(word in text.lower() for word in ["reply", "回复", "tweet", "发推", "post", "发送"]):
                                        self.logger.debug(f"找到发送按钮，使用选择器: {selector}, 文本: {text}")
                                        send_button = button
                                        break
                                    elif not text:  # 某些按钮可能没有文本，只有图标
                                        self.logger.debug(f"找到发送按钮（无文本），使用选择器: {selector}")
                                        send_button = button
                                        break
                            except:
                                pass
                except Exception as e:
                    self.logger.debug(f"发送按钮选择器失败 {selector}: {e}")
                    continue
            
            # 最后的智能查找尝试
            if not send_button:
                self.logger.debug("尝试使用智能查找方法查找发送按钮...")
                send_button = await self._smart_find_element(self.page, "button", ["reply", "tweet", "post", "发送", "回复", "发推"])
            
            if not send_button:
                self.logger.warning(f"未找到发送按钮 (@{username})")
                return ActionResult.FAILED
            
            # 多重策略点击发送按钮
            try:
                # 温和清理阻挡元素
                await self._gentle_clear_blockers()
                
                # 策略1: 强制点击
                try:
                    await send_button.click(force=True, timeout=3000)
                    self.logger.debug("发送按钮点击成功 (强制点击)")
                except Exception as e:
                    self.logger.debug(f"强制点击失败: {e}")
                    
                    # 策略2: JavaScript点击
                    try:
                        await send_button.evaluate("element => element.click()")
                        self.logger.debug("发送按钮点击成功 (JS点击)")
                    except Exception as e:
                        self.logger.debug(f"JS点击失败: {e}")
                        
                        # 策略3: 普通点击
                        await send_button.click(timeout=3000)
                        self.logger.debug("发送按钮点击成功 (普通点击)")
                
            except Exception as e:
                self.logger.error(f"点击发送按钮失败: {e}")
                return ActionResult.ERROR
            
            # 等待发送完成
            await asyncio.sleep(random.uniform(3.0, 5.0))
            
            # 验证发送成功
            try:
                # 检查评论框是否消失（说明评论已发送）
                if await comment_box.count() == 0:
                    self.logger.info(f"评论发送成功: {comment_text}")
                else:
                    # 检查是否还有内容，如果清空了说明发送成功
                    try:
                        content = await comment_box.text_content(timeout=2000)
                        if not content or len(content.strip()) == 0:
                            self.logger.info(f"评论发送成功: {comment_text}")
                        else:
                            self.logger.warning(f"评论可能未发送成功，输入框仍有内容: {content[:50]}")
                    except:
                        # 如果获取不到内容，可能是页面变化了，认为发送成功
                        self.logger.info(f"评论发送成功: {comment_text}")
                
            except Exception as e:
                self.logger.debug(f"验证评论发送状态失败: {e}")
                # 即使验证失败，也认为可能成功了
                self.logger.info(f"评论发送成功: {comment_text}")
            
            # 随机延迟
            await self.random_delay(1.0, 3.0)
            
            return ActionResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"评论操作失败: {e}")
            return ActionResult.ERROR
    
    async def _generate_comment_text(self, tweet_info: Dict[str, Any], action_config: ActionConfig) -> Optional[str]:
        """生成评论文本"""
        # 如果启用AI评论且AI服务可用
        if action_config.use_ai_comment and self.ai_config:
            try:
                self.logger.debug("尝试使用AI生成评论...")
                ai_comment = await ai_service_manager.generate_comment(tweet_info)
                
                if ai_comment:
                    self.logger.info(f"AI生成评论成功: {ai_comment}")
                    return ai_comment
                else:
                    self.logger.warning("AI评论生成失败")
                    
            except Exception as e:
                self.logger.error(f"AI评论生成异常: {e}")
        
        # AI失败或未启用时的备用方案
        if action_config.ai_comment_fallback or not action_config.use_ai_comment:
            if action_config.comment_templates:
                template_comment = random.choice(action_config.comment_templates)
                self.logger.info(f"使用模板评论: {template_comment}")
                return template_comment
            else:
                default_comment = self._get_default_comment()
                self.logger.info(f"使用默认评论: {default_comment}")
                return default_comment
        
        return None
    
    async def _execute_retweet(self, tweet_element: Any, tweet_info: Dict[str, Any]) -> ActionResult:
        """执行转发操作"""
        try:
            # 检查页面是否仍然可用
            if not await self._check_page_available():
                self.logger.error("页面不可用，跳过转发操作")
                return ActionResult.ERROR
            
            # 使用多种策略查找转发按钮
            retweet_button = None
            retweet_selectors = [
                'div[data-testid="retweet"]',
                '[data-testid="retweet"]',
                'button[data-testid="retweet"]',
                'div[role="button"][aria-label*="retweet"]',
                'div[role="button"][aria-label*="Retweet"]',
                'button[aria-label*="retweet"]',
                'button[aria-label*="Retweet"]'
            ]
            
            for selector in retweet_selectors:
                try:
                    button = tweet_element.locator(selector).first
                    if await button.count() > 0:
                        retweet_button = button
                        self.logger.debug(f"找到转发按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"转发选择器失败 {selector}: {e}")
                    continue
            
            if not retweet_button:
                self.logger.warning("未找到转发按钮")
                return ActionResult.FAILED
            
            # 点击转发按钮
            try:
                await retweet_button.click(timeout=5000)
                self.logger.debug("转发按钮点击成功")
            except Exception as e:
                self.logger.error(f"点击转发按钮失败: {e}")
                return ActionResult.FAILED
            
            # 等待转发选项出现
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # 使用多种策略查找确认转发按钮
            confirm_button = None
            confirm_selectors = [
                'div[data-testid="retweetConfirm"]',
                '[data-testid="retweetConfirm"]',
                'button[data-testid="retweetConfirm"]',
                'div[role="menuitem"]:has-text("Retweet")',
                'div[role="menuitem"]:has-text("转发")',
                'button:has-text("Retweet")',
                'button:has-text("转发")'
            ]
            
            for selector in confirm_selectors:
                try:
                    button = self.page.locator(selector).first
                    if await button.count() > 0:
                        confirm_button = button
                        self.logger.debug(f"找到确认转发按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"确认转发选择器失败 {selector}: {e}")
                    continue
            
            if not confirm_button:
                self.logger.warning("未找到确认转发按钮")
                return ActionResult.FAILED
            
            # 点击确认转发
            try:
                await confirm_button.click(timeout=5000)
                self.logger.debug("确认转发按钮点击成功")
            except Exception as e:
                self.logger.error(f"点击确认转发按钮失败: {e}")
                return ActionResult.FAILED
            
            # 等待转发完成
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            self.logger.info(f"转发成功: {tweet_info.get('content', '')[:50]}...")
            return ActionResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"转发操作失败: {e}")
            return ActionResult.ERROR
    
    def _get_default_comment(self) -> str:
        """获取默认评论"""
        default_comments = [
            "Great content! 👍",
            "Thanks for sharing!",
            "Interesting perspective 🤔",
            "Love this! 💯",
            "Very insightful 📚",
            "Nice post! 🔥",
            "Totally agree! ✅",
            "Well said! 👏"
        ]
        return random.choice(default_comments)
    
    async def random_delay(self, min_seconds: float, max_seconds: float):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"Random delay: {delay:.2f} seconds")
        await asyncio.sleep(delay)
    
    async def _smart_find_element(self, container, element_type: str, keywords: List[str] = None) -> Any:
        """智能查找元素的通用方法"""
        try:
            if keywords is None:
                keywords = []
            
            # 根据元素类型定义搜索策略
            if element_type == "button":
                # 查找所有可能的按钮元素
                selectors = ['button', 'div[role="button"]', 'a[role="button"]', '[tabindex="0"]']
            elif element_type == "input":
                # 查找所有可能的输入元素
                selectors = ['input', 'textarea', 'div[contenteditable="true"]', 'div[role="textbox"]']
            else:
                selectors = ['*']
            
            for selector in selectors:
                elements = container.locator(selector)
                count = await elements.count()
                
                for i in range(count):
                    element = elements.nth(i)
                    try:
                        # 检查可见性
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue
                        
                        # 检查aria-label
                        aria_label = await element.get_attribute("aria-label", timeout=500)
                        if aria_label and keywords:
                            for keyword in keywords:
                                if keyword.lower() in aria_label.lower():
                                    self.logger.debug(f"通过aria-label找到元素: {aria_label}")
                                    return element
                        
                        # 检查文本内容
                        text = await element.text_content(timeout=500)
                        if text and keywords:
                            for keyword in keywords:
                                if keyword.lower() in text.lower():
                                    self.logger.debug(f"通过文本找到元素: {text}")
                                    return element
                        
                        # 检查placeholder
                        placeholder = await element.get_attribute("placeholder", timeout=500)
                        if placeholder and keywords:
                            for keyword in keywords:
                                if keyword.lower() in placeholder.lower():
                                    self.logger.debug(f"通过placeholder找到元素: {placeholder}")
                                    return element
                        
                        # 检查data-testid
                        testid = await element.get_attribute("data-testid", timeout=500)
                        if testid and keywords:
                            for keyword in keywords:
                                if keyword.lower() in testid.lower():
                                    self.logger.debug(f"通过data-testid找到元素: {testid}")
                                    return element
                        
                        # 检查SVG图标的aria-label
                        svg_elements = element.locator('svg')
                        svg_count = await svg_elements.count()
                        for j in range(svg_count):
                            svg_aria = await svg_elements.nth(j).get_attribute("aria-label", timeout=500)
                            if svg_aria and keywords:
                                for keyword in keywords:
                                    if keyword.lower() in svg_aria.lower():
                                        self.logger.debug(f"通过SVG aria-label找到元素: {svg_aria}")
                                        return element
                        
                    except:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"智能查找元素失败: {e}")
            return None
    
    async def _check_page_available(self) -> bool:
        """检查页面是否仍然可用"""
        try:
            # 检查页面是否关闭
            if self.page.is_closed():
                self.logger.warning("页面已关闭")
                return False
            
            # 尝试获取页面标题来验证页面是否响应
            try:
                title = await self.page.title()
                self.logger.debug(f"页面可用，标题: {title}")
                return True
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"页面标题获取失败: {error_msg}")
                
                # 检查是否是执行上下文被销毁
                if "execution context was destroyed" in error_msg.lower() or "context was destroyed" in error_msg.lower():
                    self.logger.warning("检测到执行上下文被销毁，页面不可用")
                    return False
                
                # 检查是否是导航相关错误
                if "navigation" in error_msg.lower():
                    self.logger.warning("检测到导航相关错误，页面不可用")
                    return False
                
                # 其他错误也认为页面不可用
                return False
                
        except Exception as e:
            self.logger.debug(f"页面可用性检查失败: {e}")
            return False
    
    async def _check_and_dismiss_cookie_popup(self):
        """检查并清除Cookie弹窗"""
        try:
            cookie_mask = self.page.locator('[data-testid="twc-cc-mask"]')
            mask_count = await cookie_mask.count()
            
            if mask_count > 0:
                self.logger.debug(f"🍪 检测到Cookie弹窗遮罩，强制移除...")
                await self._force_remove_cookie_mask()
                await asyncio.sleep(1)  # 等待遮罩消失
                return True
            return True
        except Exception as e:
            self.logger.debug(f"检查Cookie弹窗失败: {e}")
            return True
    
    async def _force_remove_cookie_mask(self):
        """强制移除Cookie遮罩层 - 增强版"""
        try:
            await self.page.evaluate("""
                (() => {
                    console.log('🔧 强制移除Cookie遮罩层...');
                    
                    // 1. 移除Cookie同意遮罩
                    document.querySelectorAll('[data-testid="twc-cc-mask"]').forEach((mask, index) => {
                        console.log('移除Cookie遮罩', index, mask);
                        mask.remove();
                    });
                    
                    // 2. 移除所有data-testid="mask"的元素
                    document.querySelectorAll('[data-testid="mask"]').forEach((mask, index) => {
                        console.log('移除通用遮罩', index, mask);
                        mask.remove();
                    });
                    
                    // 3. 移除所有具有特定遮罩类的元素
                    const overlayClasses = [
                        'r-1p0dtai', 'r-1d2f490', 'r-1xcajam', 'r-zchlnj', 'r-ipm5af', 'r-1ffj0ar'
                    ];
                    overlayClasses.forEach(className => {
                        document.querySelectorAll('.' + className).forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.position === 'fixed' && (parseInt(style.zIndex) > 999 || el.dataset.testid === 'mask')) {
                                console.log('移除覆盖层:', className, el);
                                el.remove();
                            }
                        });
                    });
                    
                    // 4. 清理layers容器
                    const layersContainer = document.querySelector('#layers');
                    if (layersContainer) {
                        Array.from(layersContainer.children).forEach((child, index) => {
                            const style = window.getComputedStyle(child);
                            if (style.position === 'fixed' && parseInt(style.zIndex) > 999) {
                                console.log('移除layers子元素', index, child);
                                child.remove();
                            }
                        });
                    }
                    
                    // 5. 强制设置body和html的pointer-events
                    document.body.style.pointerEvents = 'auto';
                    document.documentElement.style.pointerEvents = 'auto';
                    
                    // 6. 隐藏或移除所有可能的阻挡元素
                    document.querySelectorAll('div').forEach(div => {
                        const style = window.getComputedStyle(div);
                        if (style.position === 'fixed' && 
                            (parseInt(style.zIndex) > 999 || div.dataset.testid === 'mask' || div.dataset.testid === 'twc-cc-mask')) {
                            div.style.display = 'none';
                            div.style.pointerEvents = 'none';
                        }
                    });
                    
                    console.log('✅ 强制移除遮罩完成');
                })();
            """)
            return True
        except Exception as e:
            self.logger.debug(f"强制移除遮罩失败: {e}")
            return False

    async def _gentle_clear_blockers(self):
        """温和地清理阻挡元素（避免破坏页面结构）"""
        try:
            await self.page.evaluate("""
                (() => {
                    console.log('🧹 温和清理阻挡元素...');
                    
                    // 1. 只移除明确的遮罩元素
                    document.querySelectorAll('[data-testid*="mask"]').forEach(el => {
                        if (el.dataset.testid && (el.dataset.testid.includes('mask') || el.dataset.testid === 'twc-cc-mask')) {
                            console.log('移除遮罩元素:', el);
                            el.remove();
                        }
                    });
                    
                    // 2. 只处理明显的阻挡层（高z-index且覆盖大部分屏幕）
                    document.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed' && parseInt(style.zIndex) > 9999) {
                            const rect = el.getBoundingClientRect();
                            // 只移除覆盖超过80%屏幕的大遮罩
                            if (rect.width > window.innerWidth * 0.8 && rect.height > window.innerHeight * 0.8) {
                                console.log('移除大遮罩:', el, 'z-index:', style.zIndex);
                                el.style.display = 'none';
                                el.style.pointerEvents = 'none';
                            }
                        }
                    });
                    
                    // 3. 恢复body交互
                    document.body.style.pointerEvents = 'auto';
                    
                    console.log('✅ 温和清理完成');
                })();
            """)
            return True
        except Exception as e:
            self.logger.debug(f"温和清理失败: {e}")
            return False

    async def _aggressive_clear_blockers(self):
        """激进地清理所有可能的阻挡元素（仅在必要时使用）"""
        try:
            await self.page.evaluate("""
                (() => {
                    console.log('🔧 激进清理阻挡元素...');
                    
                    // 1. 移除所有testid包含mask的元素
                    document.querySelectorAll('[data-testid*="mask"]').forEach(el => {
                        console.log('移除mask元素:', el);
                        el.remove();
                    });
                    
                    // 2. 移除所有高z-index的fixed元素
                    document.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed' && parseInt(style.zIndex) > 999) {
                            // 检查是否是阻挡元素
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 100 && rect.height > 100) {
                                console.log('移除高z-index元素:', el, 'z-index:', style.zIndex);
                                el.remove();
                            }
                        }
                    });
                    
                    // 3. 处理layers容器
                    const layers = document.querySelector('#layers');
                    if (layers) {
                        Array.from(layers.children).forEach(child => {
                            const style = window.getComputedStyle(child);
                            if (style.pointerEvents !== 'none') {
                                console.log('移除layers中的阻挡元素:', child);
                                child.remove();
                            }
                        });
                    }
                    
                    // 4. 移除所有可能的遮罩类
                    const maskClasses = [
                        'r-1p0dtai', 'r-1d2f490', 'r-1xcajam', 'r-zchlnj', 'r-ipm5af', 'r-1ffj0ar'
                    ];
                    maskClasses.forEach(className => {
                        document.querySelectorAll('.' + className).forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.position === 'fixed' || style.position === 'absolute') {
                                if (parseInt(style.zIndex) > 500) {
                                    console.log('移除遮罩类元素:', className, el);
                                    el.style.display = 'none';
                                    el.style.pointerEvents = 'none';
                                }
                            }
                        });
                    });
                    
                    // 5. 强制恢复body的交互
                    document.body.style.pointerEvents = 'auto';
                    document.documentElement.style.pointerEvents = 'auto';
                    
                    console.log('✅ 激进清理完成');
                })();
            """)
            return True
        except Exception as e:
            self.logger.debug(f"激进清理失败: {e}")
            return False

class ContentFilter:
    """内容过滤器"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = get_session_logger(session_id)
    
    def should_interact(self, content_info: Dict[str, Any], target_config: Any) -> bool:
        """判断是否应该与内容互动"""
        try:
            # 检查点赞数过滤
            like_count = content_info.get('like_count', 0)
            if isinstance(like_count, str):
                like_count = self._parse_count_string(like_count)
            
            if like_count < target_config.min_likes:
                self.logger.debug(f"Skipping content with {like_count} likes (min: {target_config.min_likes})")
                return False
            
            # 检查语言过滤
            content_text = content_info.get('content', '').lower()
            languages_to_check = target_config.content_languages or target_config.languages
            if languages_to_check:
                # 语言检测
                has_valid_language = any(
                    self._detect_language(content_text, lang) 
                    for lang in languages_to_check
                )
                if not has_valid_language:
                    self.logger.info(f"🌍 跳过非目标语言内容: {content_text[:50]}...")
                    return False
            
            # 检查排除关键词
            if target_config.exclude_keywords:
                for keyword in target_config.exclude_keywords:
                    if keyword.lower() in content_text:
                        self.logger.debug(f"Skipping content containing excluded keyword: {keyword}")
                        return False
            
            # 检查目标关键词（如果设置了的话）
            if target_config.keywords:
                has_target_keyword = any(
                    keyword.lower() in content_text 
                    for keyword in target_config.keywords
                )
                if not has_target_keyword:
                    self.logger.debug(f"Skipping content without target keywords")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in content filter: {e}")
            return False
    
    def _parse_count_string(self, count_str: str) -> int:
        """解析计数字符串（如 "1.2K", "5M"）"""
        try:
            count_str = count_str.strip().upper()
            if 'K' in count_str:
                return int(float(count_str.replace('K', '')) * 1000)
            elif 'M' in count_str:
                return int(float(count_str.replace('M', '')) * 1000000)
            else:
                return int(count_str.replace(',', ''))
        except:
            return 0
    
    def _detect_language(self, text: str, target_lang: str) -> bool:
        """改进的语言检测"""
        if not text.strip():
            return False
            
        if target_lang == 'en':
            # 英文检测：多种策略结合
            text_lower = text.lower()
            
            # 策略1: 常见英文词汇
            english_words = [
                'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'this', 'that', 'have', 'has', 'had', 'will', 'would', 'can', 'could',
                'should', 'must', 'might', 'may', 'do', 'does', 'did', 'get', 'got',
                'make', 'made', 'take', 'took', 'come', 'came', 'go', 'went', 'see', 'saw',
                'know', 'new', 'first', 'last', 'long', 'great', 'little', 'own', 'other',
                'old', 'right', 'big', 'high', 'different', 'small', 'large', 'next',
                'early', 'young', 'important', 'few', 'public', 'bad', 'same', 'able',
                'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'about', 'out',
                'up', 'down', 'here', 'there', 'where', 'when', 'what', 'who', 'how', 'why'
            ]
            
            # 策略2: 英文专业词汇（AI、技术相关）
            tech_words = [
                'ai', 'artificial', 'intelligence', 'machine', 'learning', 'deep', 'neural',
                'technology', 'tech', 'innovation', 'data', 'algorithm', 'model', 'training',
                'programming', 'code', 'development', 'software', 'computer', 'digital'
            ]
            
            words = text_lower.split()
            if len(words) == 0:
                return False
            
            # 检查英文常用词
            common_word_count = sum(1 for word in words if any(eng_word == word for eng_word in english_words))
            # 检查英文专业词汇
            tech_word_count = sum(1 for word in words if any(tech_word in word for tech_word in tech_words))
            
            # 策略3: 字符检测（主要是拉丁字母）
            latin_chars = sum(1 for char in text if char.isalpha() and ord(char) < 256)
            total_alpha_chars = sum(1 for char in text if char.isalpha())
            
            # 综合判断
            if len(words) <= 3:  # 短文本
                # 短文本：有英文常用词或专业词汇就认为是英文
                return common_word_count > 0 or tech_word_count > 0 or (total_alpha_chars > 0 and latin_chars / total_alpha_chars > 0.8)
            else:  # 长文本
                # 长文本：英文词汇占比超过20%就认为是英文
                english_score = (common_word_count + tech_word_count) / len(words)
                latin_score = latin_chars / max(total_alpha_chars, 1)
                return english_score > 0.2 or latin_score > 0.7
            
        elif target_lang == 'zh':
            # 中文检测：包含中文字符，但排除日文
            chinese_chars = [char for char in text if '\u4e00' <= char <= '\u9fff']
            # 检查是否包含日文特有字符
            hiragana_chars = [char for char in text if '\u3040' <= char <= '\u309f']
            katakana_chars = [char for char in text if '\u30a0' <= char <= '\u30ff']
            
            # 如果包含较多平假名或片假名，可能是日文而非中文
            if len(text) > 0:
                hiragana_ratio = len(hiragana_chars) / len(text)
                katakana_ratio = len(katakana_chars) / len(text)
                chinese_ratio = len(chinese_chars) / len(text)
                
                # 如果日文字符占比较高，不认为是中文
                if hiragana_ratio > 0.1 or katakana_ratio > 0.1:
                    return False
                
                # 如果中文字符占比超过20%，且没有太多日文字符，认为是中文
                return chinese_ratio > 0.2
            
            return False
            
        elif target_lang == 'ja':
            # 日文检测：平假名、片假名、汉字
            japanese_chars = [char for char in text if 
                             '\u3040' <= char <= '\u309f' or  # 平假名
                             '\u30a0' <= char <= '\u30ff' or  # 片假名
                             '\u4e00' <= char <= '\u9fff']    # 汉字
            return len(text) > 0 and (len(japanese_chars) / len(text)) > 0.2
            
        elif target_lang == 'ko':
            # 韩文检测：韩文字符
            korean_chars = [char for char in text if '\uac00' <= char <= '\ud7af']
            return len(text) > 0 and (len(korean_chars) / len(text)) > 0.2
            
        elif target_lang == 'ar':
            # 阿拉伯文检测
            arabic_chars = [char for char in text if '\u0600' <= char <= '\u06ff']
            return len(text) > 0 and (len(arabic_chars) / len(text)) > 0.2
            
        else:
            # 其他语言暂时返回True（不过滤）
            return True 