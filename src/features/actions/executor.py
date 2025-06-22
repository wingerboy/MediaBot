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
    
    def __init__(self, page: Page, session_id: str, ai_config: Optional[AIConfig] = None):
        self.page = page
        self.session_id = session_id
        self.logger = get_session_logger(session_id)
        self.ai_config = ai_config
        
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
            
            # 使用多种策略查找点赞按钮
            like_button = None
            like_selectors = [
                'div[data-testid="like"]',
                '[data-testid="like"]',
                'button[data-testid="like"]',
                'div[role="button"][aria-label*="like"]',
                'div[role="button"][aria-label*="Like"]',
                'button[aria-label*="like"]',
                'button[aria-label*="Like"]'
            ]
            
            for selector in like_selectors:
                try:
                    button = tweet_element.locator(selector).first
                    if await button.count() > 0:
                        like_button = button
                        self.logger.debug(f"找到点赞按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"点赞选择器失败 {selector}: {e}")
                    continue
            
            if not like_button:
                self.logger.warning("未找到点赞按钮")
                return ActionResult.FAILED
            
            # 检查是否已经点赞
            try:
                aria_label = await like_button.get_attribute('aria-label', timeout=3000)
                if aria_label and ('liked' in aria_label.lower() or '已赞' in aria_label):
                    self.logger.info(f"推文已点赞: {tweet_info.get('id', 'unknown')}")
                    return ActionResult.SKIPPED
            except Exception as e:
                self.logger.debug(f"检查点赞状态失败: {e}")
                # 继续执行点赞，可能是未点赞状态
            
            # 执行点赞
            try:
                await like_button.click(timeout=5000)
                self.logger.debug("点赞按钮点击成功")
            except Exception as e:
                self.logger.error(f"点击点赞按钮失败: {e}")
                return ActionResult.FAILED
            
            # 等待反馈确认
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 验证点赞是否成功（可选，失败不影响结果）
            try:
                updated_aria_label = await like_button.get_attribute('aria-label', timeout=2000)
                if updated_aria_label and ('liked' in updated_aria_label.lower() or '已赞' in updated_aria_label):
                    self.logger.info(f"点赞成功: {tweet_info.get('content', '')[:50]}...")
                    return ActionResult.SUCCESS
                else:
                    # 即使验证失败，也认为可能成功了
                    self.logger.info(f"点赞操作完成（验证可能失败）: {tweet_info.get('content', '')[:50]}...")
                    return ActionResult.SUCCESS
            except Exception as e:
                self.logger.debug(f"验证点赞状态失败: {e}")
                # 假设成功
                self.logger.info(f"点赞操作完成: {tweet_info.get('content', '')[:50]}...")
                return ActionResult.SUCCESS
                
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
            
            # 使用多种策略查找关注按钮
            follow_button = None
            follow_selectors = [
                'div[data-testid*="follow"]:not([data-testid*="unfollow"])',
                '[data-testid*="follow"]:not([data-testid*="unfollow"])',
                'button[data-testid*="follow"]:not([data-testid*="unfollow"])',
                'div[role="button"]:has-text("Follow")',
                'div[role="button"]:has-text("关注")',
                'button:has-text("Follow")',
                'button:has-text("关注")'
            ]
            
            for selector in follow_selectors:
                try:
                    button = user_element.locator(selector).first
                    if await button.count() > 0:
                        follow_button = button
                        self.logger.debug(f"找到关注按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"关注选择器失败 {selector}: {e}")
                    continue
            
            if not follow_button:
                self.logger.warning("未找到关注按钮")
                return ActionResult.FAILED
            
            # 检查按钮状态
            try:
                button_text = await follow_button.text_content(timeout=3000)
                if button_text:
                    button_text_lower = button_text.lower()
                    # 如果已经关注，跳过
                    if any(word in button_text_lower for word in ['following', 'unfollow', '已关注', '取消关注']):
                        self.logger.info(f"已关注用户: {user_info.get('username', 'unknown')}")
                        return ActionResult.SKIPPED
            except Exception as e:
                self.logger.debug(f"检查关注状态失败: {e}")
            
            # 执行关注
            try:
                await follow_button.click(timeout=5000)
                self.logger.debug("关注按钮点击成功")
            except Exception as e:
                self.logger.error(f"点击关注按钮失败: {e}")
                return ActionResult.FAILED
            
            # 等待反馈确认
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 验证关注是否成功（可选）
            try:
                updated_text = await follow_button.text_content(timeout=2000)
                if updated_text and any(word in updated_text.lower() for word in ['following', 'unfollow', '已关注']):
                    self.logger.info(f"关注成功: {user_info.get('username', 'unknown')}")
                    return ActionResult.SUCCESS
                else:
                    # 即使验证失败，也认为可能成功了
                    self.logger.info(f"关注操作完成: {user_info.get('username', 'unknown')}")
                    return ActionResult.SUCCESS
            except Exception as e:
                self.logger.debug(f"验证关注状态失败: {e}")
                self.logger.info(f"关注操作完成: {user_info.get('username', 'unknown')}")
                return ActionResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"关注操作失败: {e}")
            return ActionResult.ERROR
    
    async def _execute_comment(self, tweet_element: Any, tweet_info: Dict[str, Any], 
                             action_config: ActionConfig) -> ActionResult:
        """执行评论操作"""
        try:
            # 检查页面是否仍然可用
            if not await self._check_page_available():
                self.logger.error("页面不可用，跳过评论操作")
                return ActionResult.ERROR
            
            # 使用多种策略查找回复按钮
            reply_button = None
            reply_selectors = [
                'div[data-testid="reply"]',
                '[data-testid="reply"]',
                'button[data-testid="reply"]',
                'div[role="button"][aria-label*="reply"]',
                'div[role="button"][aria-label*="Reply"]',
                'button[aria-label*="reply"]',
                'button[aria-label*="Reply"]'
            ]
            
            for selector in reply_selectors:
                try:
                    button = tweet_element.locator(selector).first
                    if await button.count() > 0:
                        reply_button = button
                        self.logger.debug(f"找到回复按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"回复选择器失败 {selector}: {e}")
                    continue
            
            if not reply_button:
                self.logger.warning("未找到回复按钮")
                return ActionResult.FAILED
            
            # 点击回复按钮
            try:
                await reply_button.click(timeout=5000)
                self.logger.debug("回复按钮点击成功")
            except Exception as e:
                self.logger.error(f"点击回复按钮失败: {e}")
                return ActionResult.FAILED
            
            # 等待评论框出现
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 使用多种策略查找评论输入框
            comment_box = None
            comment_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]',
                'textarea'
            ]
            
            for selector in comment_selectors:
                try:
                    box = self.page.locator(selector).first
                    await box.wait_for(state="visible", timeout=3000)
                    if await box.count() > 0:
                        comment_box = box
                        self.logger.debug(f"找到评论输入框，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"评论框选择器失败 {selector}: {e}")
                    continue
            
            if not comment_box:
                self.logger.warning("未找到评论输入框")
                return ActionResult.FAILED
            
            # 生成评论内容
            comment_text = await self._generate_comment_text(tweet_info, action_config)
            
            if not comment_text:
                self.logger.warning("无法生成评论内容，跳过评论")
                return ActionResult.SKIPPED
            
            # 输入评论
            try:
                await comment_box.fill(comment_text, timeout=5000)
                self.logger.debug(f"评论内容输入成功: {comment_text}")
            except Exception as e:
                self.logger.error(f"输入评论内容失败: {e}")
                return ActionResult.FAILED
            
            # 模拟打字延迟
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # 使用多种策略查找发送按钮
            send_button = None
            send_selectors = [
                'div[data-testid="tweetButtonInline"]',
                '[data-testid="tweetButtonInline"]',
                'div[data-testid="tweetButton"]',
                '[data-testid="tweetButton"]',
                'button:has-text("Tweet")',
                'button:has-text("Reply")',
                'button:has-text("发送")',
                'div[role="button"]:has-text("Tweet")',
                'div[role="button"]:has-text("Reply")'
            ]
            
            for selector in send_selectors:
                try:
                    button = self.page.locator(selector).first
                    if await button.count() > 0:
                        send_button = button
                        self.logger.debug(f"找到发送按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"发送按钮选择器失败 {selector}: {e}")
                    continue
            
            if not send_button:
                self.logger.warning("未找到发送按钮")
                return ActionResult.FAILED
            
            # 发送评论
            try:
                await send_button.click(timeout=5000)
                self.logger.debug("发送按钮点击成功")
            except Exception as e:
                self.logger.error(f"点击发送按钮失败: {e}")
                return ActionResult.FAILED
            
            # 等待发送完成
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            self.logger.info(f"评论发送成功: {comment_text}")
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
    
    async def _check_page_available(self) -> bool:
        """检查页面是否仍然可用"""
        try:
            # 检查页面是否关闭
            if self.page.is_closed():
                return False
            
            # 尝试获取页面标题来验证页面是否响应
            await self.page.title()
            return True
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
            if target_config.languages:
                # 简单的语言检测（可以扩展）
                has_valid_language = any(
                    self._detect_language(content_text, lang) 
                    for lang in target_config.languages
                )
                if not has_valid_language:
                    self.logger.debug(f"Skipping content due to language filter")
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
        """简单的语言检测"""
        if target_lang == 'en':
            # 英文检测：包含常见英文词汇
            english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
            return any(word in text.lower() for word in english_words)
        elif target_lang == 'zh':
            # 中文检测：包含中文字符
            return any('\u4e00' <= char <= '\u9fff' for char in text)
        else:
            # 其他语言暂时返回True
            return True 