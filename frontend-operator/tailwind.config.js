/** @type {import('tailwindcss').Config} */
export default {
	content: ['./index.html', './src/**/*.{ts,tsx}'],
	theme: {
		extend: {
			colors: {
				brand: { 50: '#eff6ff', 500: '#3b82f6', 700: '#1d4ed8' },
				flag: {
					low: '#f59e0b',
					high: '#ef4444',
					ok: '#22c55e',
					review: '#f97316',
				},
			},
		},
	},
	plugins: [],
};
