import { render } from "@testing-library/react-native";
import EmptyState from "./EmptyState";

jest.mock("@expo/vector-icons/Ionicons", () =>
  function MockIonicons() {
    return null;
  },
);

describe("EmptyState", () => {
  it("renders the title and description", async () => {
    const screen = await render(
      <EmptyState title="Nenhum registro ainda" description="Os gastos aparecem aqui." />,
    );

    expect(screen.getByText("Nenhum registro ainda")).toBeTruthy();
    expect(screen.getByText("Os gastos aparecem aqui.")).toBeTruthy();
  });

  it("renders without a description", async () => {
    const screen = await render(<EmptyState title="Nenhum registro ainda" />);

    expect(screen.getByText("Nenhum registro ainda")).toBeTruthy();
  });
});
