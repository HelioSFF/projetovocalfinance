import type { VoiceDebug } from "./VoiceDebug";

export type FinancialRecordType = "income" | "expense";

export type FinancialRecord = {
  id: string;
  type: FinancialRecordType;
  category: string;
  category_label: string;
  item: string;
  quantity: string;
  unit_price: string;
  total: string;
  currency: string;
  transcript: string;
  normalized_text: string | null;
  created_at: string;
};

export type FinancialRecordList = {
  items: FinancialRecord[];
  limit: number;
  offset: number;
};

export type VoiceRecordResponse = FinancialRecord & {
  debug?: VoiceDebug;
};
