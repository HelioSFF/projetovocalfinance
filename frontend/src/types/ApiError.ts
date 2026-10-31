import type { VoiceDebug } from "./VoiceDebug";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly debug?: VoiceDebug;

  constructor(code: string, message: string, status: number, debug?: VoiceDebug) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.debug = debug;
  }
}
