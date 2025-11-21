"""
AH股溢价计算适配器 (AH Share Premium Adapter)

计算在A股和H股同时上市的股票的价格溢价，用于识别套利机会。

AH股溢价率 = (A股价格 * 汇率 - H股价格) / H股价格 * 100%
- 正值表示A股溢价（A股贵）
- 负值表示H股溢价（H股贵）

这是一个独立的工具类，专门用于双重上市股票分析。
使用AKShare库获取数据，无需额外API key。

数据来源: AKShare - 东方财富网AH股数据
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    ak = None
    pd = None

logger = logging.getLogger(__name__)

# AH股对照表 (港股代码 -> A股代码)
AH_STOCK_MAPPING = {
    # 金融类
    "00939": "601398",  # 建设银行
    "01398": "601398",  # 工商银行
    "03988": "601988",  # 中国银行
    "01288": "601328",  # 交通银行
    "02318": "601318",  # 中国平安
    "02628": "601628",  # 中国人寿
    # 能源类
    "00386": "600028",  # 中国石化
    "00857": "601857",  # 中国石油
    "00338": "600688",  # 中国海油
    # 科技类
    "00941": "601186",  # 中国移动
    "00728": "600050",  # 中国联通
    # 更多可以后续添加...
}


class AHPremiumAdapter:
    """
    AH股溢价计算适配器

    功能:
    - 计算单只股票的AH溢价率
    - 获取AH股溢价排行榜
    - 识别套利机会
    - 提供溢价趋势分析

    注意: 这不是BaseDataAdapter的子类，是独立的分析工具
    """

    def __init__(self):
        """初始化AH股溢价适配器"""
        if ak is None:
            raise ImportError(
                "AKShare is required for AHPremiumAdapter. "
                "Install with: pip install akshare"
            )

        logger.info("AHPremiumAdapter initialized")

    def calculate_premium(self, h_ticker: str) -> Optional[Dict]:
        """
        计算指定港股的AH股溢价

        Args:
            h_ticker: 港股代码，支持格式:
                      - "00700" (腾讯无AH股，返回None)
                      - "HKEX:00939" (建设银行，有AH股)
                      - "00939" (建设银行)

        Returns:
            Dict包含:
            - h_stock_code: 港股代码
            - h_stock_name: 港股名称
            - h_price: 港股价格 (HKD)
            - a_stock_code: A股代码
            - a_stock_name: A股名称
            - a_price: A股价格 (CNY)
            - exchange_rate: 人民币兑港币汇率
            - premium_rate: 溢价率 (%)
            - premium_type: "A股溢价" 或 "H股溢价"
            - arbitrage_opportunity: 套利机会评估

            如果不是AH股，返回None

        Example:
            >>> adapter = AHPremiumAdapter()
            >>> premium = adapter.calculate_premium("00939")
            >>> if premium:
            >>>     print(f"{premium['h_stock_name']} AH溢价率: {premium['premium_rate']:.2f}%")
        """
        try:
            # 清理ticker格式
            h_code = h_ticker.replace("HKEX:", "").strip()

            # 检查是否是AH股
            if h_code not in AH_STOCK_MAPPING:
                logger.info(f"{h_code} 不是AH股，无法计算溢价")
                return None

            a_code = AH_STOCK_MAPPING[h_code]

            # 使用AKShare获取AH股对比数据
            # API: stock_zh_ah_spot_em
            df = ak.stock_zh_ah_spot_em()

            if df is None or df.empty:
                logger.warning("AH股数据为空")
                return None

            # 查找该股票的数据
            # 尝试匹配港股代码
            h_code_variants = [h_code, h_code.lstrip("0"), f"0{h_code}"]
            stock_row = None

            for variant in h_code_variants:
                mask = df.astype(str).apply(
                    lambda row: row.str.contains(variant, na=False).any(), axis=1
                )
                if mask.any():
                    stock_row = df[mask].iloc[0]
                    break

            if stock_row is None:
                logger.warning(f"找不到{h_code}的AH股数据")
                return None

            # 提取数据（字段名可能变化，使用多个候选）
            h_name = self._extract_field(stock_row, ["名称", "港股名称", "h_name"])
            a_name = self._extract_field(stock_row, ["A股名称", "a_name"])
            h_price = self._extract_field(
                stock_row, ["港股价格", "H股价格", "h_price"], float
            )
            a_price = self._extract_field(stock_row, ["A股价格", "a_price"], float)
            premium_rate = self._extract_field(
                stock_row, ["溢价率", "premium_rate", "比价"], float
            )

            # 获取汇率 (CNY/HKD)
            # AKShare的溢价数据已经考虑了汇率
            exchange_rate = self._get_exchange_rate()

            # 如果AKShare没有提供溢价率，自己计算
            if premium_rate is None and h_price and a_price and exchange_rate:
                # 计算: (A股价格/汇率 - H股价格) / H股价格 * 100
                h_price_in_cny = h_price * exchange_rate
                premium_rate = ((a_price - h_price_in_cny) / h_price_in_cny) * 100

            if premium_rate is None:
                logger.warning(f"无法计算{h_code}的溢价率")
                return None

            # 构建结果
            result = {
                "h_stock_code": h_code,
                "h_stock_name": h_name or "未知",
                "h_price": round(h_price, 2) if h_price else 0.0,
                "h_currency": "HKD",
                "a_stock_code": a_code,
                "a_stock_name": a_name or "未知",
                "a_price": round(a_price, 2) if a_price else 0.0,
                "a_currency": "CNY",
                "exchange_rate": round(exchange_rate, 4),
                "premium_rate": round(premium_rate, 2),
                "premium_type": "A股溢价" if premium_rate > 0 else "H股溢价",
                "arbitrage_opportunity": self._assess_arbitrage(premium_rate),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            logger.info(f"{h_name} AH溢价率: {premium_rate:.2f}%")
            return result

        except Exception as e:
            logger.error(f"计算AH溢价失败 ({h_ticker}): {e}", exc_info=True)
            return None

    def get_all_ah_premiums(self) -> List[Dict]:
        """
        获取所有AH股的溢价情况

        Returns:
            List[Dict] 包含所有AH股的溢价数据，按溢价率排序

        Example:
            >>> adapter = AHPremiumAdapter()
            >>> premiums = adapter.get_all_ah_premiums()
            >>> top_5 = premiums[:5]
            >>> for stock in top_5:
            >>>     print(f"{stock['h_stock_name']}: {stock['premium_rate']:.2f}%")
        """
        try:
            df = ak.stock_zh_ah_spot_em()

            if df is None or df.empty:
                logger.warning("AH股数据为空")
                return []

            premiums = []
            for _, row in df.iterrows():
                premium_data = {
                    "h_stock_code": str(
                        self._extract_field(row, ["港股代码", "h_code"])
                    ),
                    "h_stock_name": str(
                        self._extract_field(row, ["名称", "港股名称", "h_name"])
                    ),
                    "h_price": self._extract_field(
                        row, ["港股价格", "H股价格", "h_price"], float
                    ),
                    "a_stock_code": str(
                        self._extract_field(row, ["A股代码", "a_code"])
                    ),
                    "a_stock_name": str(
                        self._extract_field(row, ["A股名称", "a_name"])
                    ),
                    "a_price": self._extract_field(row, ["A股价格", "a_price"], float),
                    "premium_rate": self._extract_field(
                        row, ["溢价率", "premium_rate", "比价"], float
                    ),
                }

                if premium_data["premium_rate"] is not None:
                    premium_data["premium_type"] = (
                        "A股溢价" if premium_data["premium_rate"] > 0 else "H股溢价"
                    )
                    premium_data["arbitrage_opportunity"] = self._assess_arbitrage(
                        premium_data["premium_rate"]
                    )
                    premiums.append(premium_data)

            # 按溢价率排序（从高到低）
            premiums.sort(key=lambda x: x["premium_rate"], reverse=True)

            logger.info(f"成功获取{len(premiums)}只AH股溢价数据")
            return premiums

        except Exception as e:
            logger.error(f"获取AH股溢价列表失败: {e}", exc_info=True)
            return []

    def get_arbitrage_opportunities(self, threshold: float = 10.0) -> Dict:
        """
        获取套利机会（溢价率超过阈值的股票）

        Args:
            threshold: 溢价率阈值（%），默认10%

        Returns:
            Dict包含:
            - high_a_premium: A股溢价超过阈值的股票列表（买H卖A）
            - high_h_premium: H股溢价超过阈值的股票列表（买A卖H）
            - count: 总数

        Example:
            >>> opportunities = adapter.get_arbitrage_opportunities(threshold=15.0)
            >>> print(f"发现{opportunities['count']}个套利机会")
        """
        try:
            all_premiums = self.get_all_ah_premiums()

            high_a_premium = [p for p in all_premiums if p["premium_rate"] > threshold]
            high_h_premium = [p for p in all_premiums if p["premium_rate"] < -threshold]

            result = {
                "high_a_premium": high_a_premium,
                "high_h_premium": high_h_premium,
                "count": len(high_a_premium) + len(high_h_premium),
                "threshold": threshold,
                "analysis": f"A股溢价机会{len(high_a_premium)}个，H股溢价机会{len(high_h_premium)}个",
            }

            logger.info(f"发现{result['count']}个套利机会（阈值{threshold}%）")
            return result

        except Exception as e:
            logger.error(f"获取套利机会失败: {e}", exc_info=True)
            return {"high_a_premium": [], "high_h_premium": [], "count": 0}

    def is_ah_stock(self, h_ticker: str) -> bool:
        """
        检查是否是AH股

        Args:
            h_ticker: 港股代码

        Returns:
            bool: True如果是AH股，False否则
        """
        h_code = h_ticker.replace("HKEX:", "").strip()
        return h_code in AH_STOCK_MAPPING

    def get_a_stock_code(self, h_ticker: str) -> Optional[str]:
        """
        获取对应的A股代码

        Args:
            h_ticker: 港股代码

        Returns:
            str: A股代码，如果不是AH股返回None
        """
        h_code = h_ticker.replace("HKEX:", "").strip()
        return AH_STOCK_MAPPING.get(h_code)

    # ===== 辅助方法 =====

    def _extract_field(self, row: pd.Series, candidates: List[str], dtype=str):
        """从DataFrame行中提取字段（支持多个候选列名）"""
        for candidate in candidates:
            if candidate in row.index and pd.notna(row[candidate]):
                try:
                    if dtype is float:
                        return float(row[candidate])
                    elif dtype is int:
                        return int(row[candidate])
                    else:
                        return str(row[candidate])
                except Exception:
                    continue
        return None

    def _get_exchange_rate(self) -> float:
        """
        获取人民币兑港币汇率

        Returns:
            float: CNY/HKD汇率，例如0.91表示1港币=0.91人民币
        """
        try:
            # 使用AKShare获取实时汇率
            # API: currency_latest
            df = ak.currency_latest(symbol="CNY/HKD")
            if df is not None and not df.empty:
                rate = float(df.iloc[0]["最新价"])
                return rate
        except Exception:
            pass

        # 如果获取失败，使用近似汇率
        logger.warning("无法获取实时汇率，使用默认值0.91")
        return 0.91

    def _assess_arbitrage(self, premium_rate: float) -> str:
        """
        评估套利机会

        Args:
            premium_rate: 溢价率(%)

        Returns:
            str: 套利评估
        """
        abs_rate = abs(premium_rate)

        if abs_rate > 20:
            return "高度套利机会"
        elif abs_rate > 10:
            return "中等套利机会"
        elif abs_rate > 5:
            return "低套利机会"
        else:
            return "无明显套利机会"
