import { useState } from "react";
import { Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import { colors } from "../constants/colors";
import type {
  DebugAcceptanceValue,
  DebugStage,
  DecisionAnswer,
  VoiceDebug,
} from "../types/VoiceDebug";
import { formatMs, formatUsd, stageBarStyle } from "../utils/formatDebug";
import JsonBlock from "./JsonBlock";

type DevPanelProps = {
  debug: VoiceDebug | null;
  clientTotalMs: number | null;
};

function formatProbability(value: number | null): string {
  return value === null ? "—" : String(value);
}

function answerText(answer: DecisionAnswer): string {
  if (answer.type === "predicate") {
    return `probability ${formatProbability(answer.probability)}`;
  }

  if (answer.type === "choice") {
    return `${answer.choice ?? "—"} (${formatProbability(answer.confidence)})`;
  }

  return "refusal";
}

function topProbabilitiesText(answer: DecisionAnswer): string {
  return answer.top_probabilities
    .map((item) => `${item.value} ${formatProbability(item.probability)}`)
    .join(" · ");
}

function acceptanceText(label: string, value: DebugAcceptanceValue): string {
  return `${value.passed ? "✓" : "✗"} ${label} ${formatProbability(value.value)}`;
}

function StagesSection({
  debug,
  clientTotalMs,
}: {
  debug: VoiceDebug;
  clientTotalMs: number | null;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Etapas</Text>
      {debug.timing.stages.map((stage, index) => (
        <StageRow
          key={`${stage.name}-${stage.attempt ?? "main"}-${index}`}
          stage={stage}
          totalMs={debug.timing.server_total_ms}
        />
      ))}
      <Text style={styles.meta}>Servidor: {formatMs(debug.timing.server_total_ms)}</Text>
      {clientTotalMs !== null ? (
        <Text style={styles.meta}>
          Rede + upload ≈ {formatMs(Math.max(clientTotalMs - debug.timing.server_total_ms, 0))}
        </Text>
      ) : null}
    </View>
  );
}

function StageRow({ stage, totalMs }: { stage: DebugStage; totalMs: number }) {
  const bar = stageBarStyle(stage, totalMs);
  const barColor = stage.error ? colors.danger : stage.parallel ? colors.accent : colors.primary;

  return (
    <View style={styles.stage}>
      <View style={styles.stageHeader}>
        <Text style={[styles.stageLabel, stage.parallel && styles.stageLabelParallel]}>
          {stage.label}
          {stage.attempt !== null ? ` #${stage.attempt}` : ""}
        </Text>
        <Text style={styles.stageDuration}>{formatMs(stage.duration_ms)}</Text>
      </View>
      <View style={styles.barTrack}>
        <View
          style={[
            styles.barFill,
            {
              marginLeft: `${bar.left}%` as DimensionValue,
              width: `${bar.width}%` as DimensionValue,
              backgroundColor: barColor,
            },
          ]}
        />
      </View>
      {stage.error ? (
        <Text style={styles.stageError}>
          {stage.error}
          {stage.http_status ? ` (${stage.http_status})` : ""}
        </Text>
      ) : null}
    </View>
  );
}

function CostsSection({ debug }: { debug: VoiceDebug }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Tokens e custo</Text>
      {debug.costs.lines.map((line, index) => (
        <View key={`${line.stage}-${line.attempt ?? "main"}-${index}`} style={styles.costLine}>
          <View style={styles.costHeader}>
            <Text style={styles.costTitle}>
              {line.stage}
              {line.attempt !== null ? ` #${line.attempt}` : ""} · {line.model}
            </Text>
            <Text style={styles.costValue}>
              {formatUsd(line.usd)}
              {line.estimated ? " *" : ""}
            </Text>
          </View>
          <Text style={styles.meta}>{line.basis}</Text>
        </View>
      ))}
      <Text style={styles.total}>Total da mensagem: {formatUsd(debug.costs.total_usd)}</Text>
      {debug.costs.estimated ? <Text style={styles.meta}>* estimativa</Text> : null}
    </View>
  );
}

function TranscriptionSection({ debug }: { debug: VoiceDebug }) {
  const transcription = debug.transcription;

  if (!transcription) {
    return (
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Transcrição bruta</Text>
        <Text style={styles.meta}>—</Text>
      </View>
    );
  }

  const audioSeconds =
    transcription.audio_seconds !== null ? `${transcription.audio_seconds} s` : "—";
  const audioSource = transcription.audio_seconds_source
    ? ` (${transcription.audio_seconds_source})`
    : "";

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Transcrição bruta</Text>
      <Text style={styles.quote}>{`"${transcription.text ?? "—"}"`}</Text>
      <Text style={styles.meta}>{`Áudio: ${audioSeconds}${audioSource}`}</Text>
    </View>
  );
}

function DecisionsSection({ debug }: { debug: VoiceDebug }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Decisions</Text>
      {debug.attempts.map((attempt) => (
        <View key={attempt.number} style={styles.attempt}>
          <Text style={styles.attemptTitle}>
            Tentativa {attempt.number} · {attempt.source}
          </Text>
          {attempt.decision.answers.map((answer) => (
            <View key={answer.name} style={styles.answer}>
              <View style={styles.answerHeader}>
                <Text style={styles.answerName}>{answer.name}</Text>
                <Text style={styles.answerValue}>{answerText(answer)}</Text>
              </View>
              {answer.top_probabilities.length > 0 ? (
                <Text style={styles.meta}>{topProbabilitiesText(answer)}</Text>
              ) : null}
              {answer.refusal ? <Text style={styles.refusal}>{answer.refusal}</Text> : null}
            </View>
          ))}
          <JsonBlock value={attempt.decision} />
        </View>
      ))}
    </View>
  );
}

function ExtractionSection({ debug }: { debug: VoiceDebug }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Extração</Text>
      {debug.attempts.map((attempt) => (
        <View key={attempt.number} style={styles.attempt}>
          <Text style={styles.attemptTitle}>Tentativa {attempt.number}</Text>
          {attempt.extraction ? (
            <JsonBlock value={attempt.extraction.parsed ?? attempt.extraction.raw_text} />
          ) : (
            <Text style={styles.meta}>—</Text>
          )}
        </View>
      ))}
    </View>
  );
}

function AcceptanceSection({ debug }: { debug: VoiceDebug }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Aceite</Text>
      <Text style={styles.meta}>Limiar: {String(debug.threshold)}</Text>
      {debug.attempts.map((attempt) => (
        <View key={attempt.number} style={styles.attempt}>
          <Text style={styles.attemptTitle}>Tentativa {attempt.number}</Text>
          <Text
            style={attempt.acceptance.plausible.passed ? styles.pass : styles.fail}
          >
            {acceptanceText("plausible", attempt.acceptance.plausible)}
          </Text>
          <Text
            style={attempt.acceptance.is_financial.passed ? styles.pass : styles.fail}
          >
            {acceptanceText("is_financial", attempt.acceptance.is_financial)}
          </Text>
          <Text style={attempt.acceptance.extraction_valid ? styles.pass : styles.fail}>
            {`${attempt.acceptance.extraction_valid ? "✓" : "✗"} extração válida`}
          </Text>
          <Text style={attempt.acceptance.accepted ? styles.pass : styles.fail}>
            Resultado: {attempt.acceptance.accepted ? "aceito" : "recusado"}
          </Text>
        </View>
      ))}
      <Text style={styles.meta}>
        {debug.fallback.used
          ? `Fallback DeepSeek: usado → "${debug.fallback.rewritten_text ?? "—"}"`
          : "Fallback DeepSeek: não usado"}
      </Text>
    </View>
  );
}

function ResultSection({ debug }: { debug: VoiceDebug }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Registro final</Text>
      {debug.result ? (
        <View style={styles.attempt}>
          <Text style={styles.formula}>{debug.result.formula}</Text>
          <Text style={styles.meta}>
            Tipo: {debug.result.type_choice} → {debug.result.type}
          </Text>
          <Text style={styles.meta}>
            Categoria: {debug.result.category_choice} → {debug.result.category}
          </Text>
          <Text style={styles.meta}>
            {debug.result.reconciled ? "Reconciliado" : "Sem reconciliação"}
          </Text>
        </View>
      ) : (
        <Text style={styles.fail}>
          Nada gravado ({debug.failure_code ?? debug.outcome})
        </Text>
      )}
    </View>
  );
}

export default function DevPanel({ debug, clientTotalMs }: DevPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const header = debug
    ? `Dev tools · ${formatMs(debug.timing.server_total_ms)} · ${formatUsd(debug.costs.total_usd)}`
    : "Dev tools";

  return (
    <View style={styles.panel}>
      <Pressable
        style={styles.header}
        onPress={() => setExpanded((value) => !value)}
        accessibilityRole="button"
        accessibilityLabel="Alternar Dev tools"
      >
        <Text style={styles.headerText}>{header}</Text>
        <Text style={styles.chevron}>{expanded ? "▾" : "▸"}</Text>
      </Pressable>

      {expanded ? (
        debug ? (
          <View style={styles.content}>
            <StagesSection debug={debug} clientTotalMs={clientTotalMs} />
            <CostsSection debug={debug} />
            <TranscriptionSection debug={debug} />
            <DecisionsSection debug={debug} />
            <ExtractionSection debug={debug} />
            <AcceptanceSection debug={debug} />
            <ResultSection debug={debug} />
          </View>
        ) : (
          <Text style={styles.emptyText}>
            Sem dados de debug: o backend não está em development.
          </Text>
        )
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    width: "100%",
    gap: 12,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    backgroundColor: colors.card,
    padding: 16,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  headerText: {
    flex: 1,
    color: colors.text,
    fontSize: 14,
    fontWeight: "600",
  },
  chevron: {
    color: colors.textMuted,
    fontSize: 14,
  },
  content: {
    gap: 16,
  },
  section: {
    gap: 6,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  meta: {
    color: colors.textMuted,
    fontSize: 12,
  },
  stage: {
    gap: 4,
  },
  stageHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  stageLabel: {
    flex: 1,
    color: colors.text,
    fontSize: 12,
  },
  stageLabelParallel: {
    marginLeft: 12,
  },
  stageDuration: {
    color: colors.textMuted,
    fontSize: 12,
  },
  barTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.border,
    overflow: "hidden",
  },
  barFill: {
    height: 6,
    borderRadius: 3,
  },
  stageError: {
    color: colors.danger,
    fontSize: 12,
  },
  costLine: {
    gap: 2,
  },
  costHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  costTitle: {
    flex: 1,
    color: colors.text,
    fontSize: 12,
  },
  costValue: {
    color: colors.text,
    fontSize: 12,
    fontWeight: "600",
  },
  total: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "700",
  },
  quote: {
    color: colors.text,
    fontSize: 14,
    fontStyle: "italic",
  },
  attempt: {
    gap: 6,
  },
  attemptTitle: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: "600",
  },
  answer: {
    gap: 2,
  },
  answerHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  answerName: {
    color: colors.text,
    fontSize: 12,
    fontWeight: "600",
  },
  answerValue: {
    color: colors.textMuted,
    fontSize: 12,
  },
  refusal: {
    color: colors.danger,
    fontSize: 12,
  },
  pass: {
    color: colors.success,
    fontSize: 12,
  },
  fail: {
    color: colors.danger,
    fontSize: 12,
  },
  formula: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "600",
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 12,
  },
});
