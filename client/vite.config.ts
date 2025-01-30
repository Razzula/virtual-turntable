import { networkInterfaces } from 'os';
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

function getlocalIP() {
    const nets = networkInterfaces();
    for (const name of Object.keys(nets)) {
        for (const iface of nets[name] || []) {
            if (iface.family === 'IPv4' && !iface.internal) {
                return iface.address;
            }
        }
    }
    return 'localhost';
}

const localIP = getlocalIP();
console.log(`Running on ${localIP}`);

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
        proxy: {
            '/virtual-turntable/auth': {
                target: `http://${localIP}:8491`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/virtual-turntable/, ''),
                configure: (proxy) => {
                    console.log('Proxy instance configured');
                    proxy.on('proxyReq', (proxyReq, req) => {
                        const rawClientIP = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
                        if (rawClientIP && typeof rawClientIP === 'string') {
                            const clientIP = rawClientIP?.replace(/^::ffff:/, '');
                            proxyReq.setHeader('X-Forwarded-For', clientIP);
                        }
                    });
                },
            },
            '/virtual-turntable/server': {
                target: `http://${localIP}:8491`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/virtual-turntable\/server/, ''),
                configure: (proxy) => {
                    console.log('Proxy instance configured');
                    proxy.on('proxyReq', (proxyReq, req) => {
                        const rawClientIP = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
                        if (rawClientIP && typeof rawClientIP === 'string') {
                            const clientIP = rawClientIP?.replace(/^::ffff:/, '');
                            proxyReq.setHeader('X-Forwarded-For', clientIP);
                        }
                    });
                },
            },
        },
        host: true,
    },
    preview: {
        port: 1948,
        /* "In 1948, backed by Columbia Records, the first vinyl record was introduced at the soon-to-be standardized 33 1/3 rpm speed."
         * - https://victrola.com/blogs/articles/beyond-the-needle-history-of-vinyl-records
        */
        proxy: {
            '/virtual-turntable/auth': {
                target: `http://${localIP}:8491`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/virtual-turntable/, ''),
                configure: (proxy) => {
                    proxy.on('proxyReq', (proxyReq, req) => {
                        const rawClientIP = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
                        if (rawClientIP && typeof rawClientIP === 'string') {
                            const clientIP = rawClientIP?.replace(/^::ffff:/, '');
                            proxyReq.setHeader('X-Forwarded-For', clientIP);
                        }
                    });
                },
            },
            '/virtual-turntable/server': {
                target: `http://${localIP}:8491`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/virtual-turntable\/server/, ''),
                configure: (proxy) => {
                    proxy.on('proxyReq', (proxyReq, req) => {
                        const rawClientIP = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
                        if (rawClientIP && typeof rawClientIP === 'string') {
                            const clientIP = rawClientIP?.replace(/^::ffff:/, '');
                            proxyReq.setHeader('X-Forwarded-For', clientIP);
                        }
                    });
                },
            },
        },
        host: true,
    },
    base: '/virtual-turntable/',
    define: {
        'process.env.HOST_URL': JSON.stringify(localIP),
    },
});
