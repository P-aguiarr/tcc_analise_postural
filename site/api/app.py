# site/api/app.py
import json
import os
import uuid
from datetime import datetime
import requests # Usaremos a biblioteca 'requests' para o proxy (mais moderna que urllib)

# Importações do Flask
from flask import Flask, jsonify, request, abort, make_response
from flask_cors import CORS

# 🔥 URL DO SEU BACKEND (Render.com ou outro serviço)
# É crucial que esta URL esteja correta.
BACKEND_URL = os.environ.get("BACKEND_URL", "https://seu-backend.onrender.com")

# 1. INICIALIZAR A APLICAÇÃO FLASK
app = Flask(__name__)
# Aplicar CORS globalmente, assim como o seu código original fazia
CORS(app)

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
            data=data,
            headers=proxy_headers,
            verify=True # Garantir segurança SSL
        )
        
        print(f"✅ Backend respondeu: {response.status_code}")
        
        # Cria a resposta para o cliente com o conteúdo e status do backend
        client_response = make_response(response.content, response.status_code)
        
        # Copia o Content-Type do backend
        client_response.headers['Content-Type'] = response.headers.get('Content-Type', 'application/json')
        
        # O CORS já está a ser gerido pela extensão CORS, mas podemos adicionar outros headers se necessário
        
        return client_response

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro no backend (HTTP): {e.response.status_code}")
        abort(make_response(jsonify(message=f"Backend Error: {str(e)}"), e.response.status_code))
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro no proxy (Conexão): {str(e)}")
        # Em caso de falha de conexão (503 Service Unavailable)
        abort(make_response(jsonify(message=f"Proxy Connection Error: {str(e)}"), 503))


# -----------------------------------------------------
# ROTAS FLASK (Substituindo os métodos do_GET/do_POST)
# -----------------------------------------------------

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Rota de Healthcheck. O Railway usa isto para verificar se a app está OK (Status 200).
    """
    return jsonify({
        "success": True,
        "message": "API Proxy Flask está funcionando",
        "backend_url": BACKEND_URL,
        "timestamp": datetime.now().isoformat()
    }), 200 # Retorna 200 OK

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    """Rota POST para encaminhar para /api/process-analysis."""
    # O Flask cuida de obter o body (request.data)
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
# COMANDO DE INICIALIZAÇÃO (NECESSÁRIO PARA TESTE LOCAL)
# -----------------------------------------------------

# Isto só será executado quando correr 'python app.py' localmente.
# O Gunicorn (no Railway) irá ignorar esta parte.
if __name__ == '__main__':
    # O Gunicorn irá usar o 0.0.0.0 e a porta de ambiente
    # Para testes locais, pode usar a porta 5000
    print("⚠️ A rodar em modo de desenvolvimento. Use 'gunicorn' em produção.")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
