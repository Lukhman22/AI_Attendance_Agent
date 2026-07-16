/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Sora"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Outfit"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        brand: {
          50: '#eef8f6',
          100: '#d5efe9',
          200: '#abe0d5',
          300: '#78c9ba',
          400: '#47ab9a',
          500: '#2d8f80',
          600: '#227267',
          700: '#1e5c54',
          800: '#1c4a44',
          900: '#1a3e3a',
          950: '#0c2422',
        },
        ink: {
          50: '#f5f7f8',
          100: '#e5eaed',
          200: '#ced7dc',
          300: '#abb9c2',
          400: '#8195a2',
          500: '#667987',
          600: '#566370',
          700: '#4a5360',
          800: '#404851',
          900: '#393e46',
          950: '#24282d',
        },
      },
      boxShadow: {
        soft: '0 10px 30px -18px rgba(15, 23, 42, 0.35)',
      },
    },
  },
  plugins: [],
}
