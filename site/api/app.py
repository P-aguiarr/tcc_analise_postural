# site/api/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis():
    try:
        logger.info("🎬 INICIANDO PROCESSAMENTO NO VERCEL")
        
        # Verificar tamanho do conteúdo
        content_length = request.content_length or 0
        max_size = 4.5 * 1024 * 1024  # 4.5MB
        
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
        
        # Processar arquivos (simulação no Vercel)
        if frontal_file and frontal_file.filename:
            file_size = len(frontal_file.read())
            frontal_file.seek(0)  # Reset para leitura futura
            logger.info(f"✅ Frontal recebido - {file_size} bytes")
            uploaded_files.append('frontal')
        
        if transversal_file and transversal_file.filename:
            file_size = len(transversal_file.read())
            transversal_file.seek(0)
            logger.info(f"✅ Transversal recebido - {file_size} bytes")
            uploaded_files.append('transversal')
        
        # Simular análise (Vercel não suporta OpenCV)
        result_data = {
            'analysis_id': analysis_id,
            'uploaded_files': uploaded_files,
            'videos': generate_video_urls(analysis_id, uploaded_files),
            'metrics': generate_metrics(uploaded_files),
            'environment': 'vercel',
            'limitation': 'Processamento simulado - Vercel não suporta OpenCV/MediaPipe',
            'file_sizes': {
                'frontal': len(frontal_file.read()) if frontal_file else 0,
                'transversal': len(transversal_file.read()) if transversal_file else 0
            }
        }
        
        logger.info("🎉 PROCESSAMENTO SIMULADO CONCLUÍDO!")
        
        return jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"💥 ERRO: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_video_urls(analysis_id, uploaded_files):
    videos = {}
    if 'frontal' in uploaded_files:
        videos['frontal_original'] = f'/api/videos/{analysis_id}_frontal.mp4'
        videos['frontal_processed'] = f'/api/videos/{analysis_id}_frontal_processed.mp4'
    if 'transversal' in uploaded_files:
        videos['transversal_original'] = f'/api/videos/{analysis_id}_transversal.mp4'
        videos['transversal_processed'] = f'/api/videos/{analysis_id}_transversal_processed.mp4'
    return videos

def generate_metrics(uploaded_files):
    return {
        'posture_score': 78,
        'symmetry_score': 85,
        'gait_quality': 72 if 'transversal' in uploaded_files else 0,
        'overall_health': 80,
        'note': 'Métricas simuladas - Vercel'
    }

@app.route('/api/analysis/<analysis_id>')
def get_analysis(analysis_id):
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
        },
        'environment': 'vercel'
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'environment': 'vercel', 
        'max_file_size': '4MB',
        'limitation': 'Simulação apenas - sem OpenCV'
    })

# Handler para Vercel
def handler(request):
    from flask import make_response
    with app.app_context():
        response = make_response()
        response = app.full_dispatch_request()
        return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
