import Ionicons from "@expo/vector-icons/Ionicons";
import { StyleSheet, Text, View } from "react-native";
import { getCategoryStyle } from "../constants/categoryStyles";
import { colors } from "../constants/colors";
import type { FinancialRecord } from "../types/FinancialRecord";
import { formatCurrency } from "../utils/formatCurrency";
import { formatDate } from "../utils/formatDate";

type RecordCardProps = {
  record: FinancialRecord;
};

export default function RecordCard({ record }: RecordCardProps) {
  const categoryStyle = getCategoryStyle(record.category);
  const isExpense = record.type === "expense";
  const itemLabel = record.item.charAt(0).toUpperCase() + record.item.slice(1);
  const showQuantity = Number(record.quantity) !== 1;

  return (
    <View style={styles.card}>
      <View style={[styles.icon, { backgroundColor: `${categoryStyle.color}22` }]}>
        <Ionicons name={categoryStyle.icon} size={24} color={categoryStyle.color} />
      </View>

      <View style={styles.info}>
        <Text style={styles.date}>{formatDate(record.created_at)}</Text>
        <Text style={styles.item}>{itemLabel}</Text>
        <View style={styles.categoryRow}>
          <View style={[styles.dot, { backgroundColor: categoryStyle.color }]} />
          <Text style={styles.category}>{record.category_label}</Text>
        </View>
        {showQuantity ? (
          <Text style={styles.quantity}>
            {record.quantity} × {formatCurrency(record.unit_price)}
          </Text>
        ) : null}
      </View>

      <Text style={[styles.total, isExpense ? styles.expense : styles.income]}>
        {isExpense ? "- " : "+ "}
        {formatCurrency(record.total)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    backgroundColor: colors.card,
    padding: 16,
  },
  icon: {
    alignItems: "center",
    justifyContent: "center",
    width: 48,
    height: 48,
    borderRadius: 12,
  },
  info: {
    flex: 1,
    gap: 2,
  },
  date: {
    color: colors.textMuted,
    fontSize: 12,
  },
  item: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "600",
  },
  categoryRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  category: {
    color: colors.textMuted,
    fontSize: 12,
  },
  quantity: {
    color: colors.textMuted,
    fontSize: 12,
  },
  total: {
    fontSize: 16,
    fontWeight: "700",
  },
  expense: {
    color: colors.text,
  },
  income: {
    color: colors.success,
  },
});
