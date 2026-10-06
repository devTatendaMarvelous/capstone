/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14241c",
        paper: "#f4f7f3",
        canvas: "#f4f7f3",
        leaf: "#14613f",
        moss: "#3d6b54",
        clay: "#b44532",
        mist: "#e8f5ec",
        line: "#e2e8e3",
        lime: "#d7f26a",
      },
      fontFamily: {
        sans: ["Outfit", "Segoe UI", "sans-serif"],
        serif: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(20, 36, 28, 0.04), 0 16px 40px rgba(20, 36, 28, 0.06)",
      },
    },
  },
  plugins: [],
};
