"""
智能 Provider 自动选择器

根据以下因素自动选择最佳可用的 API Provider：
1. 地理位置和网络可达性
2. API Key 配置状态
3. Provider 健康状态
4. 成本和性能权衡
"""

import os
import time
from typing import Dict, Optional, Tuple

import requests
from loguru import logger


class ProviderHealthChecker:
    """Provider 健康检查器"""

    # Provider 健康检查配置
    HEALTH_CHECK_ENDPOINTS = {
        "openai": "https://api.openai.com/v1/models",
        "openrouter": "https://openrouter.ai/api/v1/models",
        "google": "https://generativelanguage.googleapis.com/v1/models",
        "moonshot": "https://api.moonshot.cn/v1/models",
    }

    # 超时时间（秒）
    TIMEOUT = 3

    # 缓存健康状态（避免频繁检查）
    _cache: Dict[str, Tuple[bool, float]] = {}
    CACHE_TTL = 300  # 5分钟缓存

    @classmethod
    def is_reachable(cls, provider: str, api_key: Optional[str] = None) -> bool:
        """
        检查 Provider 是否可达

        Args:
            provider: Provider 名称
            api_key: API Key（可选）

        Returns:
            bool: 是否可达
        """
        # 检查缓存
        if provider in cls._cache:
            is_healthy, timestamp = cls._cache[provider]
            if time.time() - timestamp < cls.CACHE_TTL:
                return is_healthy

        # 获取健康检查端点
        endpoint = cls.HEALTH_CHECK_ENDPOINTS.get(provider)
        if not endpoint:
            logger.debug(f"No health check endpoint for {provider}, assume reachable")
            return True

        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(
                endpoint, headers=headers, timeout=cls.TIMEOUT, allow_redirects=True
            )

            # 2xx 或 401/403 都说明网络可达（401/403 是认证问题，不是网络问题）
            is_reachable = response.status_code < 500

            # 更新缓存
            cls._cache[provider] = (is_reachable, time.time())

            if is_reachable:
                logger.debug(
                    f"✅ {provider} is reachable (status: {response.status_code})"
                )
            else:
                logger.warning(
                    f"⚠️  {provider} returned error (status: {response.status_code})"
                )

            return is_reachable

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  {provider} health check timeout")
            cls._cache[provider] = (False, time.time())
            return False

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"❌ {provider} connection error: {e}")
            cls._cache[provider] = (False, time.time())
            return False

        except Exception as e:
            logger.warning(f"⚠️  {provider} health check failed: {e}")
            # 未知错误，假设可达（避免误报）
            return True

    @classmethod
    def clear_cache(cls):
        """清除健康状态缓存"""
        cls._cache.clear()


class ProviderAutoSelector:
    """
    智能 Provider 自动选择器

    根据地理位置、网络环境、API Key 配置等因素
    自动选择最佳可用的 Provider
    """

    # Provider 优先级配置（按地区）
    # 格式: {region: [(provider, priority_score)]}
    PROVIDER_PRIORITIES = {
        # 中国大陆（无VPN）
        "cn_no_vpn": [
            ("openai", 95),  # OpenAI 在国内可用，稳定性高
            ("moonshot", 90),  # 国内服务商，低延迟
            ("google", 85),  # Google 亚太区可用
            ("siliconflow", 80),  # 国内服务商
            ("openrouter", 30),  # 需要VPN，低优先级
        ],
        # 中国大陆（有VPN）
        "cn_with_vpn": [
            ("openrouter", 95),  # 可访问所有模型
            ("openai", 90),  # 稳定快速
            ("google", 85),  # 多区域
            ("moonshot", 80),  # 国内备用
        ],
        # 国际（默认）
        "international": [
            ("openrouter", 95),  # 模型最多
            ("openai", 90),  # 稳定快速
            ("google", 85),  # 免费额度
            ("moonshot", 70),  # 可能延迟较高
        ],
    }

    # 模型映射（当切换 Provider 时使用等效模型）
    MODEL_EQUIVALENTS = {
        "openrouter": {
            "anthropic/claude-haiku-4.5": "anthropic/claude-haiku-4.5",
            "anthropic/claude-sonnet-4": "anthropic/claude-sonnet-4",
        },
        "openai": {
            "anthropic/claude-haiku-4.5": "gpt-4o-mini",
            "anthropic/claude-sonnet-4": "gpt-4o",
        },
        "moonshot": {
            "anthropic/claude-haiku-4.5": "moonshot-v1-8k",
            "anthropic/claude-sonnet-4": "moonshot-v1-32k",
        },
        "google": {
            "anthropic/claude-haiku-4.5": "gemini-2.5-flash",
            "anthropic/claude-sonnet-4": "gemini-2.5-pro",
        },
    }

    def __init__(self):
        self.health_checker = ProviderHealthChecker()

    def detect_region(self) -> str:
        """
        自动检测地理区域

        Returns:
            str: 区域标识 (cn_no_vpn, cn_with_vpn, international)
        """
        # 检查环境变量强制指定
        region_override = os.getenv("PROVIDER_REGION")
        if region_override in self.PROVIDER_PRIORITIES:
            logger.info(f"Using forced region: {region_override}")
            return region_override

        # 尝试检测 OpenRouter 可达性（判断是否有VPN）
        openrouter_reachable = self.health_checker.is_reachable("openrouter")

        # 检测是否在中国（简单方法：检查时区或语言）
        timezone = os.getenv("TZ", "")
        lang = os.getenv("LANG", "")
        is_china = "Asia/Shanghai" in timezone or "zh_CN" in lang

        if is_china and not openrouter_reachable:
            logger.info("Detected region: China (no VPN)")
            return "cn_no_vpn"
        elif is_china and openrouter_reachable:
            logger.info("Detected region: China (with VPN)")
            return "cn_with_vpn"
        else:
            logger.info("Detected region: International")
            return "international"

    def get_available_providers(self) -> Dict[str, str]:
        """
        获取所有已配置 API Key 的 Providers

        Returns:
            Dict[str, str]: {provider_name: api_key}
        """
        providers = {}

        api_key_env_vars = {
            "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "google": "GOOGLE_API_KEY",
            "moonshot": "MOONSHOT_API_KEY",
            "siliconflow": "SILICONFLOW_API_KEY",
            "azure": "AZURE_OPENAI_API_KEY",
        }

        for provider, env_var in api_key_env_vars.items():
            api_key = os.getenv(env_var)
            if api_key and api_key.strip():
                providers[provider] = api_key
                logger.debug(f"✅ {provider}: API key configured")
            else:
                logger.debug(f"⚠️  {provider}: No API key")

        return providers

    def select_best_provider(
        self, check_health: bool = True, fallback_count: int = 3
    ) -> Tuple[str, Optional[str]]:
        """
        自动选择最佳 Provider

        Args:
            check_health: 是否进行健康检查
            fallback_count: 返回的备用 Provider 数量

        Returns:
            Tuple[str, Optional[str]]: (best_provider, equivalent_model)
        """
        logger.info("🔍 Auto-selecting best provider...")

        # 1. 检测地理区域
        region = self.detect_region()
        priorities = self.PROVIDER_PRIORITIES[region]

        # 2. 获取已配置的 Providers
        available_providers = self.get_available_providers()

        if not available_providers:
            raise ValueError(
                "No API keys configured! Please set at least one provider's API key in .env"
            )

        logger.info(f"Available providers: {list(available_providers.keys())}")

        # 3. 按优先级排序并筛选
        candidates = []
        for provider, priority in priorities:
            if provider not in available_providers:
                continue

            # 健康检查（可选）
            if check_health:
                api_key = available_providers[provider]
                if not self.health_checker.is_reachable(provider, api_key):
                    logger.warning(f"⚠️  {provider} failed health check, skipping")
                    continue

            candidates.append((provider, priority))

        if not candidates:
            # 健康检查都失败了，使用最高优先级的（忽略健康检查）
            logger.warning("All health checks failed, using highest priority provider")
            for provider, priority in priorities:
                if provider in available_providers:
                    candidates.append((provider, priority))
                    break

        if not candidates:
            raise ValueError(
                f"No suitable provider found for region: {region}. "
                f"Available: {list(available_providers.keys())}"
            )

        # 4. 选择最佳 Provider
        best_provider = candidates[0][0]

        logger.info(f"✅ Selected best provider: {best_provider}")
        logger.info(
            f"📋 Fallback providers: {[p for p, _ in candidates[1 : fallback_count + 1]]}"
        )

        return best_provider, None

    def get_equivalent_model(self, original_model: str, target_provider: str) -> str:
        """
        获取等效模型

        Args:
            original_model: 原始模型 ID
            target_provider: 目标 Provider

        Returns:
            str: 等效模型 ID
        """
        equivalents = self.MODEL_EQUIVALENTS.get(target_provider, {})

        # 检查是否有直接映射
        if original_model in equivalents:
            return equivalents[original_model]

        # 如果没有映射，尝试使用 Provider 的默认模型
        # 这里简化处理，返回原模型（会在实际创建时使用 provider 的 default_model）
        return original_model


# 全局单例
_auto_selector = None


def get_auto_selector() -> ProviderAutoSelector:
    """获取全局 ProviderAutoSelector 实例"""
    global _auto_selector
    if _auto_selector is None:
        _auto_selector = ProviderAutoSelector()
    return _auto_selector


def auto_select_provider(check_health: bool = True) -> Tuple[str, Optional[str]]:
    """
    自动选择最佳 Provider（便捷函数）

    Args:
        check_health: 是否进行健康检查

    Returns:
        Tuple[str, Optional[str]]: (provider_name, equivalent_model)

    Example:
        >>> provider, model = auto_select_provider()
        >>> print(f"Best provider: {provider}")
    """
    selector = get_auto_selector()
    return selector.select_best_provider(check_health=check_health)
