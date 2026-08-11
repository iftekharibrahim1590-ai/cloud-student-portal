/**
 * Reverse proxy: forwards all traffic on port 3000 to the Flask app on 8001.
 * This lets Flask serve HTML at "/", "/login", "/dashboard" etc., since the
 * platform ingress routes non-"/api" traffic to port 3000.
 */
const http = require('http');
const httpProxy = require('http-proxy');

const PORT = process.env.PORT || 3000;
const TARGET = process.env.FLASK_TARGET || 'http://127.0.0.1:8001';

const proxy = httpProxy.createProxyServer({
  target: TARGET,
  changeOrigin: true,
  xfwd: true,
  ws: true,
});

proxy.on('error', (err, req, res) => {
  console.error('[proxy] error:', err.message);
  if (res && !res.headersSent) {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
  }
  if (res) res.end('Bad gateway: Flask backend unreachable.');
});

const server = http.createServer((req, res) => {
  proxy.web(req, res);
});

server.on('upgrade', (req, socket, head) => {
  proxy.ws(req, socket, head);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[proxy] listening on 0.0.0.0:${PORT} -> ${TARGET}`);
});
