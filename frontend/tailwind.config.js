/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Outfit"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'xs':   ['0.75rem',  { lineHeight: '1.125rem', letterSpacing: '0.01em' }],
        'sm':   ['0.8125rem', { lineHeight: '1.25rem' }],
        'base': ['0.875rem', { lineHeight: '1.375rem' }],
        'lg':   ['1rem',     { lineHeight: '1.5rem' }],
        'xl':   ['1.125rem', { lineHeight: '1.625rem' }],
        '2xl':  ['1.375rem', { lineHeight: '1.75rem',  letterSpacing: '-0.01em' }],
        '3xl':  ['1.75rem',  { lineHeight: '2.125rem', letterSpacing: '-0.02em' }],
      },
      colors: {
        brand: {
          50:  '#f0faf8',
          100: '#d4f1eb',
          200: '#a9e3d7',
          300: '#72cebe',
          400: '#45b3a0',
          500: '#2d9585',
          600: '#22776b',
          700: '#1f6158',
          800: '#1d4e48',
          900: '#1b413c',
          950: '#0a2724',
        },
        ink: {
          50:  '#f8f9fa',
          100: '#eef0f3',
          200: '#dce1e6',
          300: '#bec6cf',
          400: '#97a3b0',
          500: '#768493',
          600: '#5e6b79',
          700: '#4d5865',
          800: '#434c56',
          900: '#3a414a',
          950: '#1e2228',
        },
        surface: {
          DEFAULT: '#ffffff',
          dark: '#1a1e24',
        },
      },
      spacing: {
        '4.5': '1.125rem',
        '13':  '3.25rem',
        '15':  '3.75rem',
        '18':  '4.5rem',
      },
      borderRadius: {
        'lg':  '0.5rem',
        'xl':  '0.625rem',
        '2xl': '0.75rem',
        '3xl': '1rem',
      },
      boxShadow: {
        'soft':     '0 1px 2px 0 rgba(0, 0, 0, 0.04), 0 1px 3px 0 rgba(0, 0, 0, 0.06)',
        'card':     '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 2px 8px -2px rgba(0, 0, 0, 0.06)',
        'elevated': '0 4px 16px -4px rgba(0, 0, 0, 0.08), 0 1px 3px 0 rgba(0, 0, 0, 0.04)',
        'modal':    '0 8px 32px -8px rgba(0, 0, 0, 0.14), 0 2px 8px -2px rgba(0, 0, 0, 0.06)',
        'ring':     '0 0 0 3px rgba(45, 149, 133, 0.16)',
      },
      ringWidth: {
        '3': '3px',
      },
      ringColor: {
        brand: 'rgba(45, 149, 133, 0.24)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'zoom-in': {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        }
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out forwards',
        'slide-up': 'slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-down': 'slide-down 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'zoom-in': 'zoom-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'shimmer': 'shimmer 2s infinite linear',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
