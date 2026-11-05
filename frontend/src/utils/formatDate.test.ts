import { formatDate } from "./formatDate";

describe("formatDate", () => {
  it("formats a date as dd/mm/yyyy", () => {
    expect(formatDate(new Date(2026, 4, 16))).toBe("16/05/2026");
  });

  it("formats an ISO date string", () => {
    expect(formatDate("2026-05-16T12:00:00")).toBe("16/05/2026");
  });
});
