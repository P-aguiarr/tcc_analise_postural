# site/api/app.py
from flask import Flask, request, jsonify
import os
import json
from datetime import datetime
import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ✅ CORS MANUAL (sem biblioteca externa)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    try:
        logger.info("🔍 Health check chamado")
        
        if request.method == 'OPTIONS':
            return '', 200
            
        return jsonify({
            'status': 'healthy', 
            'environment': 'vercel',
            'timestamp': datetime.now().isoformat(),
            'message': 'API funcionando!'
        })
        
    except Exception as e:
        logger.error(f"💥 Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-analysis', methods=['POST', 'OPTIONS'])
def process_analysis():
    try:
        logger.info("🎬 INICIANDO PROCESSAMENTO")
        
        if request.method == 'OPTIONS':
            return '', 200
            
        # Verificar arquivos
        if not request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo'}), 400
        
        frontal_file = request.files.get('video_frontal')
        
        if not frontal_file:
            return jsonify({'success': False, 'error': 'Vídeo frontal obrigatório'}), 400
        
        # Simular processamento
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result_data = {
            'analysis_id': analysis_id,
            'uploaded_files': ['frontal'],
            'videos': {
                'frontal_original': f'/api/videos/{analysis_id}_frontal.mp4',
                'frontal_processed': f'/api/videos/{analysis_id}_frontal_processed.mp4'
            },
            'metrics': {
                'posture_score': 78,
                'symmetry_score': 85,
                'gait_quality': 0,
                'overall_health': 80
            },
            'message': 'Processamento simulado - Vercel'
        }
        
        logger.info("🎉 PROCESSAMENTO CONCLUÍDO!")
        
        return jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"💥 ERRO: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/<analysis_id>', methods=['GET', 'OPTIONS'])
def get_analysis(analysis_id):
    try:
        if request.method == 'OPTIONS':
            return '', 200
            
        return jsonify({
            'analysis_id': analysis_id,
            'status': 'completed',
            'uploaded_files': ['frontal'],
            'videos': {
                'frontal_original': f'/api/videos/{analysis_id}_frontal.mp4',
                'frontal_processed': f'/api/videos/{analysis_id}_frontal_processed.mp4'
            },
            'metrics': {
                'posture_score': 78,
                'symmetry_score': 85,
                'gait_quality': 0,
                'overall_health': 80
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# ✅ Handler SIMPLES para Vercel
def handler(request):
    try:
        with app.app_context():
            return app.full_dispatch_request()
    except Exception as e:
        logger.error(f"💥 Handler error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
