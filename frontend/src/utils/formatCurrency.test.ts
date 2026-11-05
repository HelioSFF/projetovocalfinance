import { formatCurrency } from "./formatCurrency";

describe("formatCurrency", () => {
  it("formats a number as BRL", () => {
    expect(formatCurrency(1234.5)).toBe("R$ 1.234,50");
  });

  it("formats a decimal string", () => {
    expect(formatCurrency("15.00")).toBe("R$ 15,00");
  });
});
