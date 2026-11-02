import { act, renderHook } from "@testing-library/react-native";
import { AudioModule, setAudioModeAsync } from "expo-audio";
import { useVoiceRecorder } from "./useVoiceRecorder";

const mockRecorder = {
  prepareToRecordAsync: jest.fn(),
  record: jest.fn(),
  stop: jest.fn(),
  getStatus: jest.fn(),
  uri: "blob:audio",
};

jest.mock("expo-audio", () => ({
  AudioModule: { requestRecordingPermissionsAsync: jest.fn() },
  RecordingPresets: { HIGH_QUALITY: { web: {} } },
  setAudioModeAsync: jest.fn(),
  useAudioRecorder: () => mockRecorder,
  useAudioRecorderState: () => ({ durationMillis: 0 }),
}));

const requestPermissionMock = AudioModule.requestRecordingPermissionsAsync as jest.Mock;
const setAudioModeMock = setAudioModeAsync as jest.Mock;

describe("useVoiceRecorder", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    requestPermissionMock.mockResolvedValue({ granted: true });
    setAudioModeMock.mockResolvedValue(undefined);
    mockRecorder.prepareToRecordAsync.mockResolvedValue(undefined);
    mockRecorder.stop.mockResolvedValue(undefined);
    mockRecorder.getStatus.mockReturnValue({ durationMillis: 1200 });
  });

  it("starts recording without asking for permission again after being prepared", async () => {
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.prepare();
    });

    requestPermissionMock.mockClear();
    mockRecorder.prepareToRecordAsync.mockClear();

    let started = false;
    await act(async () => {
      started = await result.current.start();
    });

    expect(started).toBe(true);
    expect(requestPermissionMock).not.toHaveBeenCalled();
    expect(mockRecorder.prepareToRecordAsync).not.toHaveBeenCalled();
    expect(mockRecorder.record).toHaveBeenCalledTimes(1);
  });

  it("prepares only once when prepare is called repeatedly", async () => {
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await Promise.all([result.current.prepare(), result.current.prepare()]);
    });

    expect(requestPermissionMock).toHaveBeenCalledTimes(1);
    expect(mockRecorder.prepareToRecordAsync).toHaveBeenCalledTimes(1);
  });

  it("prepares on demand when start runs before any preparation", async () => {
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });

    expect(mockRecorder.prepareToRecordAsync).toHaveBeenCalledTimes(1);
    expect(mockRecorder.record).toHaveBeenCalledTimes(1);
  });

  it("prepares again for the next recording after a start", async () => {
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.start();
    });

    expect(mockRecorder.prepareToRecordAsync).toHaveBeenCalledTimes(2);
  });

  it("returns false and does not record when the microphone is denied", async () => {
    requestPermissionMock.mockResolvedValue({ granted: false });
    const { result } = await renderHook(() => useVoiceRecorder());

    let started = true;
    await act(async () => {
      started = await result.current.start();
    });

    expect(started).toBe(false);
    expect(mockRecorder.record).not.toHaveBeenCalled();
  });

  it("asks for permission again on the next press after a denial", async () => {
    requestPermissionMock.mockResolvedValueOnce({ granted: false });
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.start();
    });

    expect(requestPermissionMock).toHaveBeenCalledTimes(2);
    expect(mockRecorder.record).toHaveBeenCalledTimes(1);
  });

  it("returns the recording uri and duration on stop", async () => {
    const { result } = await renderHook(() => useVoiceRecorder());

    let recording = null;
    await act(async () => {
      recording = await result.current.stop();
    });

    expect(recording).toEqual({ uri: "blob:audio", durationMs: 1200 });
  });
});
