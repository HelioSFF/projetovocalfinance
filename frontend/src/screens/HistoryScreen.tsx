import Ionicons from "@expo/vector-icons/Ionicons";
import { useFocusEffect } from "@react-navigation/native";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import EmptyState from "../components/EmptyState";
import RecordCard from "../components/RecordCard";
import { colors } from "../constants/colors";
import { getRecords } from "../services/recordService";
import { ApiError } from "../types/ApiError";
import type { FinancialRecord } from "../types/FinancialRecord";
import { formatCurrency } from "../utils/formatCurrency";

export default function HistoryScreen() {
  const [records, setRecords] = useState<FinancialRecord[]>([]);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRecords = useCallback(async (query: string, isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    setError(null);

    try {
      const response = await getRecords({ q: query, limit: 50, offset: 0 });
      setRecords(response.items);
    } catch (loadError) {
      setError(loadError instanceof ApiError ? loadError.message : "Sem conexão com o servidor");
    } finally {
      if (isRefresh) {
        setIsRefreshing(false);
      } else {
        setIsLoading(false);
      }
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadRecords(appliedSearch);
    }, [appliedSearch, loadRecords]),
  );

  const handleSearch = () => {
    if (isLoading) {
      return;
    }

    const nextSearch = search.trim();

    if (nextSearch === appliedSearch) {
      loadRecords(nextSearch);
    } else {
      setAppliedSearch(nextSearch);
    }
  };

  const expenseTotal = records
    .filter((record) => record.type === "expense")
    .reduce((total, record) => total + Number(record.total), 0);

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <View style={styles.content}>
        <Text style={styles.title}>Histórico</Text>

        <View style={styles.summaryCard}>
          <View style={styles.summaryIcon}>
            <Ionicons name="receipt" size={28} color={colors.accent} />
          </View>
          <View style={styles.summaryText}>
            <Text style={styles.summaryLabel}>Gastos recentes</Text>
            <Text style={styles.summaryValue}>{formatCurrency(expenseTotal)}</Text>
          </View>
        </View>

        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color={colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder="Buscar gasto"
            placeholderTextColor={colors.textMuted}
            value={search}
            onChangeText={setSearch}
            onSubmitEditing={handleSearch}
            returnKeyType="search"
          />
        </View>

        <Text style={styles.sectionTitle}>Mais recentes</Text>

        {isLoading ? (
          <View style={styles.centered}>
            <ActivityIndicator color={colors.accent} />
          </View>
        ) : error ? (
          <View style={styles.centered}>
            <Text style={styles.errorMessage}>{error}</Text>
            <Pressable
              style={styles.retryButton}
              onPress={() => loadRecords(appliedSearch)}
              accessibilityRole="button"
            >
              <Text style={styles.retryLabel}>Tentar novamente</Text>
            </Pressable>
          </View>
        ) : (
          <FlatList
            style={styles.list}
            data={records}
            keyExtractor={(record) => record.id}
            renderItem={({ item }) => <RecordCard record={item} />}
            contentContainerStyle={styles.listContent}
            refreshing={isRefreshing}
            onRefresh={() => loadRecords(appliedSearch, true)}
            ListEmptyComponent={
              <EmptyState
                icon="time-outline"
                title={appliedSearch ? "Nenhum registro encontrado" : "Nenhum registro ainda"}
                description={
                  appliedSearch
                    ? "Tente buscar por outro termo."
                    : "Os gastos registrados aparecem aqui."
                }
              />
            }
            showsVerticalScrollIndicator={false}
          />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    gap: 16,
    paddingHorizontal: 16,
    paddingTop: 24,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: "700",
  },
  summaryCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    backgroundColor: colors.card,
    padding: 16,
  },
  summaryIcon: {
    alignItems: "center",
    justifyContent: "center",
    width: 56,
    height: 56,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  summaryText: {
    gap: 4,
  },
  summaryLabel: {
    color: colors.textMuted,
    fontSize: 14,
  },
  summaryValue: {
    color: colors.text,
    fontSize: 28,
    fontWeight: "700",
  },
  searchContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    backgroundColor: colors.card,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  searchInput: {
    flex: 1,
    color: colors.text,
    fontSize: 16,
    padding: 0,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: 14,
    fontWeight: "500",
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    paddingBottom: 24,
  },
  errorMessage: {
    color: colors.danger,
    fontSize: 14,
    textAlign: "center",
  },
  retryButton: {
    borderWidth: 1,
    borderColor: colors.accent,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  retryLabel: {
    color: colors.accent,
    fontSize: 14,
    fontWeight: "600",
  },
  list: {
    flex: 1,
  },
  listContent: {
    flexGrow: 1,
    gap: 12,
    paddingBottom: 24,
  },
});
