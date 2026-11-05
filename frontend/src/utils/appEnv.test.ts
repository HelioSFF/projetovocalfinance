import { isDevToolsEnabled } from "./appEnv";

const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;

afterEach(() => {
  if (originalAppEnv === undefined) {
    delete process.env.EXPO_PUBLIC_APP_ENV;
  } else {
    process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
  }
});

describe("isDevToolsEnabled", () => {
  it("is true only for development", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "development";
    expect(isDevToolsEnabled()).toBe(true);

    process.env.EXPO_PUBLIC_APP_ENV = "Development";
    expect(isDevToolsEnabled()).toBe(false);

    process.env.EXPO_PUBLIC_APP_ENV = "production";
    expect(isDevToolsEnabled()).toBe(false);

    process.env.EXPO_PUBLIC_APP_ENV = "";
    expect(isDevToolsEnabled()).toBe(false);

    process.env.EXPO_PUBLIC_APP_ENV = "dev";
    expect(isDevToolsEnabled()).toBe(false);
  });
});
