#!/usr/bin/env python3
"""
AutoX - 可配置的Twitter自动化任务系统
"""
import asyncio
import sys
import argparse
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.browser.manager import BrowserManager
from src.core.twitter.client import TwitterClient
from src.features.browse.timeline import TimelineBrowser
from src.features.actions.executor import ActionExecutor, ContentFilter
from src.config.task_config import SessionConfig, config_manager, ActionType
from src.services.ai_service import AIConfig
from src.utils.session_logger import get_session_logger, SessionLogger
from src.utils.session_data import SessionDataManager, ActionResult
from src.core.account.manager import AccountConfig, account_manager
from config.settings import settings

class AutoXSession:
    """AutoX自动化会话"""
    
    def __init__(self, session_config: SessionConfig, search_keywords: Optional[List[str]] = None, account_config: Optional[AccountConfig] = None):
        self.config = session_config
        self.session_id = session_config.session_id
        self.search_keywords = search_keywords or []
        self.account_config = account_config  # 新增账号配置
        
        # 初始化组件
        self.logger = get_session_logger(self.session_id)
        self.data_manager = SessionDataManager(self.session_id)
        self.browser_manager = None
        self.twitter_client = None
        self.timeline_browser = None
        self.action_executor = None
        self.content_filter = None
        
        # 会话状态
        self.start_time = datetime.now()
        self.action_counts = {action_type.value: 0 for action_type in ActionType}
        self.total_actions = 0
        self.is_running = False
    
    async def start(self):
        """启动会话"""
        try:
            self.logger.info(f"=== AutoX Session Starting ===")
            self.logger.info(f"Session ID: {self.session_id}")
            self.logger.info(f"Task Name: {self.config.name}")
            self.logger.info(f"Description: {self.config.description}")
            
            # 账号信息
            if self.account_config:
                self.logger.info(f"Account: {self.account_config.account_id} (@{self.account_config.username})")
                self.logger.info(f"Display Name: {self.account_config.display_name}")
            
            # 启动浏览器
            self.browser_manager = BrowserManager()
            await self.browser_manager.start(headless=False)  # 设置为非headless模式
            
            # 初始化客户端
            self.twitter_client = TwitterClient(self.browser_manager.page)
            
            # 加载账号cookies（如果配置了账号）
            if self.account_config and Path(self.account_config.cookies_file).exists():
                try:
                    await self.browser_manager.load_cookies(self.account_config.cookies_file)
                    self.logger.info(f"Loaded cookies from: {self.account_config.cookies_file}")
                    
                    # 设置可能已登录的标志
                    self.twitter_client.cookies_loaded = True
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load cookies: {e}")
                    self.twitter_client.cookies_loaded = False
            else:
                self.twitter_client.cookies_loaded = False
            
            # 创建AI配置（如果有API密钥）
            ai_config = None
            if settings.DEEPSEEK_API_KEY:
                ai_config = AIConfig(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL,
                    model=settings.DEEPSEEK_MODEL,
                    temperature=settings.DEEPSEEK_TEMPERATURE,
                    max_tokens=settings.DEEPSEEK_MAX_TOKENS,
                    timeout=settings.DEEPSEEK_TIMEOUT
                )
                self.logger.info("AI配置已创建，支持智能评论生成")
            else:
                self.logger.info("未配置DeepSeek API密钥，将使用模板评论")
            
            self.timeline_browser = TimelineBrowser(self.browser_manager)
            self.action_executor = ActionExecutor(self.browser_manager.page, self.session_id, ai_config, self.browser_manager)
            self.content_filter = ContentFilter(self.session_id)
            
            self.is_running = True
            self.logger.info("Session components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            await self.close()
            raise
    
    async def run_task(self):
        """执行主要任务"""
        try:
            # 检查登录状态
            if not await self.twitter_client.check_login_status():
                self.logger.info("Need to login, starting login process...")
                
                # 使用账号配置或默认设置登录
                if self.account_config:
                    login_success = await self.twitter_client.login(
                        username=self.account_config.username,
                        password=self.account_config.password,
                        email=self.account_config.email
                    )
                else:
                    login_success = await self.twitter_client.login(
                        username=settings.TWITTER_USERNAME,
                        password=settings.TWITTER_PASSWORD,
                        email=settings.TWITTER_EMAIL
                    )
                
                if not login_success:
                    self.logger.error("Login failed, cannot continue")
                    return
                
                # 保存cookies（如果配置了账号）
                if self.account_config:
                    try:
                        await self.browser_manager.save_cookies(self.account_config.cookies_file)
                        self.logger.info(f"Saved cookies to: {self.account_config.cookies_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to save cookies: {e}")
            
            # 开始执行配置的任务
            await self._execute_configured_actions()
            
        except Exception as e:
            self.logger.error(f"Error during task execution: {e}")
        finally:
            # 更新账号使用信息（不设置冷却）
            if self.account_config:
                try:
                    account_manager.update_account_usage(self.account_config.account_id)
                    self.logger.info(f"Updated usage for account: {self.account_config.account_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to update account usage: {e}")
            
            await self.close()
    
    async def _execute_configured_actions(self):
        """执行配置的行为 - 对每条推文执行所有启用的动作"""
        self.logger.info("Starting configured actions execution")
        
        # 计算总的时间限制
        max_end_time = self.start_time + timedelta(minutes=self.config.max_duration_minutes)
        
        # 获取所有启用的动作配置
        enabled_actions = [action for action in self.config.actions if action.enabled]
        if not enabled_actions:
            self.logger.warning("No enabled actions found")
            return
        
        self.logger.info(f"Enabled actions: {[action.action_type.value for action in enabled_actions]}")
        
        # 计算每种动作的剩余配额
        action_quotas = {
            action.action_type: action.count for action in enabled_actions
        }
        
        processed_items = set()  # 防止重复处理
        
        try:
            # 获取内容源
            content_source = await self._get_content_source()
            
            loop_count = 0
            consecutive_empty_iterations = 0
            max_consecutive_empty = 3  # 允许的最大连续空迭代次数
            
            while (self.total_actions < self.config.max_total_actions and
                   datetime.now() < max_end_time and
                   self.is_running and
                   any(quota > 0 for quota in action_quotas.values())):
                
                loop_count += 1
                remaining_time = (max_end_time - datetime.now()).total_seconds() / 60
                self.logger.debug(f"=== 循环 {loop_count} 开始 ===")
                self.logger.debug(f"剩余时间: {remaining_time:.1f}分钟, 总动作数: {self.total_actions}/{self.config.max_total_actions}")
                self.logger.debug(f"剩余配额: Like={action_quotas[ActionType.LIKE]}, Comment={action_quotas[ActionType.COMMENT]}, Follow={action_quotas[ActionType.FOLLOW]}")
                
                # 获取推文内容
                content_items = await self._extract_tweets_from_page()
                
                if not content_items:
                    consecutive_empty_iterations += 1
                    self.logger.warning(f"No content items found (连续第{consecutive_empty_iterations}次)")
                    
                    if consecutive_empty_iterations >= max_consecutive_empty:
                        self.logger.warning(f"连续{max_consecutive_empty}次无法获取内容，可能已到达时间线底部，结束任务")
                        break
                    
                    # 尝试滚动获取更多内容
                    try:
                        self.logger.info("尝试滚动获取更多内容...")
                        await self._scroll_for_more_content()
                        await asyncio.sleep(3)  # 增加等待时间
                        continue
                    except Exception as e:
                        self.logger.debug(f"Error scrolling: {e}")
                        break
                else:
                    consecutive_empty_iterations = 0  # 重置计数器
                    self.logger.debug(f"获取到 {len(content_items)} 条推文")
                
                items_processed_in_loop = 0
                actions_executed_in_loop = 0
                
                # 处理每个推文
                for item in content_items:
                    # 检查运行状态和限制
                    if (self.total_actions >= self.config.max_total_actions or
                        datetime.now() >= max_end_time or
                        not self.is_running or
                        all(quota <= 0 for quota in action_quotas.values())):
                        self.logger.info(f"达到终止条件 - 总动作:{self.total_actions}>={self.config.max_total_actions}, 时间超时:{datetime.now() >= max_end_time}, 运行中:{self.is_running}, 配额耗尽:{all(quota <= 0 for quota in action_quotas.values())}")
                        break
                    
                    item_id = item.get('id') or item.get('url', str(hash(str(item))))
                    if item_id in processed_items:
                        continue
                    
                    processed_items.add(item_id)
                    
                    # 内容过滤
                    try:
                        if not self.content_filter.should_interact(item, self.config.target):
                            continue
                    except Exception as e:
                        self.logger.debug(f"Error in content filter: {e}")
                        continue
                    
                    items_processed_in_loop += 1
                    self.logger.info(f"Processing tweet from @{item.get('username', 'Unknown')}: {item.get('content', '')[:50]}...")
                    
                    # 对这条推文执行所有启用的动作
                    tweet_actions_executed = 0
                    
                    for action_config in enabled_actions:
                        # 检查该动作是否还有配额
                        if action_quotas[action_config.action_type] <= 0:
                            continue
                        
                        # 检查时间和总数限制
                        if (self.total_actions >= self.config.max_total_actions or
                            datetime.now() >= max_end_time or
                            not self.is_running):
                            break
                        
                        # 对于follow动作，需要特殊处理（从推文提取用户信息）
                        if action_config.action_type == ActionType.FOLLOW:
                            # 构造用户信息用于follow动作，保留推文的互动数据用于条件检查
                            user_item = {
                                'username': item.get('username'),
                                'display_name': item.get('display_name'),
                                'user_handle': item.get('user_handle'),
                                'is_verified': item.get('is_verified', False),
                                'follower_count': item.get('follower_count', 0),
                                'element': item.get('element'),  # 推文元素，可能需要导航到用户页面
                                'id': f"user_{item.get('username')}",
                                
                                # 保留推文的互动数据用于条件检查
                                'like_count': item.get('like_count', '0'),
                                'retweet_count': item.get('retweet_count', '0'),
                                'reply_count': item.get('reply_count', '0'),
                                'view_count': item.get('view_count', '0'),
                                'content': item.get('content', ''),
                                'has_images': item.get('has_images', False),
                                'has_video': item.get('has_video', False),
                                'has_gif': item.get('has_gif', False)
                            }
                            execution_item = user_item
                        else:
                            execution_item = item
                        
                        # 执行动作
                        try:
                            result = await self._execute_action_on_item(action_config, execution_item)
                            
                            if result == ActionResult.SUCCESS:
                                action_quotas[action_config.action_type] -= 1
                                self.action_counts[action_config.action_type.value] += 1
                                self.total_actions += 1
                                tweet_actions_executed += 1
                                actions_executed_in_loop += 1
                                
                                self.logger.info(f"✅ {action_config.action_type.value} successful on @{item.get('username')} - Remaining quota: {action_quotas[action_config.action_type]}")
                            else:
                                self.logger.debug(f"❌ {action_config.action_type.value} failed/skipped on @{item.get('username')}")
                            
                            # 记录行为
                            serializable_details = {
                                key: value for key, value in execution_item.items() 
                                if key != 'element'
                            }
                            
                            self.data_manager.record_action(
                                action_type=action_config.action_type.value,
                                target_type="tweet" if action_config.action_type in [ActionType.LIKE, ActionType.RETWEET, ActionType.COMMENT] else "user",
                                target_id=execution_item.get('id', item_id),
                                result=result,
                                details=serializable_details
                            )
                            
                        except Exception as e:
                            self.logger.error(f"Error executing {action_config.action_type.value} on item {item_id}: {e}")
                            continue
                        
                        # 动作间间隔
                        if tweet_actions_executed > 0:  # 在动作之间添加间隔
                            try:
                                if self.config.randomize_intervals:
                                    interval = random.uniform(
                                        min(action.min_interval for action in enabled_actions),
                                        max(action.max_interval for action in enabled_actions)
                                    )
                                    await asyncio.sleep(interval)
                                else:
                                    await asyncio.sleep(action_config.min_interval)
                            except asyncio.CancelledError:
                                self.logger.info("Action execution cancelled")
                                return
                            except Exception as e:
                                self.logger.debug(f"Error in delay: {e}")
                    
                    # 推文处理完成的日志
                    if tweet_actions_executed > 0:
                        self.logger.info(f"Completed {tweet_actions_executed} actions on tweet from @{item.get('username')}")
                
                # 循环总结
                self.logger.debug(f"=== 循环 {loop_count} 完成 ===")
                self.logger.debug(f"本轮处理推文: {items_processed_in_loop}, 执行动作: {actions_executed_in_loop}")
                
                # 滚动获取更多内容
                if (self.total_actions < self.config.max_total_actions and
                    datetime.now() < max_end_time and
                    self.is_running and
                    any(quota > 0 for quota in action_quotas.values())):
                    try:
                        self.logger.debug("准备滚动获取更多内容...")
                        await self._scroll_for_more_content()
                        await asyncio.sleep(2)  # 等待内容加载
                    except asyncio.CancelledError:
                        self.logger.info("Scrolling cancelled")
                        return
                    except Exception as e:
                        self.logger.debug(f"Error scrolling: {e}")
                        
            # 循环结束原因分析
            self.logger.info("=== 循环结束原因分析 ===")
            self.logger.info(f"总动作限制: {self.total_actions} >= {self.config.max_total_actions} ? {self.total_actions >= self.config.max_total_actions}")
            self.logger.info(f"时间限制: 当前时间 >= 最大结束时间 ? {datetime.now() >= max_end_time}")
            self.logger.info(f"运行状态: {self.is_running}")
            self.logger.info(f"配额状态: {[(action.action_type.value, action_quotas[action.action_type]) for action in enabled_actions]}")
            self.logger.info(f"所有配额耗尽: {all(quota <= 0 for quota in action_quotas.values())}")
                        
        except Exception as e:
            self.logger.error(f"Error in configured actions execution: {e}")
        
        # 总结
        self.logger.info("Configured actions execution completed")
        for action in enabled_actions:
            executed = action.count - action_quotas[action.action_type]
            self.logger.info(f"{action.action_type.value}: {executed}/{action.count} completed")
    
    async def _execute_single_action_type(self, action_config, max_end_time):
        """执行单一类型的行为 - 保留此方法以防其他地方调用"""
        # 这个方法现在主要用于向后兼容，实际执行逻辑在_execute_configured_actions中
        pass
    
    async def _get_content_source(self):
        """获取内容源"""
        try:
            # 检查并恢复页面状态
            page_recovered = await self._check_and_recover_page_state()
            if not page_recovered:
                self.logger.error("无法恢复页面状态，任务终止")
                raise Exception("无法恢复页面状态")
            
            current_url = self.browser_manager.page.url
            self.logger.info(f"当前页面URL: {current_url}")
            
            # 确定目标URL
            target_url = None
            if self.search_keywords:
                # 选择一个关键词进行搜索
                keyword = random.choice(self.search_keywords)
                
                # 根据is_live参数决定排序方式
                if self.config.target.is_live:
                    target_url = f"https://x.com/search?q={keyword}&f=live"
                    self.logger.info(f"Using search results for keyword (最新): {keyword}")
                else:
                    target_url = f"https://x.com/search?q={keyword}"
                    self.logger.info(f"Using search results for keyword (热门): {keyword}")
            elif self.config.target.hashtags and len(self.config.target.hashtags) > 0:
                # 使用配置的hashtag
                hashtag = random.choice(self.config.target.hashtags)
                # 确保hashtag以#开头
                if not hashtag.startswith('#'):
                    hashtag = f"#{hashtag}"
                # URL编码hashtag
                import urllib.parse
                encoded_hashtag = urllib.parse.quote(hashtag)
                
                # 根据is_live参数决定排序方式
                if self.config.target.is_live:
                    target_url = f"https://x.com/search?q={encoded_hashtag}&src=hashtag_click&f=live"
                    self.logger.info(f"Using hashtag search (最新): {hashtag}")
                else:
                    target_url = f"https://x.com/search?q={encoded_hashtag}&src=hashtag_click"
                    self.logger.info(f"Using hashtag search (热门): {hashtag}")
            elif self.config.target.keywords and len(self.config.target.keywords) > 0:
                # 使用配置的关键词
                keyword = random.choice(self.config.target.keywords)
                
                # 根据is_live参数决定排序方式
                if self.config.target.is_live:
                    target_url = f"https://x.com/search?q={keyword}&f=live"
                    self.logger.info(f"Using keyword search (最新): {keyword}")
                else:
                    target_url = f"https://x.com/search?q={keyword}"
                    self.logger.info(f"Using keyword search (热门): {keyword}")
            else:
                # 使用主页时间线
                target_url = "https://x.com/home"
                self.logger.info("Using home timeline")
            
            # 检查是否需要导航
            need_navigation = True
            if target_url == "https://x.com/home":
                # 如果目标是主页，检查当前是否已经在主页
                if "x.com/home" in current_url or "twitter.com/home" in current_url:
                    self.logger.info("✅ 已在主页，无需重新导航")
                    need_navigation = False
            
            # 只有在需要时才导航
            if need_navigation:
                self.logger.info(f"导航到: {target_url}")
                await self.browser_manager.page.goto(target_url, timeout=20000)
                
                # 等待页面加载，使用更宽松的设置
                try:
                    await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
                    self.logger.info("页面DOM加载完成")
                except Exception as e:
                    self.logger.warning(f"等待DOM加载超时: {e}，继续执行")
                
                # 等待网络空闲（可选，允许失败）
                try:
                    await self.browser_manager.page.wait_for_load_state("networkidle", timeout=8000)
                    self.logger.info("页面网络空闲")
                except Exception as e:
                    self.logger.debug(f"等待网络空闲超时: {e}，继续执行")
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 手动检查并处理Cookie弹窗
            await self._handle_cookie_popup_manual()
            
            self.logger.info("✅ 内容源准备完成")
            
            # 根据使用的源返回适当的类型
            if "search" in target_url:
                return "search"
            else:
                return "timeline"
            
        except Exception as e:
            self.logger.error(f"获取内容源失败: {e}")
            raise

    async def _check_and_recover_page_state(self) -> bool:
        """检查并恢复页面状态"""
        try:
            self.logger.debug("检查页面状态...")
            
            # 第一层检查：页面是否关闭
            if self.browser_manager.page.is_closed():
                self.logger.error("页面已关闭，尝试重新创建...")
                return await self._recreate_page()
            
            # 第二层检查：执行上下文是否可用
            try:
                title = await self.browser_manager.page.title()
                current_url = self.browser_manager.page.url
                self.logger.debug(f"页面状态正常 - 标题: {title}, URL: {current_url}")
                
                # 第三层检查：是否被重定向到登录页面
                if await self._is_redirected_to_login():
                    self.logger.warning("检测到被重定向到登录页面，尝试重新登录...")
                    return await self._handle_login_redirect()
                
                # 第四层检查：是否在错误页面
                if await self._is_error_page():
                    self.logger.warning("检测到错误页面，尝试恢复...")
                    return await self._recover_from_error_page()
                
                self.logger.debug("✅ 页面状态检查通过")
                return True
                
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"页面执行上下文异常: {error_msg}")
                
                # 检查是否是执行上下文被销毁
                if "execution context was destroyed" in error_msg.lower() or "context was destroyed" in error_msg.lower():
                    self.logger.warning("检测到执行上下文被销毁，尝试恢复...")
                    return await self._recover_from_context_destroyed()
                
                # 检查是否是导航相关错误
                if "navigation" in error_msg.lower():
                    self.logger.warning("检测到导航相关错误，尝试重新导航...")
                    return await self._recover_from_navigation_error()
                
                # 其他未知错误
                self.logger.error(f"未知页面错误: {error_msg}")
                return await self._attempt_general_recovery()
                
        except Exception as e:
            self.logger.error(f"页面状态检查失败: {e}")
            return False

    async def _recreate_page(self) -> bool:
        """重新创建页面"""
        try:
            self.logger.info("尝试重新创建页面...")
            
            # 重新启动浏览器管理器
            await self.browser_manager.close()
            success = await self.browser_manager.start(headless=True)
            
            if success:
                # 重新初始化Twitter客户端
                self.twitter_client = TwitterClient(self.browser_manager.page)
                
                # 尝试加载保存的cookies进行自动登录
                await self._attempt_auto_login()
                
                self.logger.info("✅ 页面重新创建成功")
                return True
            else:
                self.logger.error("重新创建页面失败")
                return False
                
        except Exception as e:
            self.logger.error(f"重新创建页面失败: {e}")
            return False

    async def _is_redirected_to_login(self) -> bool:
        """检查是否被重定向到登录页面"""
        try:
            current_url = self.browser_manager.page.url
            title = await self.browser_manager.page.title()
            
            # 检查URL和标题
            login_indicators = [
                "login" in current_url.lower(),
                "flow/login" in current_url.lower(), 
                "log in" in title.lower(),
                "sign in" in title.lower(),
                "登录" in title.lower()
            ]
            
            if any(login_indicators):
                return True
            
            # 检查页面内容
            try:
                login_form = self.browser_manager.page.locator('input[autocomplete="username"], input[name="text"]')
                if await login_form.count() > 0:
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.debug(f"检查登录重定向失败: {e}")
            return False

    async def _is_error_page(self) -> bool:
        """检查是否在错误页面"""
        try:
            # 检查常见错误页面标识
            error_selectors = [
                'text="Something went wrong"',
                'text="出现了问题"',
                'text="Sorry, that page doesn\'t exist"',
                'text="Try again"',
                'text="Rate limited"'
            ]
            
            for selector in error_selectors:
                try:
                    if await self.browser_manager.page.locator(selector).count() > 0:
                        return True
                except:
                    continue
            
            # 检查页面内容
            try:
                page_content = await self.browser_manager.page.content()
                error_keywords = ["something went wrong", "出现了问题", "rate limited", "try again"]
                if any(keyword in page_content.lower() for keyword in error_keywords):
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.debug(f"检查错误页面失败: {e}")
            return False

    async def _handle_login_redirect(self) -> bool:
        """处理登录重定向"""
        try:
            self.logger.info("处理登录重定向...")
            
            # 尝试使用cookies自动登录
            login_success = await self._attempt_auto_login()
            
            if login_success:
                self.logger.info("✅ 自动登录成功")
                return True
            else:
                self.logger.warning("❌ 自动登录失败，可能需要手动登录")
                return False
                
        except Exception as e:
            self.logger.error(f"处理登录重定向失败: {e}")
            return False

    async def _recover_from_context_destroyed(self) -> bool:
        """从执行上下文被销毁中恢复"""
        try:
            self.logger.info("尝试从执行上下文销毁中恢复...")
            
            # 等待一段时间让页面稳定
            await asyncio.sleep(3)
            
            # 尝试刷新页面
            try:
                await self.browser_manager.page.reload(timeout=20000)
                await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
                self.logger.info("✅ 页面刷新成功")
                
                # 重新检查登录状态
                if await self._is_redirected_to_login():
                    return await self._handle_login_redirect()
                    
                return True
                
            except Exception as e:
                self.logger.warning(f"页面刷新失败: {e}")
                
                # 尝试重新导航到主页
                try:
                    await self.browser_manager.page.goto("https://x.com/home", timeout=20000)
                    await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
                    self.logger.info("✅ 重新导航到主页成功")
                    
                    # 检查是否需要登录
                    if await self._is_redirected_to_login():
                        return await self._handle_login_redirect()
                        
                    return True
                    
                except Exception as e2:
                    self.logger.error(f"重新导航失败: {e2}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"从执行上下文销毁中恢复失败: {e}")
            return False

    async def _recover_from_navigation_error(self) -> bool:
        """从导航错误中恢复"""
        try:
            self.logger.info("尝试从导航错误中恢复...")
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 尝试导航到安全页面
            await self.browser_manager.page.goto("https://x.com", timeout=20000)
            await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # 检查登录状态
            if await self._is_redirected_to_login():
                return await self._handle_login_redirect()
                
            self.logger.info("✅ 从导航错误中恢复成功")
            return True
            
        except Exception as e:
            self.logger.error(f"从导航错误中恢复失败: {e}")
            return False

    async def _recover_from_error_page(self) -> bool:
        """从错误页面恢复"""
        try:
            self.logger.info("尝试从错误页面恢复...")
            
            # 等待一段时间
            await asyncio.sleep(5)
            
            # 尝试刷新页面
            await self.browser_manager.page.reload(timeout=20000)
            await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # 如果仍然是错误页面，尝试导航到主页
            if await self._is_error_page():
                await self.browser_manager.page.goto("https://x.com/home", timeout=20000)
                await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            self.logger.info("✅ 从错误页面恢复成功")
            return True
            
        except Exception as e:
            self.logger.error(f"从错误页面恢复失败: {e}")
            return False

    async def _attempt_general_recovery(self) -> bool:
        """尝试通用恢复方法"""
        try:
            self.logger.info("尝试通用恢复方法...")
            
            # 策略1：等待并刷新
            await asyncio.sleep(3)
            try:
                await self.browser_manager.page.reload(timeout=20000)
                await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
                if not await self._is_error_page():
                    self.logger.info("✅ 刷新恢复成功")
                    return True
            except:
                pass
            
            # 策略2：重新导航
            try:
                await self.browser_manager.page.goto("https://x.com/home", timeout=20000)
                await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
                if not await self._is_error_page():
                    self.logger.info("✅ 重新导航恢复成功")
                    return True
            except:
                pass
            
            # 策略3：重新创建页面
            return await self._recreate_page()
            
        except Exception as e:
            self.logger.error(f"通用恢复方法失败: {e}")
            return False

    async def _attempt_auto_login(self) -> bool:
        """尝试自动登录"""
        try:
            if not self.account_config:
                self.logger.debug("未配置账号信息，跳过自动登录")
                return False
            
            self.logger.info("尝试自动登录...")
            
            # 尝试使用Twitter客户端的check_login_status方法
            try:
                is_logged_in = await self.twitter_client.check_login_status()
                if is_logged_in:
                    self.logger.info("✅ 检测到已登录状态")
                    return True
            except Exception as e:
                self.logger.debug(f"登录状态检查失败: {e}")
            
            # 如果未登录，尝试加载cookies
            try:
                await self.twitter_client.load_cookies(self.account_config.account_id)
                
                # 导航到主页验证登录状态
                await self.browser_manager.page.goto("https://x.com/home", timeout=20000)
                await self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=15000)
                
                # 再次检查登录状态
                is_logged_in = await self.twitter_client.check_login_status()
                if is_logged_in:
                    self.logger.info("✅ 通过cookies自动登录成功")
                    return True
                else:
                    self.logger.warning("❌ cookies登录失败")
                    return False
                    
            except Exception as e:
                self.logger.debug(f"cookies登录失败: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"自动登录失败: {e}")
            return False
    
    async def _handle_cookie_popup_manual(self):
        """手动检查并处理Cookie弹窗"""
        try:
            # 等待页面完全加载
            await asyncio.sleep(2)
            
            # 检查是否存在Cookie同意遮罩层
            cookie_mask = self.browser_manager.page.locator('[data-testid="twc-cc-mask"]')
            mask_count = await cookie_mask.count()
            
            if mask_count > 0:
                self.logger.warning(f"⚠️ 检测到 {mask_count} 个Cookie遮罩层，尝试处理...")
                
                # 尝试多种方式关闭Cookie弹窗
                success = await self._dismiss_cookie_popup_manual()
                
                if success:
                    self.logger.info("✅ Cookie弹窗已手动处理成功")
                    await asyncio.sleep(2)  # 等待弹窗完全消失
                else:
                    self.logger.error("❌ 无法处理Cookie弹窗，这会影响后续操作")
                    # 强制移除遮罩层
                    await self._force_remove_cookie_mask()
            else:
                self.logger.debug("✅ 未检测到Cookie弹窗遮罩")
                
        except Exception as e:
            self.logger.warning(f"处理Cookie弹窗时出错: {e}")
    
    async def _dismiss_cookie_popup_manual(self) -> bool:
        """手动关闭Cookie弹窗的多种方法"""
        methods = [
            ("接受所有Cookies", self._accept_all_cookies),
            ("点击关闭按钮", self._click_close_button),
            ("按ESC键", self._press_escape),
            ("点击外部区域", self._click_outside),
            ("强制移除遮罩", self._force_remove_cookie_mask)
        ]
        
        for method_name, method_func in methods:
            try:
                self.logger.info(f"尝试方法: {method_name}")
                success = await method_func()
                if success:
                    self.logger.info(f"✅ {method_name} 成功")
                    return True
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.debug(f"❌ {method_name} 失败: {e}")
                continue
        
        return False
    
    async def _accept_all_cookies(self) -> bool:
        """接受所有Cookies"""
        selectors = [
            'button:has-text("Accept all cookies")',
            'button:has-text("接受所有Cookie")',
            'button:has-text("Accept")',
            'button:has-text("接受")',
            '[data-testid="BottomBar"] button',
            'div[data-testid="BottomBar"] button[role="button"]'
        ]
        
        for selector in selectors:
            try:
                button = self.browser_manager.page.locator(selector)
                if await button.count() > 0:
                    await button.first.click(timeout=5000)
                    await asyncio.sleep(2)
                    # 检查遮罩是否消失
                    if await self.browser_manager.page.locator('[data-testid="twc-cc-mask"]').count() == 0:
                        return True
            except Exception as e:
                self.logger.debug(f"点击按钮失败 {selector}: {e}")
                continue
        return False
    
    async def _click_close_button(self) -> bool:
        """点击关闭按钮"""
        selectors = [
            'button[aria-label*="close"]',
            'button[aria-label*="Close"]',
            'button[aria-label*="关闭"]',
            'svg[data-testid="icon-x"]',
            '[data-testid="icon-x"]'
        ]
        
        for selector in selectors:
            try:
                button = self.browser_manager.page.locator(selector)
                if await button.count() > 0:
                    await button.first.click(timeout=5000)
                    await asyncio.sleep(2)
                    if await self.browser_manager.page.locator('[data-testid="twc-cc-mask"]').count() == 0:
                        return True
            except Exception as e:
                self.logger.debug(f"点击关闭按钮失败 {selector}: {e}")
                continue
        return False
    
    async def _press_escape(self) -> bool:
        """按ESC键"""
        try:
            await self.browser_manager.page.keyboard.press('Escape')
            await asyncio.sleep(2)
            return await self.browser_manager.page.locator('[data-testid="twc-cc-mask"]').count() == 0
        except Exception as e:
            self.logger.debug(f"按ESC键失败: {e}")
            return False
    
    async def _click_outside(self) -> bool:
        """点击外部区域"""
        try:
            # 点击页面多个位置
            positions = [
                {'x': 100, 'y': 100},
                {'x': 500, 'y': 200},
                {'x': 800, 'y': 300}
            ]
            
            for pos in positions:
                try:
                    await self.browser_manager.page.click('body', position=pos, timeout=3000)
                    await asyncio.sleep(1)
                    if await self.browser_manager.page.locator('[data-testid="twc-cc-mask"]').count() == 0:
                        return True
                except:
                    continue
            return False
        except Exception as e:
            self.logger.debug(f"点击外部区域失败: {e}")
            return False
    
    async def _force_remove_cookie_mask(self) -> bool:
        """强制移除Cookie遮罩层"""
        try:
            self.logger.warning("🔧 强制移除Cookie遮罩层...")
            await self.browser_manager.page.evaluate("""
                // 移除Cookie同意遮罩
                const masks = document.querySelectorAll('[data-testid="twc-cc-mask"]');
                console.log('找到遮罩数量:', masks.length);
                masks.forEach((mask, index) => {
                    console.log('移除遮罩', index, mask);
                    mask.remove();
                });
                
                // 移除所有可能的覆盖层
                const layers = document.querySelectorAll('#layers > div');
                layers.forEach((layer, index) => {
                    const style = window.getComputedStyle(layer);
                    if (style.position === 'fixed' && 
                        (style.zIndex > 1000 || 
                         layer.classList.contains('r-1pi2tsx') ||
                         layer.classList.contains('r-1d2f490') ||
                         layer.classList.contains('r-1xcajam'))) {
                        console.log('移除覆盖层', index, layer);
                        layer.remove();
                    }
                });
                
                // 移除任何阻止交互的元素
                const blockers = document.querySelectorAll('div[style*="pointer-events"]');
                blockers.forEach((blocker, index) => {
                    const style = window.getComputedStyle(blocker);
                    if (style.pointerEvents === 'auto' && style.position === 'fixed') {
                        console.log('移除阻挡元素', index, blocker);
                        blocker.remove();
                    }
                });
                
                return true;
            """)
            
            await asyncio.sleep(2)
            mask_count = await self.browser_manager.page.locator('[data-testid="twc-cc-mask"]').count()
            success = mask_count == 0
            
            if success:
                self.logger.info("✅ 强制移除遮罩成功")
            else:
                self.logger.warning(f"⚠️ 强制移除后仍有 {mask_count} 个遮罩")
            
            return success
            
        except Exception as e:
            self.logger.error(f"强制移除遮罩失败: {e}")
            return False
    
    async def _check_and_dismiss_cookie_popup(self):
        """在每次操作前检查并关闭Cookie弹窗"""
        try:
            cookie_mask = self.browser_manager.page.locator('[data-testid="twc-cc-mask"]')
            mask_count = await cookie_mask.count()
            
            if mask_count > 0:
                self.logger.debug(f"🍪 检测到Cookie弹窗遮罩，尝试关闭...")
                success = await self._force_remove_cookie_mask()
                if success:
                    await asyncio.sleep(1)  # 等待遮罩消失
                    return True
                else:
                    return False
            return True
        except Exception as e:
            self.logger.debug(f"检查Cookie弹窗失败: {e}")
            return True
    
    async def _get_content_items(self, source_type: str, action_type: ActionType) -> List[Dict[str, Any]]:
        """获取内容项"""
        try:
            if action_type == ActionType.FOLLOW:
                # 对于关注行为，需要获取用户信息
                return await self._extract_users_from_page()
            else:
                # 对于其他行为，获取推文
                return await self._extract_tweets_from_page()
        except Exception as e:
            self.logger.error(f"Error getting content items: {e}")
            return []
    
    async def _extract_tweets_from_page(self) -> List[Dict[str, Any]]:
        """从页面提取推文信息"""
        tweets = []
        try:
            tweet_elements = await self.browser_manager.page.locator('article[data-testid="tweet"]').all()
            
            for i, tweet_element in enumerate(tweet_elements[:10]):  # 限制数量
                try:
                    tweet_data = await self.twitter_client._extract_tweet_data(tweet_element)
                    if tweet_data:
                        tweet_data['element'] = tweet_element
                        tweet_data['id'] = f"tweet_{i}_{hash(tweet_data.get('content', ''))}"
                        tweets.append(tweet_data)
                        
                        # 创建可序列化的数据副本（排除Locator对象）
                        serializable_data = {
                            key: value for key, value in tweet_data.items() 
                            if key != 'element'  # 排除Locator对象
                        }
                        
                        # 记录发现的目标
                        self.data_manager.record_target("tweet", tweet_data['id'], serializable_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting tweet {i}: {e}")
                    continue
            
            self.logger.debug(f"Extracted {len(tweets)} tweets from page")
            return tweets
            
        except Exception as e:
            self.logger.error(f"Error extracting tweets: {e}")
            return []
    
    async def _extract_users_from_page(self) -> List[Dict[str, Any]]:
        """从页面提取用户信息（从推文中提取，包含互动数据）"""
        users = []
        try:
            # 对于关注操作，我们需要从推文中提取用户信息，这样才能获得互动数据
            tweet_elements = await self.browser_manager.page.locator('article[data-testid="tweet"]').all()
            
            self.logger.debug(f"找到 {len(tweet_elements)} 个推文元素")
            
            for i, tweet_element in enumerate(tweet_elements[:10]):  # 限制数量
                try:
                    # 提取推文数据（包含用户信息和互动数据）
                    tweet_data = await self.twitter_client._extract_tweet_data(tweet_element)
                    
                    if tweet_data and tweet_data.get('username'):
                        # 构建用户数据，包含推文的互动信息
                        user_data = {
                            'username': tweet_data.get('username', 'Unknown'),
                            'display_name': tweet_data.get('display_name', 'Unknown'),
                            'is_verified': tweet_data.get('is_verified', False),
                            'element': tweet_element,  # 使用推文元素，因为关注按钮在推文中
                            'id': f"user_{tweet_data.get('username', 'unknown')}",
                            
                            # 包含推文的互动数据用于条件检查
                            'like_count': tweet_data.get('like_count', '0'),
                            'retweet_count': tweet_data.get('retweet_count', '0'),
                            'reply_count': tweet_data.get('reply_count', '0'),
                            'view_count': tweet_data.get('view_count', '0'),
                            'content': tweet_data.get('content', ''),
                            'has_images': tweet_data.get('has_images', False),
                            'has_video': tweet_data.get('has_video', False),
                            'has_gif': tweet_data.get('has_gif', False)
                        }
                        
                        # 避免重复用户
                        existing_usernames = [u.get('username') for u in users]
                        if user_data['username'] not in existing_usernames:
                            users.append(user_data)
                            
                            # 创建可序列化的数据副本（排除Locator对象）
                            serializable_data = {
                                key: value for key, value in user_data.items() 
                                if key != 'element'
                            }
                            
                            # 记录发现的目标
                            self.data_manager.record_target("user", user_data['id'], serializable_data)
                            
                            self.logger.debug(f"提取用户: {user_data['username']}, 推文赞数: {user_data['like_count']}")
                        
                except Exception as e:
                    self.logger.debug(f"Error extracting user from tweet {i}: {e}")
                    continue
            
            self.logger.debug(f"Extracted {len(users)} users from page")
            return users
            
        except Exception as e:
            self.logger.error(f"Error extracting users: {e}")
            return []
    
    async def _extract_user_info(self, user_element, strategy: str) -> Optional[Dict[str, Any]]:
        """从用户元素提取用户信息"""
        try:
            user_data = {
                'username': 'Unknown',
                'display_name': 'Unknown',
                'is_verified': False,
                'element': user_element,
                'id': 'unknown'
            }
            
            # 根据不同策略提取用户信息
            if 'User-Name' in strategy:
                # 从用户名区域提取
                await self._extract_from_user_name_area(user_element, user_data)
            elif 'href' in strategy:
                # 从链接提取
                await self._extract_from_user_link(user_element, user_data)
            elif 'Avatar' in strategy:
                # 从头像容器提取
                await self._extract_from_avatar_container(user_element, user_data)
            elif '@' in strategy:
                # 从@用户名提取
                await self._extract_from_at_mention(user_element, user_data)
            else:
                # 通用提取方法
                await self._extract_user_info_generic(user_element, user_data)
            
            # 验证提取的数据
            if user_data['username'] != 'Unknown' and user_data['username']:
                user_data['id'] = f"user_{user_data['username']}"
                return user_data
            
            return None
            
        except Exception as e:
            self.logger.debug(f"提取用户信息失败: {e}")
            return None
    
    async def _extract_from_user_name_area(self, user_element, user_data: Dict[str, Any]):
        """从用户名区域提取信息"""
        try:
            # 显示名称
            display_name_selectors = ['span', 'div', 'a']
            for selector in display_name_selectors:
                try:
                    name_elements = user_element.locator(selector)
                    count = await name_elements.count()
                    for i in range(min(count, 3)):
                        text = await name_elements.nth(i).text_content()
                        if text and text.strip() and not text.startswith('@') and len(text.strip()) > 1:
                            user_data['display_name'] = text.strip()
                            break
                    if user_data['display_name'] != 'Unknown':
                        break
                except Exception as e:
                    self.logger.debug(f"获取显示名失败 {selector}: {e}")
                    continue
            
            # 用户名（@handle）
            handle_selectors = ['span:has-text("@")', 'a[href^="/"]']
            for selector in handle_selectors:
                try:
                    handle_elements = user_element.locator(selector)
                    count = await handle_elements.count()
                    for i in range(count):
                        if selector == 'a[href^="/"]':
                            href = await handle_elements.nth(i).get_attribute('href')
                            if href and href.startswith('/') and len(href) > 1:
                                username = href[1:].split('/')[0]
                                if username and len(username) > 0:
                                    user_data['username'] = username
                                    break
                        else:
                            text = await handle_elements.nth(i).text_content()
                            if text and '@' in text:
                                username = text.replace('@', '').strip()
                                if username and len(username) > 0:
                                    user_data['username'] = username
                                    break
                    if user_data['username'] != 'Unknown':
                        break
                except Exception as e:
                    self.logger.debug(f"获取用户名失败 {selector}: {e}")
                    continue
            
            # 验证标识
            try:
                verified_element = user_element.locator('svg[data-testid="icon-verified"]')
                user_data['is_verified'] = await verified_element.count() > 0
            except Exception as e:
                self.logger.debug(f"获取验证状态失败: {e}")
                
        except Exception as e:
            self.logger.debug(f"从用户名区域提取失败: {e}")
    
    async def _extract_from_user_link(self, user_element, user_data: Dict[str, Any]):
        """从用户链接提取信息"""
        try:
            href = await user_element.get_attribute('href')
            if href and href.startswith('/') and len(href) > 1:
                username = href[1:].split('/')[0]
                if username and len(username) > 0 and username not in ['i', 'home', 'search', 'notifications']:
                    user_data['username'] = username
                    
                    # 尝试获取显示名称
                    try:
                        text = await user_element.text_content()
                        if text and text.strip() and not text.startswith('@'):
                            user_data['display_name'] = text.strip()
                    except Exception as e:
                        self.logger.debug(f"获取链接显示名失败: {e}")
                        
        except Exception as e:
            self.logger.debug(f"从用户链接提取失败: {e}")
    
    async def _extract_from_avatar_container(self, user_element, user_data: Dict[str, Any]):
        """从头像容器提取信息"""
        try:
            # 查找相邻的用户名信息
            parent = user_element.locator('xpath=..')
            user_name_element = parent.locator('div[data-testid="User-Name"]')
            
            if await user_name_element.count() > 0:
                await self._extract_from_user_name_area(user_name_element.first, user_data)
                
        except Exception as e:
            self.logger.debug(f"从头像容器提取失败: {e}")
    
    async def _extract_from_at_mention(self, user_element, user_data: Dict[str, Any]):
        """从@提及提取信息"""
        try:
            text = await user_element.text_content()
            if text and '@' in text:
                username = text.replace('@', '').strip()
                if username and len(username) > 0:
                    user_data['username'] = username
                    user_data['display_name'] = text.strip()
                    
        except Exception as e:
            self.logger.debug(f"从@提及提取失败: {e}")
    
    async def _extract_user_info_generic(self, user_element, user_data: Dict[str, Any]):
        """通用用户信息提取方法"""
        try:
            # 尝试获取所有文本内容并解析
            text = await user_element.text_content()
            if text:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                for line in lines:
                    if '@' in line and len(line) > 1:
                        username = line.replace('@', '').strip()
                        if username and len(username) > 0:
                            user_data['username'] = username
                            break
                
                # 如果没有找到@用户名，尝试从href获取
                if user_data['username'] == 'Unknown':
                    try:
                        links = user_element.locator('a[href^="/"]')
                        count = await links.count()
                        for i in range(count):
                            href = await links.nth(i).get_attribute('href')
                            if href and href.startswith('/') and len(href) > 1:
                                username = href[1:].split('/')[0]
                                if username and len(username) > 0 and username not in ['i', 'home', 'search', 'notifications']:
                                    user_data['username'] = username
                                    break
                    except Exception as e:
                        self.logger.debug(f"从href获取用户名失败: {e}")
                
                # 设置显示名称
                if lines and user_data['display_name'] == 'Unknown':
                    for line in lines:
                        if not line.startswith('@') and len(line) > 1 and len(line) < 50:
                            user_data['display_name'] = line
                            break
                            
        except Exception as e:
            self.logger.debug(f"通用用户信息提取失败: {e}")
    
    async def _execute_action_on_item(self, action_config, item) -> ActionResult:
        """在项目上执行行为"""
        try:
            element = item.get('element')
            if not element:
                return ActionResult.ERROR
            
            # 在执行动作前检查并清除Cookie弹窗
            await self._check_and_dismiss_cookie_popup()
            
            result = await self.action_executor.execute_action(action_config, element, item)
            
            if result == ActionResult.SUCCESS:
                self.logger.info(f"Successfully executed {action_config.action_type.value} on {item.get('id', 'unknown')}")
            elif result == ActionResult.SKIPPED:
                self.logger.debug(f"Skipped {action_config.action_type.value} on {item.get('id', 'unknown')}")
            else:
                self.logger.warning(f"Failed {action_config.action_type.value} on {item.get('id', 'unknown')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            return ActionResult.ERROR
    
    async def _scroll_for_more_content(self):
        """滚动页面获取更多内容"""
        try:
            await self.browser_manager.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.debug(f"Error scrolling: {e}")
    
    async def close(self):
        """关闭会话"""
        try:
            if self.is_running:
                self.logger.info("=== Session Closing ===")
                
                # 生成会话摘要
                try:
                    summary = self.data_manager.get_action_summary()
                    self.logger.info(f"Session Summary:")
                    self.logger.info(f"  Total Actions: {summary['total_actions']}")
                    self.logger.info(f"  Success Rate: {summary['success_rate']:.2%}")
                    self.logger.info(f"  Actions by Type: {summary['actions_by_type']}")
                except Exception as e:
                    self.logger.warning(f"Error generating session summary: {e}")
                
                # 关闭数据管理器
                try:
                    self.data_manager.close_session()
                except Exception as e:
                    self.logger.warning(f"Error closing data manager: {e}")
                
                # 关闭浏览器
                try:
                    if self.browser_manager:
                        await self.browser_manager.close()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")
                
                self.is_running = False
                self.logger.info("=== Session Closed ===")
                
                # 关闭会话logger（放在最后）
                try:
                    SessionLogger.close_session_logger(self.session_id)
                except Exception as e:
                    print(f"Warning: Error closing session logger: {e}")
                
        except Exception as e:
            print(f"Error closing session: {e}")
            # 确保浏览器关闭
            try:
                if self.browser_manager:
                    await self.browser_manager.close()
            except:
                pass
            # 确保logger关闭
            try:
                SessionLogger.close_session_logger(self.session_id)
            except:
                pass

def create_sample_config(session_id: str, name: str) -> SessionConfig:
    """创建示例配置"""
    return config_manager.create_default_config(session_id, name)

def list_available_configs():
    """列出可用配置"""
    configs = config_manager.list_configs()
    if configs:
        print("Available task configurations:")
        for i, config_id in enumerate(configs, 1):
            print(f"  {i}. {config_id}")
    else:
        print("No saved configurations found.")
    return configs

async def run_session(session_config: SessionConfig, search_keywords: Optional[List[str]] = None):
    """运行单个会话"""
    session = AutoXSession(session_config, search_keywords)
    await session.start()
    await session.run_task()

async def run_multi_account_session(session_config: SessionConfig, search_keywords: Optional[List[str]] = None):
    """使用多账号运行会话"""
    print("🚀 多账号执行模式")
    
    # 获取可用账号
    available_accounts = account_manager.get_available_accounts()
    
    if not available_accounts:
        print("❌ 没有可用的账号，请先添加账号")
        print("使用命令: python get_cookies.py <account_id>")
        return
    
    print(f"📋 找到 {len(available_accounts)} 个可用账号")
    
    # 为每个账号执行任务
    for i, account in enumerate(available_accounts, 1):
        print(f"\n=== 账号 {i}/{len(available_accounts)}: {account.account_id} (@{account.username}) ===")
        
        try:
            # 创建会话
            session = AutoXSession(session_config, search_keywords, account)
            
            # 执行任务
            await session.start()
            await session.run_task()
            
            print(f"✅ 账号 {account.account_id} 执行完成")
            
        except Exception as e:
            print(f"❌ 账号 {account.account_id} 执行失败: {e}")
    
    print("\n🎉 所有账号执行完成!")
    
    # 显示统计信息
    stats = account_manager.get_account_stats()
    print(f"\n📊 账号状态统计:")
    print(f"总账号数: {stats['total']}")
    print(f"活跃账号: {stats['active']}")
    print(f"可用账号: {stats['available']}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoX - 可配置的Twitter自动化任务系统")
    parser.add_argument("--config", help="配置文件ID或路径")
    parser.add_argument("--name", default="AutoX Task", help="任务名称")
    parser.add_argument("--search", nargs="+", help="搜索关键词限制")
    parser.add_argument("--create-config", action="store_true", help="创建示例配置")
    parser.add_argument("--list-configs", action="store_true", help="列出可用配置")
    parser.add_argument("--session-id", help="自定义会话ID")
    parser.add_argument("--multi-account", action="store_true", help="使用多账号模式")
    parser.add_argument("--account-id", help="指定单个账号ID")
    
    args = parser.parse_args()
    
    # 检查环境变量
    if not any([settings.TWITTER_USERNAME, settings.TWITTER_PASSWORD]) and not args.multi_account and not args.account_id:
        print("Warning: Twitter credentials not configured in .env file")
    
    if args.list_configs:
        list_available_configs()
        return
    
    # 生成会话ID
    session_id = args.session_id or f"autox_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    if args.create_config:
        # 创建示例配置
        config = create_sample_config(session_id, args.name)
        config_path = config_manager.save_config(config)
        print(f"Sample configuration created: {config_path}")
        print(f"Edit the configuration file and run again with --config {session_id}")
        return
    
    # 加载配置
    if args.config:
        if Path(args.config).exists():
            # 从文件路径加载
            config = SessionConfig.load_from_file(Path(args.config))
        else:
            # 从ID加载
            config = config_manager.load_config(args.config)
        
        if not config:
            print(f"Configuration not found: {args.config}")
            return
    else:
        # 使用默认配置
        config = create_sample_config(session_id, args.name)
        print("Using default configuration (created on-the-fly)")
    
    # 更新会话ID
    config.session_id = session_id
    
    # 选择执行模式
    print(f"Starting AutoX session: {session_id}")
    print(f"Task: {config.name}")
    if args.search:
        print(f"Search keywords: {args.search}")
    
    if args.multi_account:
        # 多账号模式
        print("🔄 多账号模式")
        asyncio.run(run_multi_account_session(config, args.search))
    elif args.account_id:
        # 指定账号模式
        account = account_manager.get_account(args.account_id)
        if not account:
            print(f"❌ 账号 {args.account_id} 不存在")
            print("使用 'python get_cookies.py --list' 查看可用账号")
            return
        if not account.is_available():
            print(f"❌ 账号 {args.account_id} 不可用（可能被禁用）")
            return
        
        print(f"👤 指定账号模式: {account.account_id} (@{account.username})")
        
        async def run_with_account():
            session = AutoXSession(config, args.search, account)
            try:
                await session.start()
                await session.run_task()
                print(f"✅ 账号 {account.account_id} 执行完成")
            except Exception as e:
                print(f"❌ 账号 {account.account_id} 执行失败: {e}")
        
        asyncio.run(run_with_account())
    else:
        # 单账号模式（使用环境变量）
        print("🔐 单账号模式（环境变量）")
        asyncio.run(run_session(config, args.search))

if __name__ == "__main__":
    main() 