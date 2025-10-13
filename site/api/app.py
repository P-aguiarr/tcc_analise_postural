# app.py (Proxy) - VERSÃO FINAL COM FIX DE CORS REFORÇADO E ROTA DE LOGIN

import json
import os
import uuid
from datetime import datetime
import requests 

# Importações do Flask
from flask import Flask, jsonify, request, abort, make_response
from flask_cors import CORS

# 🔥 URL DO SEU BACKEND DE ANÁLISE (O servidor que realmente processa o login/análise)
# CERTIFIQUE-SE de que esta variável está configurada no painel do Railway
# ou que o fallback (se usar) é o endereço correto.
BACKEND_URL = os.environ.get("BACKEND_URL", "https://seu-backend-de-analise.com")

# 1. INICIALIZAR A APLICAÇÃO FLASK
app = Flask(__name__)

# 🔥 CORREÇÃO CRÍTICA DO CORS:
# Configuração super-reforçada para aceitar seu Frontend Vercel
# Isto garante que o preflight OPTIONS (onde o erro ocorria) seja permitido.
CORS(app, resources={r"/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",  # SEU DOMÍNIO VERCEL (Exato)
    "http://localhost:8080",                   # Para desenvolvimento local do Frontend
    "http://localhost:5000",                   # Para desenvolvimento local do Proxy/Backend
    "http://127.0.0.1:5000"                    
], 
"methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Incluir OPTIONS é CRÍTICO para CORS
"allow_headers": ["Content-Type", "Authorization"], 
"supports_credentials": True 
}})

# -----------------------------------------------------
# FUNÇÃO CENTRAL DE PROXY (Encaminhamento)
# -----------------------------------------------------

def proxy_to_backend(endpoint, method, data=None, headers=None):
    """Encaminha requisições para o backend real usando a biblioteca 'requests'."""
    url = f"{BACKEND_URL}{endpoint}"
    
    # Prepara os headers a enviar para o backend
    proxy_headers = {
        # Mantém o Content-Type original do cliente se ele veio
        'Content-Type': request.headers.get('Content-Type', 'application/json'),
        'User-Agent': 'Railway-Proxy/1.0',
    }
    
    # Copia o header de Authorization se existir, necessário para autenticação
    if 'Authorization' in request.headers:
        proxy_headers['Authorization'] = request.headers['Authorization']

    # Adiciona/Substitui quaisquer headers adicionais passados
    if headers:
        proxy_headers.update(headers)
        
    print(f"🔀 Encaminhando {method} {url}...")

    try:
        # Fazer a requisição para o backend
        response = requests.request(
            method=method,
            url=url,
            headers=proxy_headers,
            # Se a requisição for GET, data é None. Se for POST/PUT, usa request.data
            data=request.data if method in ['POST', 'PUT'] else None,
            timeout=30 # Timeout para evitar requisições presas
        )

        # Criar a resposta do Flask com o conteúdo e status do backend
        flask_response = make_response(response.content, response.status_code)
        
        # Copia todos os headers do backend para o cliente
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Rota de Healthcheck.
    """
    try:
        # Testa a conexão com o backend real
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

# 🔥 ROTA CRÍTICA DE LOGIN (Agora presente e esperando POST)
@app.route('/api/auth/callback', methods=['POST'])
def google_auth_callback_route():
    """
    Recebe o token do Google (via POST do Frontend) e encaminha para o Backend.
    """
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
