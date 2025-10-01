# site/api/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 CORS para Vercel
CORS(app)

@app.route('/api/process-analysis', methods=['POST', 'OPTIONS'])
def process_analysis():
    try:
        logger.info("🎬 INICIANDO PROCESSAMENTO NO VERCEL")
        
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', '*')
            response.headers.add('Access-Control-Allow-Methods', '*')
            return response
        
        # Verificar tamanho (limite do Vercel: ~4.5MB)
        content_length = request.content_length or 0
        max_size = 4 * 1024 * 1024  # 4MB
        
        logger.info(f"📦 Tamanho do request: {content_length} bytes")
        
        if content_length > max_size:
            logger.error(f"❌ Arquivo muito grande: {content_length} bytes")
            return jsonify({
                'success': False, 
                'error': f'Arquivo muito grande ({content_length} bytes). Máximo: 4MB',
                'max_size': max_size,
                'received_size': content_length
            }), 413
        
        if not request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo recebido'}), 400
        
        frontal_file = request.files.get('video_frontal')
        transversal_file = request.files.get('video_transversal')
        
        logger.info(f"📹 Frontal: {frontal_file.filename if frontal_file else 'None'}")
        logger.info(f"📹 Transversal: {transversal_file.filename if transversal_file else 'None'}")
        
        if not frontal_file and not transversal_file:
            return jsonify({'success': False, 'error': 'Nenhum vídeo válido enviado'}), 400
        
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        uploaded_files = []
        
        # Simular processamento (Vercel não suporta OpenCV)
        if frontal_file and frontal_file.filename:
            file_size = len(frontal_file.read())
            frontal_file.seek(0)
            logger.info(f"✅ Frontal recebido - {file_size} bytes")
            uploaded_files.append('frontal')
        
        if transversal_file and transversal_file.filename:
            file_size = len(transversal_file.read())
            transversal_file.seek(0)
            logger.info(f"✅ Transversal recebido - {file_size} bytes")
            uploaded_files.append('transversal')
        
        # Resultados simulados
        result_data = {
            'analysis_id': analysis_id,
            'uploaded_files': uploaded_files,
            'videos': generate_video_urls(analysis_id, uploaded_files),
            'metrics': generate_metrics(uploaded_files),
            'environment': 'vercel',
            'limitation': 'Processamento simulado - Vercel não suporta OpenCV/MediaPipe para análise postural real'
        }
        
        logger.info("🎉 PROCESSAMENTO SIMULADO CONCLUÍDO!")
        
        response = jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        logger.error(f"💥 ERRO: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

def generate_video_urls(analysis_id, uploaded_files):
    """Gera URLs simuladas para os vídeos"""
    videos = {}
    if 'frontal' in uploaded_files:
        videos['frontal_original'] = f'/api/videos/{analysis_id}_frontal.mp4'
        videos['frontal_processed'] = f'/api/videos/{analysis_id}_frontal_processed.mp4'
    if 'transversal' in uploaded_files:
        videos['transversal_original'] = f'/api/videos/{analysis_id}_transversal.mp4'
        videos['transversal_processed'] = f'/api/videos/{analysis_id}_transversal_processed.mp4'
    return videos

def generate_metrics(uploaded_files):
    """Gera métricas simuladas"""
    return {
        'posture_score': 78,
        'symmetry_score': 85,
        'gait_quality': 72 if 'transversal' in uploaded_files else 0,
        'overall_health': 80,
        'note': 'Métricas simuladas - Para análise real use Railway/Render com OpenCV'
    }

@app.route('/api/analysis/<analysis_id>', methods=['GET', 'OPTIONS'])
def get_analysis(analysis_id):
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        logger.info(f"📂 Buscando análise: {analysis_id}")
        
        analysis_data = {
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
            },
            'environment': 'vercel'
        }
        
        response = jsonify(analysis_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 404

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    response = jsonify({
        'status': 'healthy',
        'environment': 'vercel',
        'timestamp': datetime.now().isoformat(),
        'limitation': 'Arquivos máx: 4MB | Processamento: simulado'
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/api/debug/info', methods=['GET', 'OPTIONS'])
def debug_info():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    response = jsonify({
        'environment': 'vercel',
        'python_version': '3.9',
        'limitation': 'Análise postural simulada - Sem OpenCV/MediaPipe'
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# Handler para Vercel
def handler(request):
    from flask import make_response
    with app.app_context():
        response = make_response()
        response = app.full_dispatch_request()
        return response

if __name__ == '__main__':
    logger.info("🚀 Servidor Flask local...")
    app.run(debug=True, port=5000)
