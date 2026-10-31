import Ionicons from "@expo/vector-icons/Ionicons";
import { colors } from "./colors";

type CategoryStyle = {
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
};

export const defaultCategoryStyle: CategoryStyle = {
  icon: "pricetag",
  color: colors.textMuted,
};

export const categoryStyles: Record<string, CategoryStyle> = {
  food: { icon: "restaurant", color: "#F7B11A" },
  groceries: { icon: "cart", color: "#01D58A" },
  housing: { icon: "home", color: "#04C7D2" },
  utilities: { icon: "flash", color: "#F7B11A" },
  transport: { icon: "car", color: "#0955EF" },
  health: { icon: "medkit", color: "#F25C6B" },
  education: { icon: "school", color: "#818CF8" },
  leisure: { icon: "game-controller", color: "#A78BFA" },
  shopping: { icon: "bag-handle", color: "#04C7D2" },
  clothing: { icon: "shirt", color: "#F472B6" },
  personal_care: { icon: "sparkles", color: "#E879F9" },
  pets: { icon: "paw", color: "#FB923C" },
  subscriptions: { icon: "repeat", color: "#60A5FA" },
  travel: { icon: "airplane", color: "#22D3EE" },
  taxes_fees: { icon: "document-text", color: "#94A3B8" },
  gifts_donations: { icon: "gift", color: "#F472B6" },
  other_expense: { icon: "ellipsis-horizontal-circle", color: colors.textMuted },
  salary: { icon: "cash", color: "#01D58A" },
  freelance: { icon: "briefcase", color: "#04C7D2" },
  sales: { icon: "storefront", color: "#F7B11A" },
  investments: { icon: "trending-up", color: "#01D58A" },
  refunds: { icon: "return-down-back", color: "#60A5FA" },
  gifts_received: { icon: "gift", color: "#F472B6" },
  other_income: { icon: "ellipsis-horizontal-circle", color: colors.textMuted },
};

export function getCategoryStyle(category: string): CategoryStyle {
  return categoryStyles[category] ?? defaultCategoryStyle;
}
