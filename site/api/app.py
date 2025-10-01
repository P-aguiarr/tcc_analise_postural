# site/api/app.py - VERSÃO SUPER SIMPLES
from flask import Flask, jsonify
import datetime

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*') 
    response.headers.add('Access-Control-Allow-Methods', '*')
    return response

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Funcionando!',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/process-analysis', methods=['POST', 'OPTIONS'])  
def process():
    if request.method == 'OPTIONS':
        return '', 200
        
    return jsonify({
        'success': True,
        'message': 'Upload recebido!'
    })

def handler(request):
    with app.app_context():
        return app.full_dispatch_request()

if __name__ == '__main__':
    app.run()
