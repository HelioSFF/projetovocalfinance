import type { DebugStage } from "../types/VoiceDebug";
import { formatMs, formatUsd, stageBarStyle } from "./formatDebug";

const stage: DebugStage = {
  name: "transcribe",
  label: "Transcrição",
  attempt: null,
  started_ms: 500,
  duration_ms: 250,
  parallel: false,
};

describe("formatMs", () => {
  it("formats milliseconds and seconds", () => {
    expect(formatMs(745)).toBe("745 ms");
    expect(formatMs(1000)).toBe("1,00 s");
    expect(formatMs(2412)).toBe("2,41 s");
  });
});

describe("formatUsd", () => {
  it("formats USD values and null", () => {
    expect(formatUsd("0.0005126")).toBe("US$ 0,0005126");
    expect(formatUsd(null)).toBe("—");
  });
});

describe("stageBarStyle", () => {
  it("returns proportional left and width percentages", () => {
    expect(stageBarStyle(stage, 1000)).toEqual({ left: 50, width: 25 });
  });

  it("keeps a minimum width and handles zero totals", () => {
    expect(stageBarStyle({ ...stage, duration_ms: 1 }, 1000).width).toBe(1);
    expect(stageBarStyle(stage, 0)).toEqual({ left: 0, width: 1 });
  });
});
