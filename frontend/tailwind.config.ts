import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: { ink: "#050806", panel: "#0b120d", line: "#1c3321", accent: "#36ef75", muted: "#8ba28f" },
    },
  },
  plugins: [],
} satisfies Config;

