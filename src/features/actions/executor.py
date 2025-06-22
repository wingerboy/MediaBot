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

class ActionExecutor:
    """行为执行器"""
    
    def __init__(self, page: Page, session_id: str):
        self.page = page
        self.session_id = session_id
        self.logger = get_session_logger(session_id)
        
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
                return await self._execute_comment(target_element, target_info, action_config.comment_templates)
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
        if not action_config.conditions:
            # 如果没有配置条件，默认允许执行
            return True
        
        try:
            # 创建ActionConditions实例并检查
            conditions = ActionConditions.from_dict(action_config.conditions)
            result = conditions.check_conditions(target_info)
            
            if not result:
                # 记录不满足的具体原因
                self._log_condition_details(action_config, target_info, conditions)
            
            return result
            
        except Exception as e:
            self.logger.error(f"检查条件时出错: {e}")
            # 出错时默认不执行，保守策略
            return False
    
    def _log_condition_details(self, action_config: ActionConfig, target_info: Dict[str, Any], 
                              conditions: ActionConditions):
        """记录条件检查的详细信息"""
        action_type = action_config.action_type.value
        username = target_info.get('username', 'Unknown')
        
        # 获取实际数据
        like_count = conditions._parse_count(target_info.get('like_count', '0'))
        retweet_count = conditions._parse_count(target_info.get('retweet_count', '0'))
        reply_count = conditions._parse_count(target_info.get('reply_count', '0'))
        view_count = conditions._parse_count(target_info.get('view_count', '0'))
        content_length = len(target_info.get('content', ''))
        is_verified = target_info.get('is_verified', False)
        
        self.logger.debug(
            f"条件检查失败 [{action_type}] @{username} - "
            f"赞:{like_count} 转:{retweet_count} 回:{reply_count} 看:{view_count} "
            f"长度:{content_length} 验证:{is_verified}"
        )
    
    async def _execute_like(self, tweet_element: Any, tweet_info: Dict[str, Any]) -> ActionResult:
        """执行点赞操作"""
        try:
            # 查找点赞按钮
            like_button = tweet_element.locator('div[data-testid="like"]')
            
            # 检查是否已经点赞
            aria_label = await like_button.get_attribute('aria-label')
            if aria_label and 'liked' in aria_label.lower():
                self.logger.info(f"Tweet {tweet_info.get('id', 'unknown')} already liked")
                return ActionResult.SKIPPED
            
            # 执行点赞
            await like_button.click()
            
            # 等待反馈确认
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 验证点赞是否成功
            updated_aria_label = await like_button.get_attribute('aria-label')
            if updated_aria_label and 'liked' in updated_aria_label.lower():
                self.logger.info(f"Successfully liked tweet: {tweet_info.get('content', '')[:50]}...")
                return ActionResult.SUCCESS
            else:
                self.logger.warning(f"Like action may have failed for tweet {tweet_info.get('id', 'unknown')}")
                return ActionResult.FAILED
                
        except Exception as e:
            self.logger.error(f"Error liking tweet: {e}")
            return ActionResult.ERROR
    
    async def _execute_follow(self, user_element: Any, user_info: Dict[str, Any]) -> ActionResult:
        """执行关注操作"""
        try:
            # 查找关注按钮
            follow_button = user_element.locator('div[data-testid*="follow"]')
            
            # 检查按钮文本
            button_text = await follow_button.text_content()
            if not button_text:
                return ActionResult.FAILED
            
            button_text = button_text.lower()
            
            # 如果已经关注，跳过
            if 'following' in button_text or 'unfollow' in button_text:
                self.logger.info(f"Already following user: {user_info.get('username', 'unknown')}")
                return ActionResult.SKIPPED
            
            # 执行关注
            if 'follow' in button_text:
                await follow_button.click()
                
                # 等待反馈确认
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # 验证关注是否成功
                updated_text = await follow_button.text_content()
                if updated_text and ('following' in updated_text.lower() or 'unfollow' in updated_text.lower()):
                    self.logger.info(f"Successfully followed user: {user_info.get('username', 'unknown')}")
                    return ActionResult.SUCCESS
                else:
                    self.logger.warning(f"Follow action may have failed for user {user_info.get('username', 'unknown')}")
                    return ActionResult.FAILED
            
            return ActionResult.FAILED
            
        except Exception as e:
            self.logger.error(f"Error following user: {e}")
            return ActionResult.ERROR
    
    async def _execute_comment(self, tweet_element: Any, tweet_info: Dict[str, Any], 
                             templates: List[str]) -> ActionResult:
        """执行评论操作"""
        try:
            # 查找回复按钮
            reply_button = tweet_element.locator('div[data-testid="reply"]')
            await reply_button.click()
            
            # 等待评论框出现
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 查找评论输入框
            comment_box = self.page.locator('div[data-testid="tweetTextarea_0"]')
            await comment_box.wait_for(state="visible", timeout=5000)
            
            # 选择评论内容
            if templates:
                comment_text = random.choice(templates)
            else:
                comment_text = self._get_default_comment()
            
            # 输入评论
            await comment_box.fill(comment_text)
            
            # 模拟打字延迟
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # 查找发送按钮
            send_button = self.page.locator('div[data-testid="tweetButtonInline"]')
            await send_button.click()
            
            # 等待发送完成
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            self.logger.info(f"Successfully commented on tweet: {comment_text}")
            return ActionResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"Error commenting on tweet: {e}")
            return ActionResult.ERROR
    
    async def _execute_retweet(self, tweet_element: Any, tweet_info: Dict[str, Any]) -> ActionResult:
        """执行转发操作"""
        try:
            # 查找转发按钮
            retweet_button = tweet_element.locator('div[data-testid="retweet"]')
            await retweet_button.click()
            
            # 等待转发选项出现
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # 查找确认转发按钮
            confirm_button = self.page.locator('div[data-testid="retweetConfirm"]')
            await confirm_button.click()
            
            # 等待转发完成
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            self.logger.info(f"Successfully retweeted: {tweet_info.get('content', '')[:50]}...")
            return ActionResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"Error retweeting: {e}")
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