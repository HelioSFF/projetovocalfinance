import { act, fireEvent, render, screen } from "@testing-library/react-native";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { getRecords, sendVoiceRecord } from "../services/recordService";
import { ApiError } from "../types/ApiError";
import type { FinancialRecord } from "../types/FinancialRecord";
import HomeScreen from "./HomeScreen";

jest.mock("@expo/vector-icons/Ionicons", () =>
  function MockIonicons() {
    return null;
  },
);

jest.mock("@react-navigation/native", () => ({
  useFocusEffect: jest.fn(),
}));

jest.mock("../hooks/useVoiceRecorder", () => ({
  useVoiceRecorder: jest.fn(),
}));

jest.mock("../services/recordService", () => ({
  getRecords: jest.fn(),
  sendVoiceRecord: jest.fn(),
}));

const prepareMock = jest.fn();
const startMock = jest.fn();
const stopMock = jest.fn();
const mockedUseVoiceRecorder = useVoiceRecorder as jest.Mock;
const mockedGetRecords = getRecords as jest.Mock;
const mockedSendVoiceRecord = sendVoiceRecord as jest.Mock;
const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;

const savedRecord: FinancialRecord = {
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

describe("HomeScreen voice flow", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    prepareMock.mockReset().mockResolvedValue(true);
    startMock.mockReset().mockResolvedValue(true);
    stopMock.mockReset().mockResolvedValue({ uri: "blob:audio", durationMs: 3000 });
    mockedUseVoiceRecorder.mockReturnValue({
      prepare: prepareMock,
      start: startMock,
      stop: stopMock,
      durationMs: 0,
    });
    mockedGetRecords.mockResolvedValue({ items: [], limit: 1, offset: 0 });
    mockedSendVoiceRecord.mockReset();
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
    jest.clearAllMocks();

    if (originalAppEnv === undefined) {
      delete process.env.EXPO_PUBLIC_APP_ENV;
    } else {
      process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
    }
  });

  it("discards a recording shorter than 700 ms", async () => {
    stopMock.mockResolvedValue({ uri: "blob:short", durationMs: 500 });
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");

    expect(mockedSendVoiceRecord).not.toHaveBeenCalled();
    expect(screen.getByText("Segure o botão enquanto fala")).toBeTruthy();
  });

  it("sends the audio and shows the saved record on success", async () => {
    mockedSendVoiceRecord.mockResolvedValue(savedRecord);
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");

    expect(mockedSendVoiceRecord).toHaveBeenCalledWith("blob:audio", 3000);
    expect(screen.getByText("Registrado: Café · R$ 15,00")).toBeTruthy();
    expect(screen.getByText("- R$ 15,00")).toBeTruthy();

    await act(async () => {
      jest.advanceTimersByTime(2500);
    });

    expect(screen.getByText("Segure para falar")).toBeTruthy();
  });

  it("shows the API error message", async () => {
    mockedSendVoiceRecord.mockRejectedValue(
      new ApiError("NOT_UNDERSTOOD", "Não entendi o gasto.", 422),
    );
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");

    expect(screen.getByText("Não entendi o gasto.")).toBeTruthy();
    expect(screen.getByText("Segure para tentar de novo")).toBeTruthy();
  });

  it("shows a connection error when the network fails", async () => {
    mockedSendVoiceRecord.mockRejectedValue(new TypeError("Network request failed"));
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");

    expect(screen.getByText("Sem conexão com o servidor")).toBeTruthy();
  });

  it("shows the permission message when the microphone is denied", async () => {
    startMock.mockResolvedValue(false);
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");

    expect(
      screen.getByText("Permita o acesso ao microfone para registrar por voz"),
    ).toBeTruthy();
    expect(stopMock).not.toHaveBeenCalled();
  });

  it("shows the short tap message while the recording start is pending", async () => {
    let resolveStart: ((value: boolean) => void) | undefined;
    startMock.mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          resolveStart = resolve;
        }),
    );
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");

    expect(screen.getByText("Segure o botão enquanto fala")).toBeTruthy();

    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    expect(screen.getByText("Segure o botão enquanto fala")).toBeTruthy();

    await act(async () => {
      resolveStart?.(true);
    });

    expect(stopMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Segure o botão enquanto fala")).toBeTruthy();
  });

  it("prepares the recorder again after a recording is sent", async () => {
    mockedSendVoiceRecord.mockResolvedValue(savedRecord);
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    expect(prepareMock).not.toHaveBeenCalled();

    await fireEvent(button, "pressOut");

    expect(prepareMock).toHaveBeenCalledTimes(1);
  });

  it("prepares the recorder again after a release that came before the start finished", async () => {
    let resolveStart: ((value: boolean) => void) | undefined;
    startMock.mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          resolveStart = resolve;
        }),
    );
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");
    await fireEvent(button, "pressOut");
    await act(async () => {
      resolveStart?.(true);
    });

    expect(prepareMock).toHaveBeenCalledTimes(1);
  });

  it("shows the hold message on a synthetic click without press events", async () => {
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "press");

    expect(screen.getByText("Segure o botão enquanto fala")).toBeTruthy();
    expect(startMock).not.toHaveBeenCalled();
  });

  it("stops and sends automatically after 60 seconds", async () => {
    mockedSendVoiceRecord.mockResolvedValue(savedRecord);
    await render(<HomeScreen />);
    const button = screen.getByLabelText("Segure para gravar");

    await fireEvent(button, "pressIn");

    await act(async () => {
      jest.advanceTimersByTime(60000);
    });

    expect(stopMock).toHaveBeenCalledTimes(1);
    expect(mockedSendVoiceRecord).toHaveBeenCalledWith("blob:audio", 3000);
  });

  it("hides DevPanel outside development", async () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    await render(<HomeScreen />);

    expect(screen.queryByText("Dev tools")).toBeNull();
  });

  it("shows DevPanel in development", async () => {
    process.env.EXPO_PUBLIC_APP_ENV = "development";
    await render(<HomeScreen />);

    expect(screen.getByText("Dev tools")).toBeTruthy();
  });
});
