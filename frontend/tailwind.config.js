import tailwindcssAnimate from 'tailwindcss-animate'

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Display: Bricolage Grotesque — headings, hero, brand
        display: ['"Bricolage Grotesque"', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        // UI/body: Schibsted Grotesk — everything else
        sans: ['"Schibsted Grotesk"', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
      },
      // Échelle 5 crans, ratio >=1.25, rem fixes (app UI, pas de clamp fluide)
      fontSize: {
        'meta': ['0.75rem', { lineHeight: '1.5', letterSpacing: '0.01em' }],
        'body': ['1rem', { lineHeight: '1.6' }],
        'subhead': ['1.375rem', { lineHeight: '1.4' }],
        'heading': ['2.25rem', { lineHeight: '1.2', letterSpacing: '-0.01em' }],
        'display': ['3.5rem', { lineHeight: '1.08', letterSpacing: '-0.02em' }],
      },
      colors: {
        // 品牌色 - 使用 CSS 变量
        'banana': {
          DEFAULT: 'var(--banana-yellow)',
          light: 'var(--banana-yellow-light)',
          dark: 'var(--banana-yellow-dark)',
          pale: 'var(--banana-yellow-pale)',
          // 保留静态色用于渐变等特殊场景 — OKLCH, même teinte (H90) que les tokens
          50: 'oklch(97% 0.03 90)',
          100: 'oklch(90% 0.09 90)',
          200: 'oklch(85% 0.13 90)',
          300: 'oklch(82% 0.15 90)',
          400: 'oklch(80% 0.16 90)',
          500: 'oklch(78% 0.17 90)',
          600: 'oklch(70% 0.18 90)',
        },
        // 背景色 - 语义化 token (+ shadcn DEFAULT via OKLCH channels)
        'background': {
          DEFAULT: 'oklch(var(--background) / <alpha-value>)',
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
          elevated: 'var(--bg-elevated)',
          hover: 'var(--bg-hover)',
        },
        // 文字色 - 语义化 token (+ shadcn DEFAULT)
        'foreground': {
          DEFAULT: 'oklch(var(--foreground) / <alpha-value>)',
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
        },
        // 边框色 - 语义化 token (+ shadcn DEFAULT)
        'border': {
          DEFAULT: 'oklch(var(--border) / <alpha-value>)',
          primary: 'var(--border-primary)',
          secondary: 'var(--border-secondary)',
          hover: 'var(--border-hover)',
        },
        // shadcn/ui semantic colors — OKLCH channels + alpha support
        'input': 'oklch(var(--input) / <alpha-value>)',
        'ring': 'oklch(var(--ring) / <alpha-value>)',
        'primary': {
          DEFAULT: 'oklch(var(--primary) / <alpha-value>)',
          foreground: 'oklch(var(--primary-foreground) / <alpha-value>)',
        },
        'secondary': {
          DEFAULT: 'oklch(var(--secondary) / <alpha-value>)',
          foreground: 'oklch(var(--secondary-foreground) / <alpha-value>)',
        },
        'muted': {
          DEFAULT: 'oklch(var(--muted) / <alpha-value>)',
          foreground: 'oklch(var(--muted-foreground) / <alpha-value>)',
        },
        'accent': {
          DEFAULT: 'oklch(var(--accent) / <alpha-value>)',
          foreground: 'oklch(var(--accent-foreground) / <alpha-value>)',
        },
        'destructive': {
          DEFAULT: 'oklch(var(--destructive) / <alpha-value>)',
          foreground: 'oklch(var(--destructive-foreground) / <alpha-value>)',
        },
        'card': {
          DEFAULT: 'oklch(var(--card) / <alpha-value>)',
          foreground: 'oklch(var(--card-foreground) / <alpha-value>)',
        },
        'popover': {
          DEFAULT: 'oklch(var(--popover) / <alpha-value>)',
          foreground: 'oklch(var(--popover-foreground) / <alpha-value>)',
        },
        // 功能色
        'success': 'var(--success)',
        'warning': 'var(--warning)',
        'error': 'var(--error)',
        'info': 'var(--info)',
      },
      borderRadius: {
        'card': '12px',
        'panel': '16px',
      },
      boxShadow: {
        'yellow': '0 4px 12px oklch(78% 0.17 90 / 0.3)',
        'sm': '0 1px 2px rgba(0,0,0,0.05)',
        'md': '0 4px 6px rgba(0,0,0,0.07)',
        'lg': '0 10px 15px rgba(0,0,0,0.1)',
        'xl': '0 20px 25px rgba(0,0,0,0.15)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
        '3xl': '0 35px 60px -12px rgba(0, 0, 0, 0.2)',
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 1.5s infinite',
        'gradient': 'gradient 3s ease infinite',
        'gradient-x': 'gradient-x 2s ease infinite',
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'float-delayed': 'float 7s ease-in-out infinite 1s',
        'fade-in-up': 'fadeInUp 0.8s ease-out forwards',
        'fade-in': 'fadeIn 1s ease-out forwards',
        'slide-in-up': 'slideInUp 0.35s ease-out both',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        slideInUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'gradient-x': {
          '0%, 100%': { backgroundPosition: '0% 0%' },
          '50%': { backgroundPosition: '100% 0%' },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate],
}
