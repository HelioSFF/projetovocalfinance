import Ionicons from "@expo/vector-icons/Ionicons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StyleSheet } from "react-native";
import { colors } from "../constants/colors";
import HistoryScreen from "../screens/HistoryScreen";
import HomeScreen from "../screens/HomeScreen";
import type { MainTabParamList } from "../types/navigation";

const Tab = createBottomTabNavigator<MainTabParamList>();

export default function TabRoutes() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.tabBarLabel,
        tabBarIcon: ({ color, size }) => (
          <Ionicons
            name={route.name === "Home" ? "home" : "receipt"}
            size={size}
            color={color}
          />
        ),
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: "Início" }} />
      <Tab.Screen name="History" component={HistoryScreen} options={{ title: "Histórico" }} />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.card,
    borderTopColor: colors.border,
  },
  tabBarLabel: {
    fontSize: 12,
    fontWeight: "600",
  },
});
