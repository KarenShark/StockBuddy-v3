/**
 * HK Stock Strategy API Client
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

// ============================================
// Types
// ============================================

export interface CreateHKStockStrategyRequest {
  strategy_name: string;
  symbols: string[];
  initial_capital: number;
  max_position_size?: number;
  max_positions?: number;
  strategy_prompt: string;
  rebalance_interval?: number;
}

export interface HKStockStrategyInfo {
  strategy_id: string;
  strategy_name: string;
  symbols: string[];
  status: string;
  initial_capital: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  position_count: number;
  trade_count: number;
  created_at: string;
  updated_at: string;
}

export interface HKStockStrategyDetail extends HKStockStrategyInfo {
  strategy_prompt: string;
  max_position_size: number;
  max_positions: number;
  rebalance_interval: number;
  last_rebalance: string | null;
}

export interface HKStrategyPosition {
  symbol: string;
  quantity: number;
  lots: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface HKStrategyTrade {
  trade_id: string;
  symbol: string;
  side: string;
  quantity: number;
  lots: number;
  price: number;
  total_value: number;
  fees: number;
  timestamp: string;
  reason: string | null;
}

export interface HKStrategyPerformancePoint {
  timestamp: string;
  portfolio_value: number;
  cash: number;
  positions_value: number;
  pnl: number;
  pnl_pct: number;
}

export interface HKStrategyAIRecommendation {
  symbol: string;
  action: string; // BUY, SELL, HOLD
  lots: number;
  reason: string;
  confidence: number; // 0-1
  target_price: number | null;
  executed: boolean | null;
  trade_id: string | null;
}

export interface HKStrategyAIDecision {
  timestamp: string;
  portfolio_value: number;
  cash: number;
  position_count: number;
  recommendation_count: number;
  recommendations: HKStrategyAIRecommendation[];
}

interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

// ============================================
// API Query Keys
// ============================================

export const HK_STRATEGY_KEYS = {
  all: ["hk-stock-strategies"] as const,
  lists: () => [...HK_STRATEGY_KEYS.all, "list"] as const,
  list: (filters: string) => [...HK_STRATEGY_KEYS.lists(), { filters }] as const,
  details: () => [...HK_STRATEGY_KEYS.all, "detail"] as const,
  detail: (id: string) => [...HK_STRATEGY_KEYS.details(), id] as const,
  positions: (id: string) => [...HK_STRATEGY_KEYS.detail(id), "positions"] as const,
  trades: (id: string) => [...HK_STRATEGY_KEYS.detail(id), "trades"] as const,
  performance: (id: string) => [...HK_STRATEGY_KEYS.detail(id), "performance"] as const,
  aiDecisions: (id: string) => [...HK_STRATEGY_KEYS.detail(id), "ai-decisions"] as const,
};

// ============================================
// API Functions
// ============================================

async function fetchHKStrategies(status?: string): Promise<HKStockStrategyInfo[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);

  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies?${params}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch HK strategies: ${response.statusText}`);
  }

  const result: ApiResponse<HKStockStrategyInfo[]> = await response.json();
  return result.data;
}

async function fetchHKStrategyDetail(strategyId: string): Promise<HKStockStrategyDetail> {
  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies/${strategyId}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch strategy detail: ${response.statusText}`);
  }

  const result: ApiResponse<HKStockStrategyDetail> = await response.json();
  return result.data;
}

async function fetchHKStrategyPositions(strategyId: string): Promise<HKStrategyPosition[]> {
  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies/${strategyId}/positions`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch strategy positions: ${response.statusText}`);
  }

  const result: ApiResponse<HKStrategyPosition[]> = await response.json();
  return result.data;
}

async function fetchHKStrategyTrades(strategyId: string, limit = 100): Promise<HKStrategyTrade[]> {
  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies/${strategyId}/trades?limit=${limit}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch strategy trades: ${response.statusText}`);
  }

  const result: ApiResponse<HKStrategyTrade[]> = await response.json();
  return result.data;
}

async function fetchHKStrategyPerformance(
  strategyId: string,
  limit = 1000
): Promise<HKStrategyPerformancePoint[]> {
  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies/${strategyId}/performance?limit=${limit}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch strategy performance: ${response.statusText}`);
  }

  const result: ApiResponse<HKStrategyPerformancePoint[]> = await response.json();
  return result.data;
}

async function fetchHKStrategyAIDecisions(
  strategyId: string,
  limit = 50
): Promise<HKStrategyAIDecision[]> {
  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies/${strategyId}/ai-decisions?limit=${limit}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch AI decisions: ${response.statusText}`);
  }

  const result: ApiResponse<HKStrategyAIDecision[]> = await response.json();
  return result.data;
}

async function createHKStrategy(
  request: CreateHKStockStrategyRequest
): Promise<HKStockStrategyDetail> {
  const response = await fetch(`${API_BASE_URL}/hk-stock-strategies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create strategy: ${error}`);
  }

  const result: ApiResponse<HKStockStrategyDetail> = await response.json();
  return result.data;
}

async function updateHKStrategy(
  strategyId: string,
  updates: { status?: string; max_position_size?: number; max_positions?: number }
): Promise<HKStockStrategyDetail> {
  const response = await fetch(
    `${API_BASE_URL}/hk-stock-strategies/${strategyId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to update strategy: ${response.statusText}`);
  }

  const result: ApiResponse<HKStockStrategyDetail> = await response.json();
  return result.data;
}

// ============================================
// React Query Hooks
// ============================================

/**
 * Hook to fetch list of HK stock strategies
 */
export function useHKStrategies(status?: string) {
  return useQuery({
    queryKey: HK_STRATEGY_KEYS.list(status || "all"),
    queryFn: () => fetchHKStrategies(status),
  });
}

/**
 * Hook to fetch HK strategy detail
 */
export function useHKStrategyDetail(strategyId: string | undefined) {
  return useQuery({
    queryKey: HK_STRATEGY_KEYS.detail(strategyId || ""),
    queryFn: () => fetchHKStrategyDetail(strategyId!),
    enabled: !!strategyId,
  });
}

/**
 * Hook to fetch HK strategy positions
 */
export function useHKStrategyPositions(strategyId: string | undefined) {
  return useQuery({
    queryKey: HK_STRATEGY_KEYS.positions(strategyId || ""),
    queryFn: () => fetchHKStrategyPositions(strategyId!),
    enabled: !!strategyId,
    refetchInterval: 3000, // Auto-refresh every 3 seconds
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
  });
}

/**
 * Hook to fetch HK strategy trades
 */
export function useHKStrategyTrades(strategyId: string | undefined, limit = 100) {
  return useQuery({
    queryKey: HK_STRATEGY_KEYS.trades(strategyId || ""),
    queryFn: () => fetchHKStrategyTrades(strategyId!, limit),
    enabled: !!strategyId,
    refetchInterval: 2000, // Auto-refresh every 2 seconds for near real-time updates
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
  });
}

/**
 * Hook to fetch HK strategy performance
 */
export function useHKStrategyPerformance(strategyId: string | undefined) {
  return useQuery({
    queryKey: HK_STRATEGY_KEYS.performance(strategyId || ""),
    queryFn: () => fetchHKStrategyPerformance(strategyId!),
    enabled: !!strategyId,
    refetchInterval: 3000, // Auto-refresh every 3 seconds
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
  });
}

/**
 * Hook to fetch HK strategy AI decisions
 */
export function useHKStrategyAIDecisions(strategyId: string | undefined, limit = 20) {
  return useQuery({
    queryKey: HK_STRATEGY_KEYS.aiDecisions(strategyId || ""),
    queryFn: () => fetchHKStrategyAIDecisions(strategyId!, limit),
    enabled: !!strategyId,
    refetchInterval: 5000, // Auto-refresh every 5 seconds to get latest AI decisions
    refetchIntervalInBackground: true, // Continue refetching even when tab is not focused
    staleTime: 3000, // Consider data fresh for 3 seconds (performance optimization)
    gcTime: 60000, // Keep unused data in cache for 1 minute
  });
}

/**
 * Hook to create new HK strategy
 */
export function useCreateHKStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createHKStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HK_STRATEGY_KEYS.lists() });
    },
  });
}

/**
 * Hook to update HK strategy
 */
export function useUpdateHKStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ strategyId, updates }: {
      strategyId: string;
      updates: { status?: string; max_position_size?: number; max_positions?: number };
    }) => updateHKStrategy(strategyId, updates),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: HK_STRATEGY_KEYS.lists() });
      queryClient.invalidateQueries({ queryKey: HK_STRATEGY_KEYS.detail(variables.strategyId) });
    },
  });
}

