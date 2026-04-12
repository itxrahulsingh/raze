import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';

export default defineConfig({
  build: {
    lib: {
      entry: 'src/index.ts',
      name: 'RazeChat',
      fileName: (format) => `raze-chat.${format === 'es' ? 'es' : 'umd'}.js`
    },
    rollupOptions: {
      output: {
        // Global variable name
        name: 'RazeChat'
      }
    },
    minify: 'terser'
  },
  plugins: [dts()]
});
