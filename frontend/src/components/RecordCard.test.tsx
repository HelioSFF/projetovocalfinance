import { render } from "@testing-library/react-native";
import type { FinancialRecord } from "../types/FinancialRecord";
import RecordCard from "./RecordCard";

jest.mock("@expo/vector-icons/Ionicons", () =>
  function MockIonicons() {
    return null;
  },
);

const expenseRecord: FinancialRecord = {
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

describe("RecordCard", () => {
  it("renders an expense with its quantity detail", async () => {
    const screen = await render(<RecordCard record={expenseRecord} />);

    expect(screen.getByText("Café")).toBeTruthy();
    expect(screen.getByText("Alimentação")).toBeTruthy();
    expect(screen.getByText("16/05/2026")).toBeTruthy();
    expect(screen.getByText("- R$ 15,00")).toBeTruthy();
    expect(screen.getByText("3 × R$ 5,00")).toBeTruthy();
  });

  it("renders an income with a plus sign and without quantity detail", async () => {
    const screen = await render(
      <RecordCard
        record={{
          ...expenseRecord,
          id: "record-2",
          type: "income",
          category: "sales",
          category_label: "Vendas",
          item: "venda",
          quantity: "1",
          unit_price: "2000.00",
          total: "2000.00",
        }}
      />,
    );

    expect(screen.getByText("Venda")).toBeTruthy();
    expect(screen.getByText("Vendas")).toBeTruthy();
    expect(screen.getByText("+ R$ 2.000,00")).toBeTruthy();
    expect(screen.queryByText("1 × R$ 2.000,00")).toBeNull();
  });
});
