/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#a5422d",
          dark: "#6d2416",
          soft: "#f8ece8",
        },
      },
    },
  },
  plugins: [],
};
