module.exports = {
  content: ["./renderer/index.html", "./renderer/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Playfair Display", "Georgia", "serif"],
        body: ["Plus Jakarta Sans", "Segoe UI", "sans-serif"]
      },
      boxShadow: {
        luxe: "0 20px 40px rgba(47, 42, 36, 0.14)",
        soft: "0 10px 25px rgba(47, 42, 36, 0.08)"
      },
      animation: {
        pulseSoft: "pulseSoft 1.8s ease-in-out infinite"
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.04)", opacity: ".88" }
        }
      }
    }
  },
  plugins: []
};
