import { ApiError } from "../types/ApiError";
import type { VoiceDebug } from "../types/VoiceDebug";

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
  };
  debug?: VoiceDebug;
};

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, options);

  if (!response.ok) {
    let errorResponse: ApiErrorResponse | null = null;

    try {
      errorResponse = (await response.json()) as ApiErrorResponse;
    } catch {
      errorResponse = null;
    }

    throw new ApiError(
      errorResponse?.error?.code ?? "UNKNOWN_ERROR",
      errorResponse?.error?.message ?? "Não foi possível concluir a solicitação.",
      response.status,
      errorResponse?.debug,
    );
  }

  return (await response.json()) as T;
}
