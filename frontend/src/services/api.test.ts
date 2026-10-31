import { ApiError } from "../types/ApiError";
import type { VoiceDebug } from "../types/VoiceDebug";
import { request } from "./api";

const originalFetch = globalThis.fetch;
const fetchMock = jest.fn();

describe("request", () => {
  beforeEach(() => {
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    fetchMock.mockReset();
  });

  afterAll(() => {
    globalThis.fetch = originalFetch;
  });

  it("throws ApiError with the backend code and message", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        error: { code: "NOT_UNDERSTOOD", message: "Não entendi o gasto." },
      }),
    });

    const error = await request("/api/financial-records").catch((value: unknown) => value);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "NOT_UNDERSTOOD",
      message: "Não entendi o gasto.",
      status: 422,
    });
  });

  it("throws ApiError with a fallback message when the body is not JSON", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("Invalid JSON");
      },
    });

    const error = await request("/api/financial-records").catch((value: unknown) => value);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "UNKNOWN_ERROR",
      message: "Não foi possível concluir a solicitação.",
      status: 500,
    });
  });

  it("exposes debug data from error responses", async () => {
    const debug = { version: 1, outcome: "rejected" } as unknown as VoiceDebug;
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        error: { code: "NOT_FINANCIAL", message: "Isso não parece um gasto." },
        debug,
      }),
    });

    const error = await request("/api/voice-records").catch((value: unknown) => value);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ debug });
  });
});
