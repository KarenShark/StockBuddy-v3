import {
  AswathDamodaranPng,
  BenGrahamPng,
  BillAckmanPng,
  CathieWoodPng,
  CharlieMungerPng,
  EmotionalAgencyPng,
  FundamentalProxyPng,
  MichaelBurryPng,
  MohnishPabraiPng,
  NewPushAgentPng,
  PeterLynchPng,
  PhilFisherPng,
  PortfolioManagerPng,
  RakeshJhunjhunwalaPng,
  ResearchAgentPng,
  SecAgentPng,
  StanleyDruckenmillerPng,
  StrategyAgentPng,
  TechnicalAgencyPng,
  ValuationAgencyPng,
  WarrenBuffettPng,
} from "@/assets/png";
import { SuperAgent } from "@/assets/svg";
import {
  ChatConversationRenderer,
  ExecutionPlanRenderer,
  MarkdownRenderer,
  ReasoningRenderer,
  ReportRenderer,
  ScheduledTaskControllerRenderer,
  ScheduledTaskRenderer,
  ToolCallRenderer,
} from "@/components/shared/renderer";
import { TimeUtils } from "@/lib/time";
import type { AgentComponentType, AgentInfo } from "@/types/agent";
import type { RendererComponent } from "@/types/renderer";

// component_type to section type
export const AGENT_SECTION_COMPONENT_TYPE = ["scheduled_task_result"] as const;

// multi section component type
export const AGENT_MULTI_SECTION_COMPONENT_TYPE = ["report"] as const;

// agent component type
export const AGENT_COMPONENT_TYPE = [
  "markdown",
  "reasoning",
  "tool_call",
  "subagent_conversation",
  "scheduled_task_controller",
  "execution_plan",
  ...AGENT_SECTION_COMPONENT_TYPE,
  ...AGENT_MULTI_SECTION_COMPONENT_TYPE,
] as const;

/**
 * Component renderer mapping with automatic type inference
 */
export const COMPONENT_RENDERER_MAP: {
  [K in AgentComponentType]: RendererComponent<K>;
} = {
  scheduled_task_result: ScheduledTaskRenderer,
  scheduled_task_controller: ScheduledTaskControllerRenderer,
  report: ReportRenderer,
  markdown: MarkdownRenderer,
  reasoning: ReasoningRenderer,
  tool_call: ToolCallRenderer,
  subagent_conversation: ChatConversationRenderer,
  execution_plan: ExecutionPlanRenderer,
};

export const AGENT_AVATAR_MAP: Record<string, string> = {
  // Investment Masters
  ResearchAgent: ResearchAgentPng,
  StrategyAgent: StrategyAgentPng,
  AswathDamodaranAgent: AswathDamodaranPng,
  BenGrahamAgent: BenGrahamPng,
  BillAckmanAgent: BillAckmanPng,
  CathieWoodAgent: CathieWoodPng,
  CharlieMungerAgent: CharlieMungerPng,
  MichaelBurryAgent: MichaelBurryPng,
  MohnishPabraiAgent: MohnishPabraiPng,
  PeterLynchAgent: PeterLynchPng,
  PhilFisherAgent: PhilFisherPng,
  RakeshJhunjhunwalaAgent: RakeshJhunjhunwalaPng,
  StanleyDruckenmillerAgent: StanleyDruckenmillerPng,
  WarrenBuffettAgent: WarrenBuffettPng,
  SuperAgent: SuperAgent,

  // Analyst Agents
  FundamentalsAnalystAgent: FundamentalProxyPng,
  TechnicalAnalystAgent: TechnicalAgencyPng,
  ValuationAnalystAgent: ValuationAgencyPng,
  SentimentAnalystAgent: EmotionalAgencyPng,

  // System Agents
  TradingAgents: PortfolioManagerPng,
  SECAgent: SecAgentPng,
  NewsAgent: NewPushAgentPng,
};

export const STOCKBUDDY_AGENT: AgentInfo = {
  agent_name: "SuperAgent",
  display_name: "StockBuddy Agent",
  enabled: true,
  description:
    "StockBuddy Agent is a super-agent that can help you manage different agents and tasks for Hong Kong stock market",
  created_at: TimeUtils.nowUTC().toISOString(),
  updated_at: TimeUtils.nowUTC().toISOString(),
  agent_metadata: {
    version: "1.0.0",
    author: "StockBuddy HK Team",
    tags: ["stockbuddy", "super-agent", "hk-stocks"],
  },
};

export const MODEL_PROVIDERS = ["openrouter", "siliconflow"] as const;
export const MODEL_PROVIDER_MAP: Record<
  (typeof MODEL_PROVIDERS)[number],
  string[]
> = {
  openrouter: [
    "deepseek/deepseek-v3.1-terminus",
    "deepseek/deepseek-v3.2-exp",
    "qwen/qwen3-max",
    "openai/gpt-5-pro",
    "openai/gpt-5",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-haiku-4.5",
  ],
  siliconflow: ["deepseek-ai/DeepSeek-V3.2-Exp", "Qwen/Qwen3-235B-A22B"],
};

// Trading symbols options
export const TRADING_SYMBOLS: string[] = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "DOGE/USDT",
  "XRP/USDT",
];
