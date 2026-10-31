import { Platform } from "react-native";
import type { FinancialRecord, FinancialRecordList } from "../types/FinancialRecord";
import { getRecords, sendVoiceRecord } from "./recordService";

const originalFetch = globalThis.fetch;
const fetchMock = jest.fn();

const savedRecord: FinancialRecord = {
  id: "record-1",
  type: "expense",
  category: "food",
  category_label: "Alimentação",
  item: "café",
  quantity: "3",
  unit_price: "5.00",
  total: "15.00",
  currency: "BRL",
  transcript: "comprei três cafés de cinco reais",
  normalized_text: null,
  created_at: "2026-05-16T12:00:00",
};

describe("recordService", () => {
  beforeEach(() => {
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    fetchMock.mockReset();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  afterAll(() => {
    globalThis.fetch = originalFetch;
  });

  it("requests records with the search, limit and offset", async () => {
    const responseBody: FinancialRecordList = { items: [], limit: 20, offset: 0 };
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => responseBody,
    });

    const result = await getRecords({ q: "café", limit: 20, offset: 0 });
    const requestedUrl = fetchMock.mock.calls[0][0] as string;

    expect(result).toEqual(responseBody);
    expect(requestedUrl).toContain("/api/financial-records?");
    expect(requestedUrl).toContain("q=caf%C3%A9");
    expect(requestedUrl).toContain("limit=20");
    expect(requestedUrl).toContain("offset=0");
  });

  it("sends a web recording as audio.webm", async () => {
    jest.replaceProperty(Platform, "OS", "web");
    const blob = new Blob(["audio"], { type: "audio/webm" });
    const appendSpy = jest.spyOn(FormData.prototype, "append");
    fetchMock
      .mockResolvedValueOnce({ ok: true, blob: async () => blob })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => savedRecord });

    const result = await sendVoiceRecord("blob:http://localhost/audio");

    expect(result).toEqual(savedRecord);
    expect(appendSpy).toHaveBeenCalledWith("file", blob, "audio.webm");
    expect(fetchMock.mock.calls[0][0]).toBe("blob:http://localhost/audio");
    expect(fetchMock.mock.calls[1][0]).toContain("/api/voice-records");
    expect(fetchMock.mock.calls[1][1].headers).toBeUndefined();
  });

  it("sends a native recording as audio.m4a", async () => {
    jest.replaceProperty(Platform, "OS", "ios");
    const appendSpy = jest.spyOn(FormData.prototype, "append");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => savedRecord,
    });

    await sendVoiceRecord("file:///audio.m4a");

    expect(appendSpy).toHaveBeenCalledWith("file", {
      uri: "file:///audio.m4a",
      name: "audio.m4a",
      type: "audio/m4a",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1].headers).toBeUndefined();
  });

  it("sends the recording duration when provided", async () => {
    jest.replaceProperty(Platform, "OS", "ios");
    const appendSpy = jest.spyOn(FormData.prototype, "append");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => savedRecord,
    });

    await sendVoiceRecord("file:///audio.m4a", 4321);

    expect(appendSpy).toHaveBeenCalledWith("duration_ms", "4321");
  });
});
