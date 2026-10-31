export type DebugOutcome = "accepted" | "rejected" | "provider_error" | "db_error";

export type DebugStage = {
  name: string;
  label: string;
  attempt: number | null;
  started_ms: number;
  duration_ms: number;
  parallel: boolean;
  error?: string;
  http_status?: number;
};

export type DebugTiming = {
  server_total_ms: number;
  stages: DebugStage[];
};

export type DebugUsage = {
  type: string;
  seconds: number;
};

export type DebugTranscription = {
  model: string;
  text: string | null;
  audio_seconds: number | null;
  audio_seconds_source: "provider" | "client" | null;
  usage: DebugUsage | null;
};

export type TopProbability = {
  value: string;
  probability: number;
};

export type DecisionAnswer = {
  name: string;
  type: "predicate" | "choice" | "refusal";
  probability: number | null;
  choice: string | null;
  confidence: number | null;
  top_probabilities: TopProbability[];
  refusal: string | null;
};

export type DecisionUsage = {
  input_tokens: number | null;
  cached_tokens: number | null;
  cache_write_tokens: number | null;
  output_tokens: number | null;
};

export type DebugDecision = {
  model: string;
  answers: DecisionAnswer[];
  usage: DecisionUsage | null;
};

export type ExtractionUsage = {
  input_tokens: number | null;
  cached_tokens: number | null;
  output_tokens: number | null;
  reasoning_tokens: number | null;
};

export type DebugExtraction = {
  model: string;
  service_tier: string | null;
  raw_text: string | null;
  parsed: Record<string, unknown> | null;
  usage: ExtractionUsage | null;
};

export type DebugAcceptanceValue = {
  value: number | null;
  passed: boolean;
};

export type DebugAcceptance = {
  plausible: DebugAcceptanceValue;
  is_financial: DebugAcceptanceValue;
  extraction_valid: boolean;
  accepted: boolean;
  failure_code: string | null;
};

export type DebugAttempt = {
  number: number;
  source: string;
  input_text: string;
  decision: DebugDecision;
  extraction: DebugExtraction | null;
  acceptance: DebugAcceptance;
};

export type FallbackUsage = {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  prompt_cache_hit_tokens: number | null;
  prompt_cache_miss_tokens: number | null;
};

export type DebugFallback = {
  used: boolean;
  model: string | null;
  input_text: string | null;
  rewritten_text: string | null;
  usage: FallbackUsage | null;
};

export type CostLine = {
  stage: string;
  attempt: number | null;
  model: string;
  basis: string;
  usd: string | null;
  estimated: boolean;
};

export type DebugCosts = {
  currency: string;
  lines: CostLine[];
  total_usd: string | null;
  estimated: boolean;
};

export type DebugResult = {
  type_choice: string;
  category_choice: string;
  type: string;
  category: string;
  reconciled: boolean;
  quantity: string;
  unit_price: string;
  total: string;
  total_source: "unit_price" | "stated_total";
  formula: string;
};

export type VoiceDebug = {
  version: number;
  app_env: string;
  outcome: DebugOutcome;
  failure_code: string | null;
  threshold: number;
  timing: DebugTiming;
  transcription: DebugTranscription | null;
  attempts: DebugAttempt[];
  fallback: DebugFallback;
  costs: DebugCosts;
  result: DebugResult | null;
};
