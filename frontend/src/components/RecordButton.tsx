import Ionicons from "@expo/vector-icons/Ionicons";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Platform,
  Pressable,
  StyleSheet,
  View,
  type ViewStyle,
} from "react-native";
import { colors } from "../constants/colors";

export type RecordButtonState = "idle" | "recording" | "processing" | "success";

type RecordButtonProps = {
  state: RecordButtonState;
  onPress: () => void;
  onPressIn: () => void;
  onPressOut: () => void;
};

const touchHitSlop = { top: 24, bottom: 24, left: 24, right: 24 };
const pressRetentionOffset = { top: 80, bottom: 80, left: 80, right: 80 };
const webTouchStyle = (
  Platform.OS === "web"
    ? { touchAction: "none", WebkitTouchCallout: "none", WebkitTapHighlightColor: "transparent" }
    : null
) as ViewStyle | null;

function preventLongPressMenu() {}

export default function RecordButton({
  state,
  onPress,
  onPressIn,
  onPressOut,
}: RecordButtonProps) {
  const [pulse] = useState(() => new Animated.Value(1));
  const [isPressed, setIsPressed] = useState(false);
  const isRecording = state === "recording" || (isPressed && state === "idle");
  const isProcessing = state === "processing";

  useEffect(() => {
    if (!isRecording) {
      pulse.setValue(1);
      return;
    }

    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.18, duration: 600, useNativeDriver: false }),
        Animated.timing(pulse, { toValue: 1, duration: 600, useNativeDriver: false }),
      ]),
    );

    animation.start();

    return () => animation.stop();
  }, [isRecording, pulse]);

  const handlePressIn = () => {
    setIsPressed(true);
    onPressIn();
  };

  const handlePressOut = () => {
    setIsPressed(false);
    onPressOut();
  };

  return (
    <View style={styles.container}>
      {isRecording ? (
        <Animated.View style={[styles.pulse, { transform: [{ scale: pulse }] }]} />
      ) : null}
      <Pressable
        style={[
          styles.button,
          webTouchStyle,
          isRecording && styles.recordingButton,
          state === "success" && styles.successButton,
        ]}
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        onLongPress={preventLongPressMenu}
        hitSlop={touchHitSlop}
        pressRetentionOffset={pressRetentionOffset}
        disabled={isProcessing}
        accessibilityRole="button"
        accessibilityLabel="Segure para gravar"
        accessibilityState={{ disabled: isProcessing }}
      >
        {isProcessing ? (
          <ActivityIndicator testID="record-button-spinner" color={colors.accent} />
        ) : state === "success" ? (
          <Ionicons name="checkmark-circle" size={44} color={colors.success} />
        ) : (
          <Ionicons name="mic" size={44} color={isRecording ? colors.text : colors.accent} />
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    width: 150,
    height: 150,
  },
  pulse: {
    position: "absolute",
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 2,
    borderColor: colors.danger,
  },
  button: {
    alignItems: "center",
    justifyContent: "center",
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 2,
    borderColor: colors.accent,
    backgroundColor: colors.card,
    userSelect: "none",
  },
  recordingButton: {
    borderColor: colors.danger,
    backgroundColor: colors.danger,
  },
  successButton: {
    borderColor: colors.success,
  },
});
