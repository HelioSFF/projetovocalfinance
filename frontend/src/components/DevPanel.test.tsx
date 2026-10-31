import { fireEvent, render, screen } from "@testing-library/react-native";
import type { VoiceDebug } from "../types/VoiceDebug";
import DevPanel from "./DevPanel";

const debugFixture: VoiceDebug = {
  version: 1,
  app_env: "development",
  outcome: "accepted",
  failure_code: null,
  threshold: 0.6,
  timing: {
    server_total_ms: 2412,
    stages: [
      {
        name: "validate",
        label: "Validação do áudio",
        attempt: null,
        started_ms: 0,
        duration_ms: 3,
        parallel: false,
      },
      {
        name: "transcribe",
        label: "Transcrição",
        attempt: null,
        started_ms: 3,
        duration_ms: 745,
        parallel: false,
      },
      {
        name: "analyze",
        label: "Análise (paralela)",
        attempt: 1,
        started_ms: 748,
        duration_ms: 1441,
        parallel: false,
      },
      {
        name: "decision",
        label: "Decisions",
        attempt: 1,
        started_ms: 748,
        duration_ms: 249,
        parallel: true,
      },
      {
        name: "extraction",
        label: "Extração",
        attempt: 1,
        started_ms: 748,
        duration_ms: 1441,
        parallel: true,
      },
      {
        name: "rules",
        label: "Cálculo e reconciliação",
        attempt: null,
        started_ms: 2189,
        duration_ms: 1,
        parallel: false,
      },
      {
        name: "db_insert",
        label: "Gravação no banco",
        attempt: null,
        started_ms: 2190,
        duration_ms: 18,
        parallel: false,
      },
    ],
  },
  transcription: {
    model: "gpt-transcribe",
    text: "Comprei três cafés de cinco reais.",
    audio_seconds: 4,
    audio_seconds_source: "provider",
    usage: { type: "duration", seconds: 4 },
  },
  attempts: [
    {
      number: 1,
      source: "transcript",
      input_text: "Comprei três cafés de cinco reais.",
      decision: {
        model: "gpt-6-luna",
        answers: [
          {
            name: "plausible",
            type: "predicate",
            probability: 0.97,
            choice: null,
            confidence: null,
            top_probabilities: [],
            refusal: null,
          },
          {
            name: "is_financial",
            type: "predicate",
            probability: 0.95,
            choice: null,
            confidence: null,
            top_probabilities: [],
            refusal: null,
          },
          {
            name: "type",
            type: "choice",
            probability: null,
            choice: "expense",
            confidence: 0.99,
            top_probabilities: [
              { value: "expense", probability: 0.99 },
              { value: "income", probability: 0.01 },
            ],
            refusal: null,
          },
          {
            name: "category",
            type: "choice",
            probability: null,
            choice: "food",
            confidence: 0.91,
            top_probabilities: [
              { value: "food", probability: 0.91 },
              { value: "groceries", probability: 0.06 },
              { value: "leisure", probability: 0.01 },
            ],
            refusal: null,
          },
        ],
        usage: {
          input_tokens: 1725,
          cached_tokens: 0,
          cache_write_tokens: 0,
          output_tokens: 0,
        },
      },
      extraction: {
        model: "gpt-6-luna",
        service_tier: null,
        raw_text: '{"item":"café","quantity":3,"unit_price":5,"stated_total":null}',
        parsed: { item: "café", quantity: 3, unit_price: 5, stated_total: null },
        usage: {
          input_tokens: 251,
          cached_tokens: 0,
          output_tokens: 30,
          reasoning_tokens: 0,
        },
      },
      acceptance: {
        plausible: { value: 0.97, passed: true },
        is_financial: { value: 0.95, passed: true },
        extraction_valid: true,
        accepted: true,
        failure_code: null,
      },
    },
  ],
  fallback: {
    used: false,
    model: null,
    input_text: null,
    rewritten_text: null,
    usage: null,
  },
  costs: {
    currency: "USD",
    lines: [
      {
        stage: "transcribe",
        attempt: null,
        model: "gpt-transcribe",
        basis: "4.0 s × 0.0045/min",
        usd: "0.0003000",
        estimated: false,
      },
      {
        stage: "decision",
        attempt: 1,
        model: "gpt-6-luna",
        basis: "1725 in, 0 cached, 0 write",
        usd: "0.0001725",
        estimated: false,
      },
      {
        stage: "extraction",
        attempt: 1,
        model: "gpt-6-luna",
        basis: "251 in, 0 cached, 30 out",
        usd: "0.0000401",
        estimated: false,
      },
    ],
    total_usd: "0.0005126",
    estimated: false,
  },
  result: {
    type_choice: "expense",
    category_choice: "food",
    type: "expense",
    category: "food",
    reconciled: false,
    quantity: "3",
    unit_price: "5.00",
    total: "15.00",
    total_source: "unit_price",
    formula: "3 × 5.00 = 15.00",
  },
};

describe("DevPanel", () => {
  it("shows the collapsed summary", async () => {
    await render(<DevPanel debug={debugFixture} clientTotalMs={3000} />);

    expect(screen.getByText("Dev tools · 2,41 s · US$ 0,0005126")).toBeTruthy();
    expect(screen.queryByText("Etapas")).toBeNull();
  });

  it("expands to show the debug sections", async () => {
    await render(<DevPanel debug={debugFixture} clientTotalMs={3000} />);

    await fireEvent.press(screen.getByRole("button"));

    expect(screen.getByText("Etapas")).toBeTruthy();
    expect(screen.getByText("Servidor: 2,41 s")).toBeTruthy();
    expect(screen.getByText("Rede + upload ≈ 588 ms")).toBeTruthy();
    expect(screen.getByText("Total da mensagem: US$ 0,0005126")).toBeTruthy();
    expect(screen.getByText('"Comprei três cafés de cinco reais."')).toBeTruthy();
    expect(screen.getByText("plausible")).toBeTruthy();
    expect(screen.getByText(/unit_price/)).toBeTruthy();
    expect(screen.getByText("Fallback DeepSeek: não usado")).toBeTruthy();
    expect(screen.getByText("Limiar: 0.6")).toBeTruthy();
    expect(screen.getByText("3 × 5.00 = 15.00")).toBeTruthy();
  }, 15000);

  it("shows a message when there is no debug payload", async () => {
    await render(<DevPanel debug={null} clientTotalMs={null} />);

    expect(screen.getByText("Dev tools")).toBeTruthy();

    await fireEvent.press(screen.getByRole("button"));

    expect(
      screen.getByText("Sem dados de debug: o backend não está em development."),
    ).toBeTruthy();
  });

  it("shows a refusal with the rewritten fallback text", async () => {
    const rejectedDebug: VoiceDebug = {
      ...debugFixture,
      outcome: "rejected",
      failure_code: "NOT_FINANCIAL",
      result: null,
      fallback: {
        used: true,
        model: "deepseek-flash",
        input_text: "bom dia",
        rewritten_text: "Bom dia, tudo bem?",
        usage: null,
      },
    };
    await render(<DevPanel debug={rejectedDebug} clientTotalMs={null} />);

    await fireEvent.press(screen.getByRole("button"));

    expect(screen.getByText("Nada gravado (NOT_FINANCIAL)")).toBeTruthy();
    expect(
      screen.getByText('Fallback DeepSeek: usado → "Bom dia, tudo bem?"'),
    ).toBeTruthy();
  });

  it("marks estimated costs", async () => {
    const estimatedDebug: VoiceDebug = {
      ...debugFixture,
      costs: {
        ...debugFixture.costs,
        lines: debugFixture.costs.lines.map((line, index) =>
          index === 0 ? { ...line, estimated: true } : line,
        ),
        estimated: true,
      },
    };
    await render(<DevPanel debug={estimatedDebug} clientTotalMs={null} />);

    await fireEvent.press(screen.getByRole("button"));

    expect(screen.getByText("* estimativa")).toBeTruthy();
  });
});
