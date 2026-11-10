/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
        obsidian: {
          950: "#0c0a09",
          900: "#141210",
          850: "#181512",
          800: "#1c1917",
          700: "#292524",
        },
        cream: {
          50: "#FFFDF7",
          100: "#FAF8F5",
          200: "#F5F2EB",
          300: "#E8E2D7",
          400: "#D6D0C7",
        },
      },
    },
  },
  plugins: [],
}
