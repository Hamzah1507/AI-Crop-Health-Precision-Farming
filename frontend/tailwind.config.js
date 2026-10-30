/** @type {import('tailwindcss').Config} */

// ---------------------------------------------------------------------------
// CropHealth AI design tokens
//
// The application's existing markup uses Tailwind's `green`, `slate` and `gray`
// names. Rather than editing every class, those scales are remapped here to the
// brand palette, so the whole UI follows one identity:
//   green  -> deep forest (action) to botanical (accent) to pale leaf tints
//   slate / gray -> warm, slightly green-tinted neutrals (ivory surfaces,
//                   green-gray secondary text)
// Semantic status colors (red, amber, blue) keep Tailwind's defaults.
// ---------------------------------------------------------------------------
const forest = {
  50:  '#F0F7F2',
  100: '#DDEDE3',
  200: '#BBDBC9',
  300: '#8DC2A5',
  400: '#55A37A',   // botanical accent
  500: '#2F8559',
  600: '#1F6E47',
  700: '#17583A',   // primary action (deep forest)
  800: '#124530',
  900: '#0E3324',
  950: '#08201A',
};

const neutral = {
  50:  '#F8F7F3',   // ivory tint
  100: '#F1EFE8',
  200: '#E6E3D9',   // hairline borders
  300: '#D4D0C3',   // input borders
  400: '#8F9A92',   // icons, placeholders
  500: '#5F6D64',   // muted green-gray text (>= 4.5:1 on white and ivory)
  600: '#4A5750',
  700: '#364239',
  800: '#232D27',
  900: '#14201A',   // headings
  950: '#0B130F',
};

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        green: forest,
        slate: neutral,
        gray: neutral,
        primary: forest,
        ivory: '#F1F1EE',   // neutral light workspace background (matches the reference)
        earth: {
          50: '#fdf8f0',
          100: '#f5e6d0',
          200: '#e8d0a8',
          300: '#d4b07a',
          400: '#c09455',
          500: '#a67b3d',
          600: '#8b6530',
          700: '#6d4f25',
          800: '#553d1d',
          900: '#3d2c15',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['Newsreader', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      borderRadius: {
        card: '16px',
        control: '10px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(20, 32, 26, 0.04), 0 1px 1px rgba(20, 32, 26, 0.02)',
        lift: '0 4px 14px -4px rgba(20, 32, 26, 0.10)',
      },
    },
  },
  plugins: [],
}
