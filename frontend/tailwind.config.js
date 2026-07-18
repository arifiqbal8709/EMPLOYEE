/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#0B0C10",
          card: "rgba(22, 26, 44, 0.45)",
          border: "rgba(255, 255, 255, 0.08)",
          accent: "#4F46E5",
          accentHover: "#4338CA",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
          textHead: "#FFFFFF",
          textBody: "#C5C6C7"
        }
      },
      backdropBlur: {
        xs: "2px"
      }
    },
  },
  plugins: [],
}
