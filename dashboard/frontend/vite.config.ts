import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false, // Allow Vite to use next available port if 5173 is busy
    open: true // Auto-open browser
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})