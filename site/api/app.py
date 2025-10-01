# site/api/app.py
from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
from datetime import datetime
import urllib.request
import urllib.parse

# 🔥 URL DO SEU BACKEND (Render.com ou outro serviço)
BACKEND_URL = "https://seu-backend.onrender.com"  # ← SUBSTITUA COM SUA URL

class Handler(BaseHTTPRequestHandler):
    
    def set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        if self.path.startswith('/api/analysis/'):
            analysis_id = self.path.split('/')[-1]
            self.proxy_to_backend('GET', f'/api/analysis/{analysis_id}')
        elif self.path == '/api/health':
            self.health_check()
        else:
            self.send_error(404, "Endpoint não encontrado")
    
    def do_POST(self):
        if self.path == '/api/process-analysis':
            self.proxy_to_backend('POST', '/api/process-analysis')
        else:
            self.send_error(404, "Endpoint não encontrado")
    
    def health_check(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.set_cors_headers()
        self.end_headers()
        
        response = {
            "success": True,
            "message": "API Vercel está funcionando",
            "backend_url": BACKEND_URL,
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def proxy_to_backend(self, method, endpoint):
        """Encaminha requisições para o backend real"""
        try:
            print(f"🔀 Encaminhando {method} {endpoint} para backend...")
            
            # Ler dados da requisição original
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else None
            
            # Preparar requisição para o backend
            backend_url = f"{BACKEND_URL}{endpoint}"
            headers = {
                'Content-Type': self.headers.get('Content-Type', 'application/json'),
                'User-Agent': 'Vercel-Proxy/1.0'
            }
            
            # Fazer requisição para o backend
            req = urllib.request.Request(
                backend_url,
                data=post_data,
                headers=headers,
                method=method
            )
            
            with urllib.request.urlopen(req) as response:
                backend_data = response.read()
                backend_status = response.getcode()
                
                print(f"✅ Backend respondeu: {backend_status}")
                
                # Repassar resposta do backend para o cliente
                self.send_response(backend_status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self.set_cors_headers()
                self.end_headers()
                self.wfile.write(backend_data)
                
        except urllib.error.HTTPError as e:
            print(f"❌ Erro no backend: {e.code} - {e.reason}")
            self.send_error(e.code, f"Backend error: {e.reason}")
        except Exception as e:
            print(f"❌ Erro no proxy: {str(e)}")
            self.send_error(500, f"Proxy error: {str(e)}")

def handler(request, context):
    return Handler().handle_request(request)
