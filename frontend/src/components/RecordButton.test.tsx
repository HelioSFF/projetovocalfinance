import { fireEvent, render } from "@testing-library/react-native";
import { colors } from "../constants/colors";
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

  it("shows the recording look as soon as the finger touches the button", async () => {
    const screen = await renderButton("idle");
    const button = screen.getByRole("button");

    expect(button).not.toHaveStyle({ backgroundColor: colors.danger });

    await fireEvent(button, "pressIn");

    expect(button).toHaveStyle({ backgroundColor: colors.danger });

    await fireEvent(button, "pressOut");

    expect(button).not.toHaveStyle({ backgroundColor: colors.danger });
  });

  it("does not show the recording look while processing", async () => {
    const screen = await renderButton("processing");

    expect(screen.getByRole("button")).not.toHaveStyle({ backgroundColor: colors.danger });
  });

  it("has a touch area larger than the circle", async () => {
    const screen = await renderButton("idle");
    const { hitSlop } = screen.getByRole("button").props;

    expect(hitSlop).toEqual({ top: 24, bottom: 24, left: 24, right: 24 });
  });

  it("does not release the press on a long press", async () => {
    const onPressOut = jest.fn();
    const screen = await render(
      <RecordButton state="idle" onPress={jest.fn()} onPressIn={jest.fn()} onPressOut={onPressOut} />,
    );
    const button = screen.getByRole("button");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "longPress");

    expect(onPressOut).not.toHaveBeenCalled();
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
