# app.py (Proxy) - VERSÃO DEFINITIVA COM CORS REFORÇADO E ROTA DE DIAGNÓSTICO

import json
import os
import uuid
from datetime import datetime
import requests 

# Importações do Flask
from flask import Flask, jsonify, request, abort, make_response
from flask_cors import CORS

# 🔥 URL DO SEU BACKEND DE ANÁLISE 
# Aqui, a variável de ambiente é lida.
BACKEND_URL = os.environ.get("BACKEND_URL", "https://seu-backend-de-analise.com")

# 1. INICIALIZAR A APLICAÇÃO FLASK
app = Flask(__name__)

# 🔥 CONFIGURAÇÃO CRÍTICA DO CORS:
# Define os domínios que podem fazer requisições para este Proxy.
CORS(app, resources={r"/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",   # SEU DOMÍNIO VERCEL (Frontend)
    "http://localhost:8080",                     # Para desenvolvimento local do Frontend
    "http://localhost:5000",                     # Para desenvolvimento local do Proxy/Backend
    "http://127.0.0.1:5000"                      
], 
"methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
"allow_headers": ["Content-Type", "Authorization"], 
"supports_credentials": True 
}})

# -----------------------------------------------------
# ** TRATAMENTO MANUAL DO PREFLIGHT OPTIONS (CRUCIAL!) **
# Garante que requests OPTIONS feitos pelo navegador retornem 200 OK
# com os headers CORS corretos antes de fazer o request POST real.
@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        # O Flask-CORS deve adicionar os cabeçalhos, mas esta função
        # garante o retorno imediato e correto do status 200.
        return make_response('', 200)
# -----------------------------------------------------

# -----------------------------------------------------
# FUNÇÃO CENTRAL DE PROXY (Encaminhamento)
# -----------------------------------------------------

def proxy_to_backend(endpoint, method, data=None, headers=None):
    """Encaminha requisições para o backend real usando a biblioteca 'requests'."""
    url = f"{BACKEND_URL}{endpoint}"
    
    proxy_headers = {
        'Content-Type': request.headers.get('Content-Type', 'application/json'),
        'User-Agent': 'Railway-Proxy/1.0',
    }
    
    # Passar o header de autorização, se existir
    if 'Authorization' in request.headers:
        proxy_headers['Authorization'] = request.headers['Authorization']

    if headers:
        proxy_headers.update(headers)
        
    print(f"🔀 Encaminhando {method} {url}...")

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=proxy_headers,
            # Se for POST ou PUT, envia os dados brutos da requisição original
            data=request.data if method in ['POST', 'PUT'] else None,
            timeout=30  
        )

        flask_response = make_response(response.content, response.status_code)
        
        # Copia todos os headers do backend (exceto os que o Flask ou o Gunicorn gerenciam)
        for key, value in response.headers.items():
            if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']:
                flask_response.headers[key] = value

        print(f"✅ Resposta do backend: {response.status_code}")
        return flask_response

    except requests.exceptions.Timeout:
        print(f"❌ Erro de Timeout ao tentar alcançar: {url}")
        return jsonify({"success": False, "error": f"Backend demorou demais para responder: {url}"}), 504
    except requests.exceptions.ConnectionError:
        print(f"❌ Erro de Conexão: Backend inacessível em {BACKEND_URL}")
        return jsonify({"success": False, "error": f"Não foi possível conectar ao backend em: {BACKEND_URL}"}), 503
    except Exception as e:
        print(f"❌ Erro inesperado no proxy: {e}")
        return jsonify({"success": False, "error": f"Erro interno do proxy: {str(e)}"}), 500


# -----------------------------------------------------
# ROTAS DO PROXY
# -----------------------------------------------------

# ROTA DE DIAGNÓSTICO
@app.route('/api/debug/backend-url', methods=['GET'])
def debug_backend_url():
    """Retorna a URL do backend configurada no ambiente."""
    return jsonify({
        "success": True,
        "message": "URL do Backend lida pelo Proxy",
        "backend_url_lida": BACKEND_URL,
        "timestamp": datetime.now().isoformat()
    }), 200 

@app.route('/api/health', methods=['GET'])
def health_check():
    """Rota de Healthcheck."""
    try:
        # Tenta checar a saúde do backend usando a URL lida
        requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        backend_status = "ok"
    except:
        backend_status = "unreachable"

    return jsonify({
        "success": True,
        "message": "API Proxy Flask está funcionando",
        "backend_url": BACKEND_URL, 
        "backend_status": backend_status,
        "timestamp": datetime.now().isoformat()
    }), 200 

# Rota de Login (Precisa do POST e OPTIONS/Preflight)
@app.route('/api/auth/callback', methods=['POST'])
def google_auth_callback_route():
    """Recebe o token do Google (via POST) e encaminha para o Backend."""
    return proxy_to_backend(
        endpoint='/api/auth/callback',
        method='POST',
        data=request.data
    )

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    """Rota POST para encaminhar /api/process-analysis."""
    return proxy_to_backend(
        endpoint='/api/process-analysis', 
        method='POST',
        data=request.data
    )

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    """Rota GET para /api/analysis/<id>."""
    return proxy_to_backend(
        endpoint=f'/api/analysis/{analysis_id}',
        method='GET'
    )

# -----------------------------------------------------
# COMANDO DE INICIALIZAÇÃO
# -----------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Servidor Proxy Flask rodando em http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
