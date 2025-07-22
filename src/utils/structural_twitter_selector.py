"""
结构化Twitter选择器
基于DOM结构推理和多重证据验证的稳定选择器实现
"""
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from playwright.async_api import Page, Locator
import logging

logger = logging.getLogger(__name__)

class StructuralTwitterSelector:
    """
    基于结构化推理的Twitter元素选择器
    
    核心理念:
    1. 层次化搜索: 推文容器 → 交互区域 → 具体按钮
    2. 多重证据验证: data-testid + aria-label + SVG特征 + 位置
    3. 智能降级: 主选择器失败时使用推理链
    4. 上下文感知: 在特定区域内查找提高准确性
    """
    
    def __init__(self, page: Page):
        self.page = page
        
        # SVG路径特征库（基于测试结果）
        self.svg_signatures = {
            "reply": ["M1.751 10c0-4.42 3.584-8 8.005", "M1.751"],
            "like": ["M16.697 5.5c-1.222-.06-2.679.5", "M16.697"],
            "retweet": ["M4.5 3.88l4.432 4.14-1.364 1.4", "M4.5 3.88"],
            "bookmark": ["M4 4.5C4 3.12 5.119", "M4 4.5C4"],
            "share": ["M12 2.59l5.7 5.7-1.4", "M12 2.59"],
            "more": ["M3 12c0-1.1.9-2 2-2s", "M3 12c0-1.1"]
        }
        
        # aria-label关键词
        self.aria_keywords = {
            "reply": ["reply", "replies", "回复"],
            "like": ["like", "likes", "点赞"],  
            "retweet": ["repost", "reposts", "retweet", "转推", "转发"],
            "bookmark": ["bookmark", "书签"],
            "share": ["share", "分享"],
            "more": ["more", "更多"]
        }

    async def find_tweet_containers(self, limit: int = 10) -> List[Locator]:
        """
        使用结构化方法查找推文容器
        """
        strategies = [
            'article[data-testid="tweet"]',          # 最准确
            'article[role="article"]:has(div[role="group"])',  # 包含交互区域
            'div[data-testid="tweet"]',              # 备选testid方式
            'article:has([data-testid="reply"])',    # 包含回复按钮
            'article'                                # 最宽泛
        ]
        
        for strategy in strategies:
            try:
                containers = await self.page.locator(strategy).all()
                if containers and len(containers) > 0:
                    logger.info(f"使用策略 '{strategy}' 找到 {len(containers)} 个推文容器")
                    return containers[:limit]
            except Exception as e:
                logger.debug(f"策略 '{strategy}' 失败: {e}")
                continue
        
        logger.warning("未找到推文容器")
        return []

    async def find_interaction_area(self, tweet_container: Locator) -> Optional[Locator]:
        """
        在推文容器中查找交互按钮区域
        """
        strategies = [
            # 策略1: 通过role="group"查找（Twitter标准）
            'div[role="group"]:has(button[data-testid="reply"])',
            'div[role="group"]:has(button)',
            
            # 策略2: 通过多个交互元素识别
            'div:has(button[data-testid="reply"]):has(button[data-testid="like"])',
            'div:has([data-testid="reply"]):has([data-testid="like"])',
            
            # 策略3: 通过SVG图标集合识别
            'div:has(svg):has(button)',
            
            # 策略4: 通过aria-label模式识别
            'div:has(button[aria-label*="Reply"]):has(button[aria-label*="Like"])'
        ]
        
        for strategy in strategies:
            try:
                areas = await tweet_container.locator(strategy).all()
                for area in areas:
                    # 验证这个区域是否真的包含多个交互按钮
                    button_count = await area.locator('button, div[role="button"], [tabindex="0"]:has(svg)').count()
                    if button_count >= 3:  # 至少包含回复、转推、点赞
                        return area
            except Exception as e:
                logger.debug(f"交互区域查找策略失败: {e}")
                continue
        
        return None

    async def find_reply_button(self, context: Optional[Locator] = None) -> Optional[Locator]:
        """查找回复按钮"""
        return await self._find_button_by_type("reply", context)

    async def find_like_button(self, context: Optional[Locator] = None) -> Optional[Locator]:
        """查找点赞按钮"""
        return await self._find_button_by_type("like", context)

    async def find_retweet_button(self, context: Optional[Locator] = None) -> Optional[Locator]:
        """查找转推按钮"""
        return await self._find_button_by_type("retweet", context)

    async def find_bookmark_button(self, context: Optional[Locator] = None) -> Optional[Locator]:
        """查找书签按钮"""
        return await self._find_button_by_type("bookmark", context)

    async def find_share_button(self, context: Optional[Locator] = None) -> Optional[Locator]:
        """查找分享按钮"""
        return await self._find_button_by_type("share", context)

    async def _find_button_by_type(self, button_type: str, context: Optional[Locator] = None) -> Optional[Locator]:
        """
        使用多重证据查找特定类型的按钮
        """
        search_base = context if context else self.page
        
        # 证据1: data-testid（最可靠，优先级最高）
        try:
            button = await search_base.locator(f'button[data-testid="{button_type}"], div[data-testid="{button_type}"]').first
            if await self._validate_button(button):
                logger.debug(f"通过data-testid找到{button_type}按钮")
                return button
        except:
            pass
        
        # 证据2: aria-label关键词
        keywords = self.aria_keywords.get(button_type, [])
        for keyword in keywords:
            try:
                button = await search_base.locator(f'button[aria-label*="{keyword}" i], div[aria-label*="{keyword}" i]').first
                if await self._validate_button(button):
                    logger.debug(f"通过aria-label关键词'{keyword}'找到{button_type}按钮")
                    return button
            except:
                continue
        
        # 证据3: SVG路径特征
        signatures = self.svg_signatures.get(button_type, [])
        for signature in signatures:
            try:
                button = await search_base.locator(f'button:has(svg path[d*="{signature}"]), div[role="button"]:has(svg path[d*="{signature}"])').first
                if await self._validate_button(button):
                    logger.debug(f"通过SVG特征找到{button_type}按钮")
                    return button
            except:
                continue
        
        # 证据4: 位置推理（基于Twitter标准布局）
        if context:  # 只在有上下文时使用位置推理
            try:
                buttons = await context.locator('button, div[role="button"]').all()
                if len(buttons) >= 3:
                    position_map = {"reply": 0, "retweet": 1, "like": 2}
                    if button_type in position_map:
                        candidate = buttons[position_map[button_type]]
                        if await self._validate_button(candidate):
                            logger.debug(f"通过位置推理找到{button_type}按钮")
                            return candidate
            except:
                pass
        
        logger.debug(f"未找到{button_type}按钮")
        return None

    async def _validate_button(self, button: Locator) -> bool:
        """验证按钮是否有效（可见且可用）"""
        try:
            is_visible = await button.is_visible()
            is_enabled = await button.is_enabled()
            return is_visible and is_enabled
        except:
            return False

    async def smart_click_button(self, button: Locator, button_name: str = "按钮") -> bool:
        """
        智能点击按钮，包含滚动、等待、重试机制
        """
        if not button:
            logger.warning(f"{button_name}未找到，无法点击")
            return False
        
        try:
            # 1. 滚动到可见位置
            await button.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            
            # 2. 等待元素稳定
            await button.wait_for(state="visible", timeout=3000)
            
            # 3. 尝试常规点击
            await button.click()
            logger.info(f"{button_name}点击成功")
            return True
            
        except Exception as e:
            logger.warning(f"{button_name}常规点击失败: {e}")
            
            # 4. 尝试强制点击
            try:
                await button.click(force=True)
                logger.info(f"{button_name}强制点击成功")
                return True
            except Exception as e2:
                logger.error(f"{button_name}强制点击也失败: {e2}")
                return False

    async def find_tweet_input_area(self) -> Optional[Locator]:
        """查找推文输入区域"""
        strategies = [
            '[data-testid="tweetTextarea_0"]',                          # 主要输入框
            'div[contenteditable="true"][aria-label*="Post text"]',     # 通过aria-label
            'div[contenteditable="true"][data-testid*="textbox"]',      # 通用textbox
            'div[contenteditable="true"]',                              # 任何可编辑div
            'textarea[placeholder*="What"]',                            # 传统textarea
        ]
        
        for strategy in strategies:
            try:
                element = await self.page.locator(strategy).first
                if await element.is_visible():
                    logger.debug(f"使用策略找到输入区域: {strategy}")
                    return element
            except:
                continue
        
        logger.warning("未找到推文输入区域")
        return None

    async def find_post_button(self) -> Optional[Locator]:
        """查找发布按钮"""
        strategies = [
            'button[data-testid="tweetButtonInline"]',     # 内联发布按钮
            'button[data-testid="tweetButton"]',           # 标准发布按钮
            'button:has-text("Post"):not([aria-label*="new posts"])',  # 通过文本，排除"new posts"
            'button:has-text("Tweet")',                    # 旧版文本
            'button[role="button"]:has(span:text("Post"))', # 通过span文本
        ]
        
        for strategy in strategies:
            try:
                element = await self.page.locator(strategy).first
                if await element.is_visible() and await element.is_enabled():
                    logger.debug(f"找到发布按钮: {strategy}")
                    return element
            except:
                continue
        
        logger.warning("未找到发布按钮")
        return None

    async def get_tweet_stats(self, tweet_container: Locator) -> Dict[str, Any]:
        """
        提取推文的互动数据（点赞数、转发数等）
        """
        stats = {
            "reply_count": 0,
            "retweet_count": 0,
            "like_count": 0,
            "view_count": 0
        }
        
        try:
            # 查找交互区域
            interaction_area = await self.find_interaction_area(tweet_container)
            if not interaction_area:
                return stats
            
            # 提取各种计数
            buttons = await interaction_area.locator('button[aria-label*="Replies"], button[aria-label*="reposts"], button[aria-label*="Likes"]').all()
            
            for button in buttons:
                try:
                    aria_label = await button.get_attribute("aria-label") or ""
                    aria_lower = aria_label.lower()
                    
                    # 使用正则提取数字
                    import re
                    numbers = re.findall(r'(\d+(?:,\d+)*)', aria_label)
                    if numbers:
                        count = int(numbers[0].replace(',', ''))
                        
                        if "replies" in aria_lower or "reply" in aria_lower:
                            stats["reply_count"] = count
                        elif "reposts" in aria_lower or "repost" in aria_lower:
                            stats["retweet_count"] = count
                        elif "likes" in aria_lower or "like" in aria_lower:
                            stats["like_count"] = count
                            
                except Exception as e:
                    logger.debug(f"解析按钮统计失败: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"获取推文统计失败: {e}")
        
        return stats

    async def execute_structured_interaction(self, action_type: str, tweet_index: int = 0) -> Tuple[bool, str]:
        """
        执行结构化的推文交互
        
        Returns:
            Tuple[bool, str]: (成功状态, 详细信息)
        """
        try:
            # 1. 获取推文容器
            tweet_containers = await self.find_tweet_containers()
            if not tweet_containers or len(tweet_containers) <= tweet_index:
                return False, f"未找到第{tweet_index + 1}个推文"
            
            tweet_container = tweet_containers[tweet_index]
            
            # 2. 查找交互区域
            interaction_area = await self.find_interaction_area(tweet_container)
            if not interaction_area:
                return False, "未找到交互区域"
            
            # 3. 根据动作类型查找对应按钮
            button = None
            if action_type == "reply":
                button = await self.find_reply_button(interaction_area)
            elif action_type == "like":
                button = await self.find_like_button(interaction_area)
            elif action_type == "retweet":
                button = await self.find_retweet_button(interaction_area)
            elif action_type == "bookmark":
                button = await self.find_bookmark_button(interaction_area)
            else:
                return False, f"不支持的操作类型: {action_type}"
            
            if not button:
                return False, f"未找到{action_type}按钮"
            
            # 4. 执行点击
            click_success = await self.smart_click_button(button, f"{action_type}按钮")
            if click_success:
                return True, f"{action_type}操作成功执行"
            else:
                return False, f"{action_type}按钮点击失败"
                
        except Exception as e:
            logger.error(f"结构化交互执行失败: {e}")
            return False, f"执行过程中出错: {str(e)}"

    async def wait_for_tweet_load(self, timeout: int = 10000) -> bool:
        """等待推文加载完成"""
        try:
            # 等待主容器出现
            await self.page.wait_for_selector('main[role="main"]', timeout=timeout)
            
            # 等待推文容器出现
            await self.page.wait_for_selector('article[data-testid="tweet"], article', timeout=timeout)
            
            # 额外等待内容稳定
            await asyncio.sleep(2)
            
            return True
        except Exception as e:
            logger.warning(f"等待推文加载超时: {e}")
            return False 