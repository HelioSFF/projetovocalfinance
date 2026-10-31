import { StyleSheet, Text } from "react-native";
import { colors } from "../constants/colors";

type StatusMessageProps = {
  message: string;
  tone?: "default" | "danger" | "success";
};

export default function StatusMessage({ message, tone = "default" }: StatusMessageProps) {
  return <Text style={[styles.message, styles[tone]]}>{message}</Text>;
}

const styles = StyleSheet.create({
  message: {
    fontSize: 16,
    fontWeight: "600",
    textAlign: "center",
  },
  default: {
    color: colors.text,
  },
  danger: {
    color: colors.danger,
  },
  success: {
    color: colors.success,
  },
});
