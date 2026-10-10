/** @type {import('tailwindcss').Config} */
/**
 * Tailwind extends HPI design tokens for optional utility usage.
 * Page redesigns may adopt these gradually; existing class names stay valid.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        hpi: {
          bg: "var(--hpi-color-bg)",
          muted: "var(--hpi-color-bg-muted)",
          surface: "var(--hpi-color-surface)",
          ink: "var(--hpi-color-ink)",
          mute: "var(--hpi-color-mute)",
          faint: "var(--hpi-color-faint)",
          line: "var(--hpi-color-line)",
          accent: "var(--hpi-color-accent)",
          "accent-hover": "var(--hpi-color-accent-hover)",
          "on-accent": "var(--hpi-color-on-accent)",
          danger: "var(--hpi-color-danger)",
          warning: "var(--hpi-color-warning)",
          success: "var(--hpi-color-success)",
        },
      },
      fontFamily: {
        display: ["var(--hpi-font-heading)"],
        body: ["var(--hpi-font-body)"],
      },
      maxWidth: {
        content: "var(--hpi-max-content)",
        prose: "var(--hpi-max-prose)",
      },
      borderRadius: {
        hpi: "var(--hpi-radius-md)",
      },
      spacing: {
        "hpi-pad": "var(--hpi-pad-page)",
      },
      transitionDuration: {
        hpi: "var(--hpi-duration-base)",
      },
    },
  },
  plugins: [],
};
