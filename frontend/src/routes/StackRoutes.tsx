import { createNativeStackNavigator } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../types/navigation";
import TabRoutes from "./TabRoutes";

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function StackRoutes() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="MainTabs" component={TabRoutes} />
    </Stack.Navigator>
  );
}
