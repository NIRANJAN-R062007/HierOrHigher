/**
 * HireOrHigher design tokens.
 *
 * One palette + type scale + spacing system shared by BOTH surfaces:
 * the cinematic dark landing pages (ink base, gold accent) and the light,
 * functional dashboard (paper base, same gold + ink for continuity).
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    fontFamily: {
      display: ["Fraunces", "Georgia", "serif"],
      sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
    },
    extend: {
      colors: {
        ink: {
          950: "#06080D",
          900: "#0B0E14",
          800: "#121826",
          700: "#1B2334",
          600: "#293349",
          500: "#3A4763",
          400: "#5C6A8A",
        },
        gold: {
          200: "#EFDCB0",
          300: "#E3C88A",
          400: "#D6B26A",
          500: "#C9A961",
          600: "#AC8C46",
          700: "#8C7136",
        },
        paper: {
          50: "#FBFAF7",
          100: "#F5F3EC",
          200: "#EAE7DC",
          300: "#DCD8C8",
        },
      },
      fontSize: {
        "display-xl": [
          "clamp(2.75rem, 6vw, 4.75rem)",
          { lineHeight: "1.05", letterSpacing: "-0.02em" },
        ],
        "display-lg": [
          "clamp(2rem, 4vw, 3rem)",
          { lineHeight: "1.1", letterSpacing: "-0.015em" },
        ],
        eyebrow: [
          "0.75rem",
          { lineHeight: "1.4", letterSpacing: "0.28em" },
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11, 14, 20, 0.06), 0 8px 24px rgba(11, 14, 20, 0.08)",
        lift: "0 12px 40px rgba(11, 14, 20, 0.35)",
        "gold-glow": "0 0 48px rgba(201, 169, 97, 0.25)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(24px)" },
          to: { opacity: "1", transform: "none" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "glow-pan": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-14px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.7s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fade-in 0.5s ease both",
        "page-in": "fade-in 0.35s ease both",
        "glow-pan": "glow-pan 14s ease-in-out infinite",
        "pulse-dot": "pulse-dot 1.2s ease-in-out infinite",
        float: "float 7s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
