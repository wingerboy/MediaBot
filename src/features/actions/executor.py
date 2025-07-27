"""
行为执行器 - 实现具体的Twitter操作
"""
import random
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import Page

from ...utils.session_logger import get_session_logger
from ...utils.session_data import ActionResult
from ...utils.playwright_stable_selector import PlaywrightStableSelector
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
        
        # 初始化选择器 - 使用验证有效的方法
        self.selector = PlaywrightStableSelector(page)
        
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
        
        # 检查排除关键词条件
        if conditions.exclude_keywords:
            content_text = target_info.get('content', '').lower()
            for keyword in conditions.exclude_keywords:
                if keyword.lower() in content_text:
                    failure_reasons.append(f"包含排除关键词({keyword})")
                    break  # 只记录第一个匹配的关键词
        
        reason_str = "; ".join(failure_reasons) if failure_reasons else "未知原因"
        
        self.logger.debug(
            f"条件检查失败 [{action_type}] @{username} - "
            f"赞:{like_count} 转:{retweet_count} 回:{reply_count} 看:{view_count} "
            f"长度:{content_length} 验证:{is_verified} - 原因: {reason_str}"
        )
    
    async def _execute_like(self, tweet_element: Any, tweet_info: Dict[str, Any]) -> ActionResult:
        """执行点赞操作 - 使用验证有效的方法"""
        try:
            username = tweet_info.get('username', 'unknown')
            self.logger.debug(f"准备点赞推文: {username}")
            
            # 使用验证有效的选择器查找点赞按钮
            like_button = await self.selector.find_like_button(tweet_element)
            
            if not like_button:
                self.logger.warning(f"未找到点赞按钮 (@{username})")
                return ActionResult.FAILED
            
            # 检查是否已经点赞
            try:
                aria_label = await like_button.get_attribute("aria-label") or ""
                if "unlike" in aria_label.lower() or "已点赞" in aria_label.lower():
                    self.logger.info(f"已点赞过，跳过 (@{username})")
                    return ActionResult.SKIPPED
            except Exception as e:
                self.logger.debug(f"检查点赞状态失败: {e}")
            
            # 执行点赞 - 使用验证有效的安全点击方法
            success = await self.selector.safe_click_element(like_button, "点赞按钮")
            
            if success:
                self.logger.info(f"✅ 点赞成功 (@{username})")
                return ActionResult.SUCCESS
            else:
                self.logger.error(f"点赞失败 (@{username})")
                return ActionResult.ERROR
            
        except Exception as e:
            self.logger.error(f"点赞操作异常: {e}")
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
        """执行评论操作 - 增强版，包含完整的可用性检测和状态管理"""
        username = tweet_info.get('username', 'unknown')
        
        try:
            self.logger.debug(f"准备评论推文: {username}")
            
            # ====== 第一阶段：预检测 ======
            # 1. 确保页面干净
            await self.selector.ensure_clean_page_state()
            
            # 2. 检测回复可用性
            reply_status = await self._check_reply_availability(tweet_element, username)
            if reply_status != "available":
                self.logger.info(f"推文不支持评论: {reply_status} (@{username})")
                return ActionResult.SKIPPED
            
            # ====== 第二阶段：准备评论 ======
            # 3. 获取评论内容
            comment_text = await self._generate_comment_text(tweet_info, action_config)
            if not comment_text:
                self.logger.warning(f"未能获取评论内容 (@{username})")
                return ActionResult.FAILED
            
            # 4. 查找并点击回复按钮
            reply_button = await self.selector.find_reply_button(tweet_element)
            if not reply_button:
                self.logger.warning(f"未找到回复按钮 (@{username})")
                return ActionResult.FAILED
            
            self.logger.info(f"点击回复按钮...")
            if not await self.selector.safe_click_element(reply_button, "回复按钮"):
                self.logger.error(f"点击回复按钮失败 (@{username})")
                await self._ensure_modal_cleanup(username)
                return ActionResult.ERROR
            
            # ====== 第三阶段：处理评论模态框 ======
            # 5. 等待并验证模态框状态
            modal_result = await self._handle_comment_modal(comment_text, username)
            
            if modal_result == "success":
                # 6. 确保模态框完全关闭
                cleanup_success = await self._ensure_modal_cleanup(username)
                if cleanup_success:
                    self.logger.info(f"✅ 评论完成，状态清理成功 (@{username})")
                    return ActionResult.SUCCESS
                else:
                    self.logger.warning(f"⚠️ 评论完成，但状态清理失败 (@{username})")
                    return ActionResult.SUCCESS  # 评论本身成功了
            elif modal_result == "restricted":
                self.logger.info(f"📝 检测到评论限制，跳过此推文 (@{username})")
                await self._ensure_modal_cleanup(username)
                return ActionResult.SKIPPED
            else:
                self.logger.error(f"❌ 评论模态框处理失败 (@{username})")
                await self._ensure_modal_cleanup(username)
                return ActionResult.ERROR
                
        except Exception as e:
            self.logger.error(f"评论操作异常: {e}")
            await self._ensure_modal_cleanup(username)
            return ActionResult.ERROR

    async def _check_reply_availability(self, tweet_element: Any, username: str) -> str:
        """检测推文的回复可用性 - 使用data-testid策略"""
        try:
            # 1. 使用验证有效的方法查找回复按钮 [data-testid="reply"]
            reply_button = await self.selector.find_reply_button(tweet_element)
            if not reply_button:
                self.logger.debug(f"未找到回复按钮 (@{username})")
                return "no_button"
            
            # 2. 检查按钮是否被禁用
            is_disabled = await reply_button.get_attribute("disabled")
            if is_disabled:
                self.logger.debug(f"回复按钮被禁用 (@{username})")
                return "disabled"
            
            # 3. 检查按钮是否可见且可点击
            if not await reply_button.is_visible():
                self.logger.debug(f"回复按钮不可见 (@{username})")
                return "not_visible"
            
            # 4. 检查aria-label是否包含限制信息
            aria_label = await reply_button.get_attribute("aria-label") or ""
            if any(keyword in aria_label.lower() for keyword in ["restricted", "限制", "disabled", "禁用"]):
                self.logger.debug(f"回复按钮aria-label显示限制: {aria_label} (@{username})")
                return "restricted_aria"
            
            # 5. 检查推文容器是否有限制提示
            try:
                # 在推文容器中查找常见的限制提示
                restriction_patterns = [
                    'text=/replies.*restricted/i',
                    'text=/回复.*限制/i', 
                    'text=/作者.*限制/i',
                    'text=/conversation.*restricted/i'
                ]
                
                for pattern in restriction_patterns:
                    restriction_elements = await tweet_element.locator(pattern).all()
                    if restriction_elements:
                        for elem in restriction_elements:
                            if await elem.is_visible():
                                text = await elem.text_content() or ""
                                self.logger.debug(f"发现限制提示: {text} (@{username})")
                                return "restricted_text"
            except Exception as e:
                self.logger.debug(f"限制提示检测失败: {e}")
            
            return "available"
            
        except Exception as e:
            self.logger.debug(f"回复可用性检测失败: {e}")
            return "unknown"  # 不确定时假设可用，避免误报
    
    async def _handle_comment_modal(self, comment_text: str, username: str) -> str:
        """处理评论模态框的完整流程"""
        try:
            # 1. 等待模态框出现
            modal_appeared = False
            for attempt in range(10):  # 等待最多5秒
                await asyncio.sleep(0.5)
                dialogs = await self.page.locator('[role="dialog"]').all()
                if dialogs:
                    modal_appeared = True
                    break
            
            if not modal_appeared:
                self.logger.error(f"评论模态框未出现 (@{username})")
                return "no_modal"
            
            # 2. 获取最新的模态框
            dialogs = await self.page.locator('[role="dialog"]').all()
            dialog = dialogs[-1]
            self.logger.debug(f"发现 {len(dialogs)} 个模态框，使用最新的")
            
            # 3. 检测模态框内是否有限制提示
            restriction_check = await self._check_modal_restrictions(dialog)
            if restriction_check != "available":
                return restriction_check
            
            # 4. 查找并处理输入框
            input_result = await self._handle_comment_input(dialog, comment_text, username)
            if not input_result:
                return "input_failed"
            
            # 5. 查找并点击发布按钮
            post_result = await self._handle_post_button(dialog, username)
            if not post_result:
                return "post_failed"
            
            # 6. 等待发布完成
            await asyncio.sleep(2)
            
            return "success"
            
        except Exception as e:
            self.logger.error(f"评论模态框处理异常: {e}")
            return "error"
    
    async def _check_modal_restrictions(self, dialog) -> str:
        """检查模态框内的限制提示 - 使用DOM结构检测"""
        try:
            # 1. 检查是否有错误或警告的data-testid元素
            error_testids = [
                '[data-testid="error"]',
                '[data-testid="toast"]',
                '[data-testid="banner"]'
            ]
            
            for testid in error_testids:
                try:
                    elements = await dialog.locator(testid).all()
                    for elem in elements:
                        if await elem.is_visible():
                            text = await elem.text_content() or ""
                            if any(keyword in text.lower() for keyword in ["restrict", "limit", "can't reply", "限制", "无法回复"]):
                                self.logger.debug(f"检测到限制元素: {testid}, 内容: {text}")
                                return "restricted"
                except:
                    continue
            
            # 2. 检查role="alert"的警告消息
            try:
                alert_elements = await dialog.locator('[role="alert"]').all()
                for alert in alert_elements:
                    if await alert.is_visible():
                        text = await alert.text_content() or ""
                        if any(keyword in text.lower() for keyword in ["restrict", "can't", "unable", "限制", "无法"]):
                            self.logger.debug(f"检测到警告消息: {text}")
                            return "restricted"
            except:
                pass
            
            # 3. 检查常见的限制提示文本（使用更精确的文本匹配）
            restriction_texts = [
                "You can't reply to this conversation",
                "Replies to this Tweet are limited",
                "回复受限",
                "无法回复此对话",
                "作者已限制回复",
                "replies are restricted"
            ]
            
            for text_pattern in restriction_texts:
                try:
                    # 使用精确文本匹配而非正则表达式，提高准确性
                    elements = await dialog.locator(f'text={text_pattern}').all()
                    if not elements:
                        # 如果精确匹配失败，尝试包含匹配
                        elements = await dialog.locator(f'text*={text_pattern}').all()
                    
                    for elem in elements:
                        if await elem.is_visible():
                            self.logger.debug(f"检测到限制提示文本: {text_pattern}")
                            return "restricted"
                except:
                    continue
                            
            # 4. 检查是否缺少输入框（可能表示评论被限制）
            try:
                input_elements = await dialog.locator('[data-testid="tweetTextarea_0"], div[contenteditable="true"]').all()
                visible_inputs = []
                for inp in input_elements:
                    if await inp.is_visible():
                        visible_inputs.append(inp)
                
                if not visible_inputs:
                    self.logger.debug("模态框中未找到可见的输入框，可能被限制")
                    return "no_input"
            except:
                pass
        
            return "available"
            
        except Exception as e:
            self.logger.debug(f"限制检测失败: {e}")
            return "available"  # 检测失败时假设可用，避免误拦截
    
    async def _handle_comment_input(self, dialog, comment_text: str, username: str) -> bool:
        """处理评论输入框 - 使用验证有效的选择器策略"""
        try:
            # 查找输入框 - 与验证有效的perform_comment_action方法保持一致
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
                            self.logger.debug(f"找到输入框: {selector}")
                            break
                    if input_element:
                                break
                except:
                    continue
            
            if not input_element:
                self.logger.error(f"未找到有效的输入框 (@{username})")
                return False
            
            # 输入评论内容
            self.logger.info(f"输入评论内容: '{comment_text}' (@{username})")
            
            # 先点击确保聚焦
            await input_element.click()
            await asyncio.sleep(0.3)
                
            # 清空可能的默认内容
            await input_element.clear()
            await asyncio.sleep(0.2)
            
            # 输入内容
            await input_element.fill(comment_text)
            await asyncio.sleep(0.5)
            
            # 验证内容是否输入成功
            content = await input_element.text_content() or ""
            if comment_text in content:
                self.logger.debug(f"输入内容验证成功")
                return True
            else:
                self.logger.warning(f"输入内容验证失败，重试...")
                # 重试一次
                await input_element.clear()
                await asyncio.sleep(0.2)
                await input_element.type(comment_text)
                await asyncio.sleep(0.5)
                return True
                
        except Exception as e:
            self.logger.error(f"输入框处理失败: {e}")
            return False
    
    async def _handle_post_button(self, dialog, username: str) -> bool:
        """处理发布按钮 - 使用验证有效的选择器策略"""
        try:
            # 查找发布按钮 - 与验证有效的perform_comment_action方法保持一致
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
                            self.logger.debug(f"找到发布按钮: {selector}")
                            break
                    if post_button:
                        break
                except:
                    continue
            
            if not post_button:
                self.logger.error(f"未找到有效的发布按钮 (@{username})")
                return False
            
            # 点击发布按钮
            self.logger.info(f"点击发布按钮... (@{username})")
            await post_button.click()
            
            # 等待发布处理
            await asyncio.sleep(1)
            
            # 验证按钮状态变化（通常会变为disabled或loading状态）  
            try:
                is_disabled = await post_button.get_attribute("disabled")
                if is_disabled:
                    self.logger.debug("发布按钮已禁用，推文正在发布")
            except:
                pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"发布按钮处理失败: {e}")
            return False
    
    async def _ensure_modal_cleanup(self, username: str) -> bool:
        """确保模态框完全清理干净"""
        try:
            self.logger.debug(f"开始模态框清理检查... (@{username})")
            
            # 1. 等待一下让自然关闭过程完成
            await asyncio.sleep(1.5)
            
            # 2. 检查当前模态框状态
            cleanup_success = False
            for attempt in range(6):  # 最多尝试6次，每次间隔递增
                dialogs = await self.page.locator('[role="dialog"]').all()
                
                if not dialogs:
                    self.logger.debug(f"✅ 无模态框存在，清理完成 (@{username})")
                    cleanup_success = True
                    break
                                    
                self.logger.debug(f"第{attempt+1}次清理，发现{len(dialogs)}个模态框...")
                
                if attempt < 3:
                    # 前3次：温和方式
                    success = await self.selector.ensure_comment_modal_closed()
                    if success:
                        cleanup_success = True
                        break
                elif attempt < 5:
                    # 第4-5次：强制方式
                    await self.selector.force_close_modals()
                else:
                    # 最后一次：终极清理
                    await self._ultimate_modal_cleanup()
                
                # 递增等待时间
                await asyncio.sleep(0.5 + attempt * 0.2)
            
            # 3. 最终验证
            final_dialogs = await self.page.locator('[role="dialog"]').all()
            final_success = len(final_dialogs) == 0
            
            if final_success:
                self.logger.info(f"✅ 模态框清理完成 (@{username})")
            else:
                self.logger.warning(f"⚠️ 模态框清理不完全，剩余{len(final_dialogs)}个 (@{username})")
            
            return final_success
            
        except Exception as e:
            self.logger.error(f"模态框清理异常: {e}")
            return False
    
    async def _ultimate_modal_cleanup(self):
        """终极模态框清理方案"""
        try:
            self.logger.debug("🚨 执行终极模态框清理...")
            
            # 1. 多次ESC
            for _ in range(5):
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.1)
            
            # 2. 点击页面多个位置
            click_positions = [(50, 50), (100, 200), (200, 100)]
            for x, y in click_positions:
                try:
                    await self.page.mouse.click(x, y)
                    await asyncio.sleep(0.1)
                except:
                    continue
            
            # 3. 强制移除DOM元素
            await self.page.evaluate("""
                () => {
                    // 移除所有dialog角色的元素
                    document.querySelectorAll('[role="dialog"]').forEach(el => {
                        console.log('移除残留模态框:', el);
                        el.remove();
                    });
                    
                    // 移除高z-index的遮罩层
                    document.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed' && parseInt(style.zIndex) > 1000) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > window.innerWidth * 0.5 && rect.height > window.innerHeight * 0.5) {
                                console.log('移除大遮罩:', el);
                                el.remove();
                            }
                        }
                    });
                }
            """)
            
            self.logger.debug("✅ 终极清理完成")
            
        except Exception as e:
            self.logger.error(f"终极清理失败: {e}")
    
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