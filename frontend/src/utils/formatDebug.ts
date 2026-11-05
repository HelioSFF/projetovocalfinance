import type { DebugStage } from "../types/VoiceDebug";

export function formatMs(ms: number): string {
  if (ms < 1000) {
    return `${ms} ms`;
  }

  return `${(ms / 1000).toFixed(2).replace(".", ",")} s`;
}

export function formatUsd(value: string | null): string {
  if (value === null) {
    return "—";
  }

  return `US$ ${value.replace(".", ",")}`;
}

export function stageBarStyle(
  stage: DebugStage,
  totalMs: number,
): { left: number; width: number } {
  if (totalMs <= 0) {
    return { left: 0, width: 1 };
  }

  const left = Math.min((stage.started_ms / totalMs) * 100, 99);
  const width = Math.max((stage.duration_ms / totalMs) * 100, 1);

  return { left, width };
}
