import { Platform } from "react-native";
import type { FinancialRecordList, VoiceRecordResponse } from "../types/FinancialRecord";
import { request } from "./api";

type GetRecordsParams = {
  q?: string;
  limit?: number;
  offset?: number;
};

type NativeAudioFile = {
  uri: string;
  name: string;
  type: string;
};

export function getRecords({
  q,
  limit = 50,
  offset = 0,
}: GetRecordsParams = {}): Promise<FinancialRecordList> {
  const params = new URLSearchParams();

  if (q) {
    params.set("q", q);
  }

  params.set("limit", String(limit));
  params.set("offset", String(offset));

  return request<FinancialRecordList>(`/api/financial-records?${params.toString()}`);
}

export async function sendVoiceRecord(
  uri: string,
  durationMs?: number,
): Promise<VoiceRecordResponse> {
  const formData = new FormData();

  if (Platform.OS === "web") {
    const response = await fetch(uri);
    const blob = await response.blob();

    formData.append("file", blob, "audio.webm");
  } else {
    const audioFile: NativeAudioFile = { uri, name: "audio.m4a", type: "audio/m4a" };

    formData.append("file", audioFile as unknown as Blob);
  }

  if (durationMs !== undefined) {
    formData.append("duration_ms", String(Math.round(durationMs)));
  }

  return request<VoiceRecordResponse>("/api/voice-records", {
    method: "POST",
    body: formData,
  });
}
