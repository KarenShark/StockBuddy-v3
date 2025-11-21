"""
港股通资金监控适配器

提供港股通（南下资金）和沪深股通（北上资金）的流向数据

数据来源: AKShare - 东方财富网
"""

from typing import Dict, List, Optional

import akshare as ak
import pandas as pd
from loguru import logger


class HKConnectAdapter:
    """
    港股通资金流向数据适配器

    使用AKShare获取港股通和沪深股通的资金流向数据。
    支持南下资金（内地投资者买入港股）和北上资金（港股投资者买入A股）的查询。

    🔧 修复说明: 使用正确的AKShare API
    - stock_hsgt_hist_em: 历史数据（按symbol: "北向资金", "南向资金", "沪股通", "深股通", "港股通沪", "港股通深"）
    - stock_hsgt_fund_flow_summary_em: 实时汇总数据

    由于历史数据API存在网络稳定性问题，优先使用汇总API + 历史趋势估算。
    """

    def __init__(self):
        """初始化适配器"""
        self.logger = logger

    @staticmethod
    def _safe_float(value) -> float:
        """安全转换为float，处理NaN（NaN不是有效的JSON）"""
        try:
            result = float(value)
            return 0.0 if pd.isna(result) else result
        except (ValueError, TypeError):
            return 0.0

    def _empty_flow_result(self) -> Dict:
        """返回空结果"""
        return {
            "total_inflow": 0.0,
            "daily_data": [],
            "trend": "unknown",
            "latest_date": None,
            "data_points": 0,
            "unit": "亿元",
            "status": "no_data",
        }

    def _analyze_trend(self, values: List[float]) -> str:
        """分析趋势"""
        if not values or len(values) < 2:
            return "unknown"

        # 简单线性趋势判断
        first_half = sum(values[: len(values) // 2])
        second_half = sum(values[len(values) // 2 :])

        if second_half > first_half * 1.1:
            return "increasing"
        elif second_half < first_half * 0.9:
            return "decreasing"
        else:
            return "stable"

    def get_southbound_flow(self, days: int = 30) -> Dict:
        """
        获取南下资金流向数据 (A股投资者买入港股)

        Args:
            days: 查询天数，默认30天

        Returns:
            Dict包含:
            - total_inflow: 总净流入（正数为净买入，负数为净卖出）
            - daily_data: 每日数据列表
            - trend: 趋势分析 ("increasing", "decreasing", "stable")
            - latest_date: 最新数据日期

        Example:
            >>> adapter = HKConnectAdapter()
            >>> flow = adapter.get_southbound_flow(days=7)
            >>> print(f"7日净流入: {flow['total_inflow']}亿元")
        """
        try:
            # 🎯 策略：使用历史数据API（更可靠）
            # symbol可选: "南向资金", "港股通沪", "港股通深"

            # 尝试获取南向资金历史数据
            df = ak.stock_hsgt_hist_em(symbol="南向资金")

            if df is None or df.empty:
                logger.warning("南下资金历史数据为空，尝试备用方案")
                # 备用方案：使用当日汇总数据
                return self._get_southbound_from_summary()

            # 处理历史数据
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values(by="日期", ascending=False)

            # 获取最近N天数据
            recent_df = df.head(days)

            # 计算总净流入（使用"当日成交净买额"字段）
            total_inflow = self._safe_float(recent_df["当日成交净买额"].sum())

            # 构建每日数据
            daily_data = []
            for _, row in recent_df.iterrows():
                net_flow = self._safe_float(row["当日成交净买额"])
                daily_data.append(
                    {
                        "date": row["日期"].strftime("%Y-%m-%d"),
                        "net_flow": round(net_flow, 2),
                        "flow_direction": "流入" if net_flow > 0 else "流出",
                    }
                )

            # 分析趋势
            trend = self._analyze_trend(recent_df["当日成交净买额"].tolist())

            result = {
                "total_inflow": round(total_inflow, 2),
                "daily_data": daily_data,
                "trend": trend,
                "latest_date": recent_df.iloc[0]["日期"].strftime("%Y-%m-%d"),
                "data_points": len(daily_data),
                "unit": "亿元",
                "status": "success",
            }

            logger.info(
                f"成功获取{days}天南下资金数据，总净流入: {total_inflow:.2f}亿元"
            )
            return result

        except Exception as e:
            logger.error(f"获取南下资金历史数据失败: {e}", exc_info=True)
            logger.info("回退到汇总数据方案")
            return self._get_southbound_from_summary()

    def _get_southbound_from_summary(self) -> Dict:
        """从汇总数据获取南下资金（备用方案）"""
        try:
            df = ak.stock_hsgt_fund_flow_summary_em()

            if df is None or df.empty:
                return self._empty_flow_result()

            # 筛选南向资金
            south_df = df[df["资金方向"] == "南向"]

            if south_df.empty:
                return self._empty_flow_result()

            # 计算总净买额（沪+深）
            total = self._safe_float(south_df["成交净买额"].sum())
            latest_date = south_df.iloc[0]["交易日"]

            result = {
                "total_inflow": round(total, 2),
                "daily_data": [
                    {
                        "date": latest_date,
                        "net_flow": round(total, 2),
                        "flow_direction": "流入" if total > 0 else "流出",
                    }
                ],
                "trend": "stable",
                "latest_date": latest_date,
                "data_points": 1,
                "unit": "亿元",
                "status": "summary_only",
                "note": "仅当日汇总数据，历史数据暂时不可用",
            }

            logger.info(f"从汇总数据获取南下资金: {total:.2f}亿元（当日）")
            return result

        except Exception as e:
            logger.error(f"获取汇总数据也失败: {e}", exc_info=True)
            return self._empty_flow_result()

    def get_northbound_flow(self, days: int = 30) -> Dict:
        """
        获取北上资金流向数据 (港股投资者买入A股)

        Args:
            days: 查询天数，默认30天

        Returns:
            Dict包含北上资金数据（结构同get_southbound_flow）
        """
        try:
            # 使用北向资金历史数据
            df = ak.stock_hsgt_hist_em(symbol="北向资金")

            if df is None or df.empty:
                logger.warning("北上资金历史数据为空，尝试备用方案")
                return self._get_northbound_from_summary()

            # 处理历史数据
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values(by="日期", ascending=False)

            # 获取最近N天数据
            recent_df = df.head(days)

            # 计算总净流入
            total_inflow = self._safe_float(recent_df["当日成交净买额"].sum())

            # 构建每日数据
            daily_data = []
            for _, row in recent_df.iterrows():
                net_flow = self._safe_float(row["当日成交净买额"])
                daily_data.append(
                    {
                        "date": row["日期"].strftime("%Y-%m-%d"),
                        "net_flow": round(net_flow, 2),
                        "flow_direction": "流入" if net_flow > 0 else "流出",
                    }
                )

            trend = self._analyze_trend(recent_df["当日成交净买额"].tolist())

            result = {
                "total_inflow": round(total_inflow, 2),
                "daily_data": daily_data,
                "trend": trend,
                "latest_date": recent_df.iloc[0]["日期"].strftime("%Y-%m-%d"),
                "data_points": len(daily_data),
                "unit": "亿元",
                "status": "success",
            }

            logger.info(
                f"成功获取{days}天北上资金数据，总净流入: {total_inflow:.2f}亿元"
            )
            return result

        except Exception as e:
            logger.error(f"获取北上资金历史数据失败: {e}", exc_info=True)
            return self._get_northbound_from_summary()

    def _get_northbound_from_summary(self) -> Dict:
        """从汇总数据获取北上资金（备用方案）"""
        try:
            df = ak.stock_hsgt_fund_flow_summary_em()

            if df is None or df.empty:
                return self._empty_flow_result()

            # 筛选北向资金
            north_df = df[df["资金方向"] == "北向"]

            if north_df.empty:
                return self._empty_flow_result()

            # 计算总净买额（沪股通+深股通）
            total = self._safe_float(north_df["成交净买额"].sum())
            latest_date = north_df.iloc[0]["交易日"]

            result = {
                "total_inflow": round(total, 2),
                "daily_data": [
                    {
                        "date": latest_date,
                        "net_flow": round(total, 2),
                        "flow_direction": "流入" if total > 0 else "流出",
                    }
                ],
                "trend": "stable",
                "latest_date": latest_date,
                "data_points": 1,
                "unit": "亿元",
                "status": "summary_only",
                "note": "仅当日汇总数据，历史数据暂时不可用",
            }

            logger.info(f"从汇总数据获取北上资金: {total:.2f}亿元（当日）")
            return result

        except Exception as e:
            logger.error(f"获取汇总数据也失败: {e}", exc_info=True)
            return self._empty_flow_result()

    def get_top_southbound_holdings(self, limit: int = 10) -> List[Dict]:
        """
        获取南下资金重仓股 (被南下资金买入最多的港股)

        Args:
            limit: 返回数量，默认10只

        Returns:
            List[Dict] 包含股票代码、名称、持仓市值等信息

        Example:
            >>> adapter = HKConnectAdapter()
            >>> top_stocks = adapter.get_top_southbound_holdings(limit=5)
            >>> for stock in top_stocks:
            ...     print(f"{stock['name']}: {stock['holding_value']}亿")
        """
        try:
            # 🔧 使用正确的API获取持仓数据
            # stock_hsgt_hold_stock_em: 持仓个股统计
            df = ak.stock_hsgt_hold_stock_em(market="北向", indicator="持股市值")

            if df is None or df.empty:
                logger.warning("南下资金持仓数据为空")
                return []

            # 按持股市值排序
            df = df.sort_values(by="持股市值", ascending=False)

            # 取前N名
            top_df = df.head(limit)

            holdings = []
            for _, row in top_df.iterrows():
                holdings.append(
                    {
                        "ticker": row["代码"],
                        "name": row["名称"],
                        "holding_value": round(float(row["持股市值"]), 2),
                        "holding_pct": round(float(row["持股占流通股比"]), 2)
                        if "持股占流通股比" in row
                        else None,
                        "unit": "亿元",
                    }
                )

            logger.info(f"成功获取{len(holdings)}只南下资金重仓股")
            return holdings

        except Exception as e:
            logger.error(f"获取南下资金重仓股失败: {e}", exc_info=True)
            return []

    def get_flow_summary(self, days: int = 30) -> Optional[Dict]:
        """
        获取南北向资金流向汇总

        Args:
            days: 查询天数

        Returns:
            Dict包含南下、北上资金汇总和分析
        """
        try:
            southbound = self.get_southbound_flow(days)
            northbound = self.get_northbound_flow(days)

            # 计算净额（北上-南下 = 资金净流向）
            net_balance = northbound["total_inflow"] - southbound["total_inflow"]

            # 分析
            analysis_parts = []
            if southbound["total_inflow"] > 0:
                analysis_parts.append(f"南下资金净流入{southbound['total_inflow']}亿元")
            else:
                analysis_parts.append(
                    f"南下资金净流出{abs(southbound['total_inflow'])}亿元"
                )

            if northbound["total_inflow"] > 0:
                analysis_parts.append(f"北上资金净流入{northbound['total_inflow']}亿元")
            else:
                analysis_parts.append(
                    f"北上资金净流出{abs(northbound['total_inflow'])}亿元"
                )

            return {
                "period_days": days,
                "southbound": southbound,
                "northbound": northbound,
                "net_balance": round(net_balance, 2),
                "analysis": "；".join(analysis_parts),
                "unit": "亿元",
            }

        except Exception as e:
            logger.error(f"获取资金流向汇总失败: {e}", exc_info=True)
            return None
