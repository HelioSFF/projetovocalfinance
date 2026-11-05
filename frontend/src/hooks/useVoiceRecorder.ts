import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import { useCallback, useRef } from "react";

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
  const preparationRef = useRef<Promise<boolean> | null>(null);

  const prepare = useCallback((): Promise<boolean> => {
    if (preparationRef.current) {
      return preparationRef.current;
    }

    const preparation = (async () => {
      const permission = await AudioModule.requestRecordingPermissionsAsync();

      if (!permission.granted) {
        return false;
      }

      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
      });

      await recorder.prepareToRecordAsync();

      return true;
    })();

    preparationRef.current = preparation;

    preparation
      .then((prepared) => {
        if (!prepared && preparationRef.current === preparation) {
          preparationRef.current = null;
        }
      })
      .catch(() => {
        if (preparationRef.current === preparation) {
          preparationRef.current = null;
        }
      });

    return preparation;
  }, [recorder]);

  const start = useCallback(async () => {
    const prepared = await prepare();

    if (!prepared) {
      return false;
    }

    preparationRef.current = null;
    recorder.record();

    return true;
  }, [prepare, recorder]);

  const stop = useCallback(async (): Promise<VoiceRecording | null> => {
    const durationMs = recorder.getStatus().durationMillis;

    await recorder.stop();

    if (!recorder.uri) {
      return null;
    }

    return { uri: recorder.uri, durationMs };
  }, [recorder]);

  return {
    prepare,
    start,
    stop,
    durationMs: recorderState.durationMillis,
  };
}
