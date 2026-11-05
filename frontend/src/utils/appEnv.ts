export function isDevToolsEnabled(): boolean {
  return process.env.EXPO_PUBLIC_APP_ENV === "development";
}
