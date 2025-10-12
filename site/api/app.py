# app.py (Proxy) - CORRIGIDO
import json
import os
import uuid
from datetime import datetime
import requests # Usaremos a biblioteca 'requests' para o proxy (mais moderna que urllib)

# Importações do Flask
from flask import Flask, jsonify, request, abort, make_response
from flask_cors import CORS

# 🔥 URL DO SEU BACKEND (Railway/Render.com ou outro serviço)
# É crucial que esta URL esteja correta e acessível.
# No Railway, esta variável deve ser configurada na seção "Variables" do serviço.
BACKEND_URL = os.environ.get("BACKEND_URL", "https://seu-backend.onrender.com")

# 1. INICIALIZAR A APLICAÇÃO FLASK
app = Flask(__name__)

# 🔥 CORREÇÃO CRÍTICA (1): Configurar CORS para aceitar o domínio Vercel
# Usaremos o domínio exato do seu log.
# Adicione também http://localhost:5000 para testes locais no backend.
CORS(app, resources={r"/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",  # Seu Frontend Vercel
    "http://localhost:8080",                   # Localhost Vercel/Frontend
    "http://localhost:5000",                   # Localhost Backend
    "http://127.0.0.1:5000"                    # Fallback
]}})

# -----------------------------------------------------
# FUNÇÃO CENTRAL DE PROXY (Encaminhamento)
# -----------------------------------------------------

def proxy_to_backend(endpoint, method, data=None, headers=None):
    """Encaminha requisições para o backend real usando a biblioteca 'requests'."""
    url = f"{BACKEND_URL}{endpoint}"
    
    # Prepara os headers a enviar para o backend
    proxy_headers = {
        'Content-Type': request.headers.get('Content-Type', 'application/json'),
        'User-Agent': 'Railway-Proxy/1.0',
    }
    # Adiciona/Substitui quaisquer headers passados
    if headers:
        proxy_headers.update(headers)
        
    print(f"🔀 Encaminhando {method} {url}...")

    try:
        # Fazer a requisição para o backend
        response = requests.request(
            method=method,
            url=url,
            headers=proxy_headers,
            data=data, # O corpo da requisição POST/PUT
            timeout=30 # Timeout para evitar requisições presas
        )

        # Criar a resposta do Flask com o conteúdo e status do backend
        flask_response = make_response(response.content, response.status_code)
        
        # Copia todos os headers do backend para o cliente (incluindo CORS)
        for key, value in response.headers.items():
            # Evitar headers que o Flask ou o Gunicorn podem querer gerenciar
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
# ROTAS DO PROXY (Rotas configuradas pelo seu frontend)
# -----------------------------------------------------

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Rota de Healthcheck. O Railway usa isto para verificar se a app está OK (Status 200).
    """
    # Adiciona um teste simples de conexão com o backend
    try:
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
    }), 200 # Retorna 200 OK

# 🔥 CORREÇÃO CRÍTICA (2): ADICIONAR ROTA DE LOGIN
@app.route('/api/auth/callback', methods=['POST'])
def google_auth_callback_route():
    """
    Rota para receber o token do Google (via POST do Frontend) e encaminhar
    para o Backend para validação.
    """
    return proxy_to_backend(
        endpoint='/api/auth/callback',
        method='POST',
        data=request.data
    )

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    """Rota POST para encaminhar para /api/process-analysis (ou /api/analyze)."""
    # O Flask cuida de obter o body (request.data)
    return proxy_to_backend(
        endpoint='/api/analyze', # Ajustei para /api/analyze que é a rota do backend_app.py
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
# COMANDO DE INICIALIZAÇÃO (DEV - Ignorado pelo Gunicorn)
# -----------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Para deploy, o Gunicorn usará 0.0.0.0 e a porta $PORT
    print(f"🌐 Servidor Proxy Flask rodando em http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
