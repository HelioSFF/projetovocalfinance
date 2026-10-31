import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import { useCallback } from "react";

const recordingOptions = {
  ...RecordingPresets.HIGH_QUALITY,
  numberOfChannels: 1,
  bitRate: 48000,
  web: {
    ...RecordingPresets.HIGH_QUALITY.web,
    bitsPerSecond: 48000,
  },
};

export type VoiceRecording = {
  uri: string;
  durationMs: number;
};

export function useVoiceRecorder() {
  const recorder = useAudioRecorder(recordingOptions);
  const recorderState = useAudioRecorderState(recorder, 200);

  const start = useCallback(async () => {
    const permission = await AudioModule.requestRecordingPermissionsAsync();

    if (!permission.granted) {
      return false;
    }

    await setAudioModeAsync({
      allowsRecording: true,
      playsInSilentMode: true,
    });

    await recorder.prepareToRecordAsync();
    recorder.record();

    return true;
  }, [recorder]);

  const stop = useCallback(async (): Promise<VoiceRecording | null> => {
    const durationMs = recorder.getStatus().durationMillis;

    await recorder.stop();

    if (!recorder.uri) {
      return null;
    }

    return { uri: recorder.uri, durationMs };
  }, [recorder]);

  return {
    start,
    stop,
    durationMs: recorderState.durationMillis,
  };
}
