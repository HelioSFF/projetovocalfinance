import { useFocusEffect } from "@react-navigation/native";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import DevPanel from "../components/DevPanel";
import EmptyState from "../components/EmptyState";
import RecordButton, { type RecordButtonState } from "../components/RecordButton";
import RecordCard from "../components/RecordCard";
import StatusMessage from "../components/StatusMessage";
import { colors } from "../constants/colors";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { getRecords, sendVoiceRecord } from "../services/recordService";
import { ApiError } from "../types/ApiError";
import type { FinancialRecord } from "../types/FinancialRecord";
import type { VoiceDebug } from "../types/VoiceDebug";
import { isDevToolsEnabled } from "../utils/appEnv";
import { formatCurrency } from "../utils/formatCurrency";

type VoiceStatus = "idle" | "recording" | "processing" | "success" | "error";

function formatDuration(durationMs: number): string {
  const totalSeconds = Math.floor(durationMs / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");

  return `${minutes}:${seconds}`;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getStatusText(status: VoiceStatus, feedback: string, durationMs: number): string {
  if (status === "recording") {
    return formatDuration(durationMs);
  }

  if (status === "processing") {
    return "Entendendo seu gasto…";
  }

  if (status === "success" || status === "error") {
    return feedback;
  }

  return "Segure para falar";
}

function getStatusHint(status: VoiceStatus): string | null {
  if (status === "recording") {
    return "Solte para enviar";
  }

  if (status === "error") {
    return "Segure para tentar de novo";
  }

  if (status === "idle") {
    return "Ex.: comprei 3 cafés de 5 reais";
  }

  return null;
}

export default function HomeScreen() {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [feedback, setFeedback] = useState("");
  const [lastRecord, setLastRecord] = useState<FinancialRecord | null>(null);
  const [isLoadingLastRecord, setIsLoadingLastRecord] = useState(true);
  const [hasLastRecordError, setHasLastRecordError] = useState(false);
  const [lastDebug, setLastDebug] = useState<VoiceDebug | null>(null);
  const [clientTotalMs, setClientTotalMs] = useState<number | null>(null);
  const isPressingRef = useRef(false);
  const isStartingRef = useRef(false);
  const isRecordingRef = useRef(false);
  const isFinishingRef = useRef(false);
  const { start, stop, durationMs } = useVoiceRecorder();

  const loadLastRecord = useCallback(async () => {
    setIsLoadingLastRecord(true);
    setHasLastRecordError(false);

    try {
      const response = await getRecords({ limit: 1 });
      setLastRecord(response.items[0] ?? null);
    } catch {
      setLastRecord(null);
      setHasLastRecordError(true);
    } finally {
      setIsLoadingLastRecord(false);
    }
  }, []);

  const finishRecording = useCallback(async () => {
    if (isFinishingRef.current) {
      return;
    }

    isFinishingRef.current = true;
    setStatus("processing");
    let requestStarted: number | null = null;

    try {
      const recording = await stop();
      isRecordingRef.current = false;

      if (!recording || recording.durationMs < 700) {
        setStatus("error");
        setFeedback("Segure o botão enquanto fala");
        return;
      }

      requestStarted = Date.now();
      const savedRecord = await sendVoiceRecord(recording.uri, recording.durationMs);
      setClientTotalMs(Date.now() - requestStarted);
      setLastDebug(savedRecord.debug ?? null);
      setLastRecord(savedRecord);
      setIsLoadingLastRecord(false);
      setHasLastRecordError(false);
      setStatus("success");
      setFeedback(`Registrado: ${capitalize(savedRecord.item)} · ${formatCurrency(savedRecord.total)}`);
    } catch (sendError) {
      if (requestStarted !== null) {
        setClientTotalMs(Date.now() - requestStarted);
      }

      if (sendError instanceof ApiError) {
        setLastDebug(sendError.debug ?? null);
        setStatus("error");
        setFeedback(sendError.message);
      } else {
        setLastDebug(null);
        setStatus("error");
        setFeedback("Sem conexão com o servidor");
      }
    } finally {
      isFinishingRef.current = false;
    }
  }, [stop]);

  const startRecording = async () => {
    if (isStartingRef.current || isRecordingRef.current || status === "processing") {
      return;
    }

    isStartingRef.current = true;
    isPressingRef.current = true;
    setLastDebug(null);
    setClientTotalMs(null);
    setFeedback("");

    try {
      const started = await start();

      if (!started) {
        isPressingRef.current = false;
        setStatus("error");
        setFeedback("Permita o acesso ao microfone para registrar por voz");
        return;
      }

      if (!isPressingRef.current) {
        await stop();
        isRecordingRef.current = false;
        setStatus("error");
        setFeedback("Segure o botão enquanto fala");
        return;
      }

      isRecordingRef.current = true;
      setStatus("recording");
    } catch {
      isPressingRef.current = false;
      setStatus("error");
      setFeedback("Não foi possível iniciar a gravação.");
    } finally {
      isStartingRef.current = false;
    }
  };

  const handleRecordStart = () => {
    void startRecording();
  };

  const handleRecordEnd = () => {
    isPressingRef.current = false;

    if (isRecordingRef.current) {
      finishRecording();
      return;
    }

    if (isStartingRef.current) {
      setStatus("error");
      setFeedback("Segure o botão enquanto fala");
    }
  };

  const handleRecordPress = () => {
    if (status === "idle" && !isStartingRef.current) {
      setStatus("error");
      setFeedback("Segure o botão enquanto fala");
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadLastRecord();
    }, [loadLastRecord]),
  );

  useEffect(() => {
    if (status !== "recording") {
      return;
    }

    const timeout = setTimeout(() => {
      finishRecording();
    }, 60000);

    return () => clearTimeout(timeout);
  }, [finishRecording, status]);

  useEffect(() => {
    if (status !== "success") {
      return;
    }

    const timeout = setTimeout(() => {
      setStatus("idle");
      setFeedback("");
    }, 2500);

    return () => clearTimeout(timeout);
  }, [status]);

  const buttonState: RecordButtonState = status === "error" ? "idle" : status;
  const statusTone: "default" | "danger" | "success" =
    status === "error" ? "danger" : status === "success" ? "success" : "default";
  const statusText = getStatusText(status, feedback, durationMs);
  const statusHint = getStatusHint(status);

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Olá!</Text>
          <Text style={styles.subtitle}>Registre seus gastos falando</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Último registro</Text>
          {isLoadingLastRecord ? (
            <View style={styles.stateCard}>
              <ActivityIndicator color={colors.accent} />
            </View>
          ) : hasLastRecordError ? (
            <View style={styles.stateCard}>
              <EmptyState
                icon="cloud-offline-outline"
                title="Não foi possível carregar"
                description="Verifique a conexão com o servidor."
              />
            </View>
          ) : lastRecord ? (
            <RecordCard record={lastRecord} />
          ) : (
            <View style={styles.stateCard}>
              <EmptyState
                title="Nenhum registro ainda"
                description="Segure o microfone e fale seu primeiro gasto."
              />
            </View>
          )}
        </View>

        <View style={styles.voiceArea}>
          <RecordButton
            state={buttonState}
            onPress={handleRecordPress}
            onPressIn={handleRecordStart}
            onPressOut={handleRecordEnd}
          />
          <StatusMessage message={statusText} tone={statusTone} />
          {statusHint ? <Text style={styles.voiceHint}>{statusHint}</Text> : null}
        </View>

        {isDevToolsEnabled() ? (
          <DevPanel debug={lastDebug} clientTotalMs={clientTotalMs} />
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    gap: 24,
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 32,
  },
  header: {
    gap: 4,
  },
  greeting: {
    color: colors.text,
    fontSize: 28,
    fontWeight: "700",
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 14,
  },
  section: {
    gap: 8,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: 14,
    fontWeight: "500",
  },
  stateCard: {
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    backgroundColor: colors.card,
    padding: 16,
  },
  voiceArea: {
    alignItems: "center",
    gap: 12,
    paddingVertical: 16,
  },
  voiceHint: {
    color: colors.textMuted,
    fontSize: 14,
    textAlign: "center",
  },
});
