
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const iperf3ResultsPath = fileURLToPath(
  new URL('../validation_results/iperf3_results.json', import.meta.url)
)

function iperf3ResultsPlugin() {
  return {
    name: 'iperf3-results-reader',

    configureServer(server) {
      server.middlewares.use('/iperf3-results.json', async (req, res) => {
        if (req.method !== 'GET') {
          res.statusCode = 405
          res.end('Method not allowed')
          return
        }

        try {
          const rawContent = await readFile(iperf3ResultsPath, 'utf8')
          const content = rawContent.replace(/^\uFEFF/, '').trim()

          // Check that the file contains valid JSON.
          JSON.parse(content)

          res.statusCode = 200
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.setHeader('Cache-Control', 'no-store')
          res.end(content)
        } catch (error) {
         console.error('Could not read iperf3 results:', error.stack || error)
          res.statusCode = 500
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.end(JSON.stringify({
            error: 'Could not read or parse iperf3 results'
          }))
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), iperf3ResultsPlugin()],


server: {
  proxy: {
    '/api': {
      target: 'http://10.56.66.133:5000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
    '/iperf3-api': {
      target: 'http://10.56.66.133:5000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/iperf3-api/, '/iperf3'),
    },
  },
},

})
