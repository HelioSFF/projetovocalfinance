import { Platform, ScrollView, StyleSheet, Text } from "react-native";
import { colors } from "../constants/colors";

type JsonBlockProps = {
  value: unknown;
};

export default function JsonBlock({ value }: JsonBlockProps) {
  const content = typeof value === "string" ? value : JSON.stringify(value, null, 2);

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontal}>
      <ScrollView style={styles.vertical} nestedScrollEnabled showsVerticalScrollIndicator={false}>
        <Text style={styles.code}>{content}</Text>
      </ScrollView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  horizontal: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    backgroundColor: colors.background,
  },
  vertical: {
    maxHeight: 220,
    padding: 12,
  },
  code: {
    color: colors.text,
    fontFamily: Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" }),
    fontSize: 12,
  },
});
