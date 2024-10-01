import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        outDir: 'dist',
    },
    server: {
        port: 1948,
        /* "In 1948, backed by Columbia Records, the first vinyl record was introduced at the soon-to-be standardized 33 1/3 rpm speed."
         * - https://victrola.com/blogs/articles/beyond-the-needle-history-of-vinyl-records
        */
    },
    base: '/virtual-turntable/',
})
