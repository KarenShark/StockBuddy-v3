/**
 * HK Stock Trading API Client
 * 
 * Provides functions to interact with HK Stock Trading endpoints
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ApiResponse, apiClient } from "@/lib/api-client";

// ============================================
// Types
// ============================================

export interface HKStockPosition {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  lot_size: number;
  lots: number;
}

export interface HKStockTrade {
  trade_id: string;
  symbol: string;
  side: string; // "BUY" | "SELL"
  quantity: number;
  price: number;
  total_value: number;
  fees: number;
  timestamp: string;
  status: string;
}

export interface HKStockPortfolioSummary {
  total_cash: number;
  total_market_value: number;
  total_assets: number;
  total_pnl: number;
  total_pnl_pct: number;
  position_count: number;
}

export interface HKPortfolioValuePoint {
  timestamp: string;
  total_value: number;
  cash: number;
  positions_value: number;
}

export interface ExecuteTradeRequest {
  symbol: string;
  side: "BUY" | "SELL";
  lots: number;
}

// ============================================
// API Requests
// ============================================

/**
 * Get HK stock positions
 */
export async function getHKStockPositions(): Promise<HKStockPosition[]> {
  const response = await apiClient.get<ApiResponse<HKStockPosition[]>>(
    "/hk-stock/positions"
  );
  return response.data || [];
}

/**
 * Get HK stock trade history
 */
export async function getHKStockTrades(): Promise<HKStockTrade[]> {
  const response = await apiClient.get<ApiResponse<HKStockTrade[]>>(
    "/hk-stock/trades"
  );
  return response.data || [];
}

/**
 * Get HK stock portfolio summary
 */
export async function getHKPortfolioSummary(): Promise<HKStockPortfolioSummary | null> {
  const response = await apiClient.get<ApiResponse<HKStockPortfolioSummary>>(
    "/hk-stock/portfolio"
  );
  return response.data || null;
}

/**
 * Get HK portfolio value history
 */
export async function getHKPortfolioValueHistory(): Promise<HKPortfolioValuePoint[]> {
  const response = await apiClient.get<ApiResponse<HKPortfolioValuePoint[]>>(
    "/hk-stock/portfolio/history"
  );
  return response.data || [];
}

/**
 * Execute a trade (buy or sell)
 */
export async function executeTrade(request: ExecuteTradeRequest): Promise<HKStockTrade> {
  const response = await apiClient.post<ApiResponse<HKStockTrade>>(
    "/hk-stock/trade",
    request
  );
  return response.data!;
}

// ============================================
// React Query Hooks
// ============================================

export const HK_STOCK_QUERY_KEYS = {
  positions: ["hk-stock", "positions"] as const,
  trades: ["hk-stock", "trades"] as const,
  portfolio: ["hk-stock", "portfolio"] as const,
  portfolioHistory: ["hk-stock", "portfolio", "history"] as const,
};

/**
 * Hook to get HK stock positions
 */
export function useGetHKStockPositions() {
  return useQuery({
    queryKey: HK_STOCK_QUERY_KEYS.positions,
    queryFn: getHKStockPositions,
    refetchInterval: 3000, // Refetch every 3 seconds
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
  });
}

/**
 * Hook to get HK stock trade history
 */
export function useGetHKStockTrades() {
  return useQuery({
    queryKey: HK_STOCK_QUERY_KEYS.trades,
    queryFn: getHKStockTrades,
    refetchInterval: 2000, // Refetch every 2 seconds for near real-time updates
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
  });
}

/**
 * Hook to get HK portfolio summary
 */
export function useGetHKPortfolioSummary() {
  return useQuery({
    queryKey: HK_STOCK_QUERY_KEYS.portfolio,
    queryFn: getHKPortfolioSummary,
    refetchInterval: 3000, // Refetch every 3 seconds
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
  });
}

/**
 * Hook to get HK portfolio value history
 */
export function useGetHKPortfolioValueHistory() {
  return useQuery({
    queryKey: HK_STOCK_QUERY_KEYS.portfolioHistory,
    queryFn: getHKPortfolioValueHistory,
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
  });
}

/**
 * Hook to execute a trade
 */
export function useExecuteTrade() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: executeTrade,
    onSuccess: () => {
      // Invalidate and refetch relevant queries
      queryClient.invalidateQueries({ queryKey: HK_STOCK_QUERY_KEYS.positions });
      queryClient.invalidateQueries({ queryKey: HK_STOCK_QUERY_KEYS.trades });
      queryClient.invalidateQueries({ queryKey: HK_STOCK_QUERY_KEYS.portfolio });
      queryClient.invalidateQueries({ queryKey: HK_STOCK_QUERY_KEYS.portfolioHistory });
    },
  });
}

