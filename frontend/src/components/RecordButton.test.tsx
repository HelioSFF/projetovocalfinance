import { fireEvent, render } from "@testing-library/react-native";
import RecordButton, { type RecordButtonState } from "./RecordButton";

jest.mock("@expo/vector-icons/Ionicons", () => {
  const { Text } = jest.requireActual("react-native");

  return function MockIonicons({ name }: { name: string }) {
    return <Text>{name}</Text>;
  };
});

function renderButton(state: RecordButtonState) {
  return render(
    <RecordButton
      state={state}
      onPress={jest.fn()}
      onPressIn={jest.fn()}
      onPressOut={jest.fn()}
    />,
  );
}

describe("RecordButton", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("shows the microphone when idle", async () => {
    const screen = await renderButton("idle");

    expect(screen.getByText("mic")).toBeTruthy();
    expect(screen.getByRole("button")).not.toBeDisabled();
  });

  it("shows the microphone while recording", async () => {
    const screen = await renderButton("recording");

    expect(screen.getByText("mic")).toBeTruthy();
  });

  it("disables the button and shows a spinner while processing", async () => {
    const screen = await renderButton("processing");

    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByTestId("record-button-spinner")).toBeTruthy();
  });

  it("shows a check mark after success", async () => {
    const screen = await renderButton("success");

    expect(screen.getByText("checkmark-circle")).toBeTruthy();
  });

  it("calls the press handlers", async () => {
    const onPress = jest.fn();
    const onPressIn = jest.fn();
    const onPressOut = jest.fn();
    const screen = await render(
      <RecordButton
        state="idle"
        onPress={onPress}
        onPressIn={onPressIn}
        onPressOut={onPressOut}
      />,
    );
    const button = screen.getByRole("button");

    await fireEvent(button, "press");
    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");

    expect(onPress).toHaveBeenCalledTimes(1);
    expect(onPressIn).toHaveBeenCalledTimes(1);
    expect(onPressOut).toHaveBeenCalledTimes(1);
  });
});
