#!/usr/bin/env python3
"""
Proxy local — Dashboard de Apontamentos Geral (Filetagem e Refile)

Serve o dashboard e repassa chamadas à API do Grafana em 172.16.0.27:3000,
resolvendo bloqueios de CORS e mixed-content do browser.

Uso:
    python3 scripts/proxy.py

Acesse no browser:
    http://localhost:5002
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

GRAFANA = 'http://172.16.0.27:3000'
PORT    = 5002
ROOT    = os.path.join(os.path.dirname(__file__), '..')
DASH    = os.path.join(ROOT, 'dashboards', 'apontamentos-btj.html')

WRAP_HEAD = b'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}</style>
</head>
<body>
'''
WRAP_FOOT = b'\n</body></html>'


class Handler(BaseHTTPRequestHandler):

    # ── OPTIONS (preflight CORS) ──────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── GET ──────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path.rstrip('/') in ('', '/dashboard'):
            self._serve_dashboard()
        else:
            self._proxy('GET')

    # ── POST ─────────────────────────────────────────────────────────
    def do_POST(self):
        self._proxy('POST')

    # ── serve dashboard HTML ──────────────────────────────────────────
    def _serve_dashboard(self):
        try:
            with open(DASH, 'rb') as f:
                body = f.read()
            html = WRAP_HEAD + body + WRAP_FOOT
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Arquivo nao encontrado: ' + DASH.encode())

    # ── proxy para Grafana ────────────────────────────────────────────
    def _proxy(self, method):
        url = GRAFANA + self.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else None

        # repassa os headers originais, exceto os que causam conflito
        skip = {'host', 'content-length', 'origin', 'referer', 'connection'}
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in skip}

        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors()
                ct = resp.headers.get('Content-Type', 'application/json')
                self.send_header('Content-Type', ct)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            msg = f'Erro de proxy: {e}'.encode()
            self.send_response(502)
            self._cors()
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(msg)

    # ── CORS headers ──────────────────────────────────────────────────
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, fmt, *args):
        print(f'  {fmt % args}')


if __name__ == '__main__':
    if not os.path.exists(DASH):
        print(f'[ERRO] Dashboard nao encontrado em: {DASH}')
        print('Execute este script a partir da raiz do repositorio.')
        sys.exit(1)

    srv = HTTPServer(('0.0.0.0', PORT), Handler)
    print()
    print('  Dashboard de Apontamentos Geral')
    print(f'  http://localhost:{PORT}')
    print()
    print(f'  Proxy  ->  {GRAFANA}')
    print('  Ctrl+C para parar')
    print()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n  Proxy encerrado.')
