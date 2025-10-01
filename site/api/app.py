# site/api/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import subprocess
import sys
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 CORS CONFIGURADO PARA O VERCEL 🔥
CORS(app, origins=[
    "https://ttc-analise-postural.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
])

# Configurações
UPLOAD_FOLDER = '/tmp/uploads'  # 🔥 No Vercel usa /tmp
RESULTS_FOLDER = '/tmp/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis():
    try:
        logger.info("🎬 ========== INICIANDO PROCESSAMENTO NO VERCEL ==========")
        logger.info(f"📦 Headers: {dict(request.headers)}")
        logger.info(f"📦 Files: {list(request.files.keys())}")
        
        # Verificar se tem arquivos
        if not request.files:
            logger.error("❌ Nenhum arquivo recebido")
            return jsonify({'success': False, 'error': 'Nenhum arquivo recebido'}), 400
        
        frontal_file = request.files.get('video_frontal')
        transversal_file = request.files.get('video_transversal')
        
        logger.info(f"📹 Frontal file: {frontal_file.filename if frontal_file else 'None'}")
        logger.info(f"📹 Transversal file: {transversal_file.filename if transversal_file else 'None'}")
        
        if not frontal_file and not transversal_file:
            logger.error("❌ Nenhum vídeo válido enviado")
            return jsonify({'success': False, 'error': 'Nenhum vídeo válido enviado'}), 400
        
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        uploaded_files = []
        file_paths = {}
        
        # Processar vídeo frontal
        if frontal_file and frontal_file.filename:
            frontal_path = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_frontal.mp4")
            logger.info(f"💾 Salvando frontal em: {frontal_path}")
            frontal_file.save(frontal_path)
            
            if os.path.exists(frontal_path):
                file_size = os.path.getsize(frontal_path)
                logger.info(f"✅ Frontal salvo - Tamanho: {file_size} bytes")
                uploaded_files.append('frontal')
                file_paths['frontal'] = frontal_path
        
        # Processar vídeo transversal
        if transversal_file and transversal_file.filename:
            transversal_path = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_transversal.mp4")
            logger.info(f"💾 Salvando transversal em: {transversal_path}")
            transversal_file.save(transversal_path)
            
            if os.path.exists(transversal_path):
                file_size = os.path.getsize(transversal_path)
                logger.info(f"✅ Transversal salvo - Tamanho: {file_size} bytes")
                uploaded_files.append('transversal')
                file_paths['transversal'] = transversal_path
        
        logger.info(f"📋 Arquivos processados: {uploaded_files}")
        
        # Simular análise (no Vercel não podemos rodar OpenCV)
        analysis_results = simulate_python_analysis(analysis_id, file_paths)
        
        result_data = {
            'analysis_id': analysis_id,
            'uploaded_files': uploaded_files,
            'file_paths': file_paths,
            'python_analysis': analysis_results,
            'videos': generate_video_urls(analysis_id, uploaded_files),
            'metrics': generate_metrics(uploaded_files),
            'debug_info': {
                'environment': 'vercel',
                'files_received': [f.filename for f in request.files.values() if f.filename],
                'files_saved': uploaded_files
            }
        }
        
        logger.info("🎉 PROCESSAMENTO CONCLUÍDO NO VERCEL!")
        
        return jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"💥 ERRO NO PROCESSAMENTO: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

def simulate_python_analysis(analysis_id, file_paths):
    """Simula a análise Python (no Vercel não roda OpenCV)"""
    logger.info("🔧 Simulando análise Python no Vercel")
    
    return {
        'status': 'simulated_vercel',
        'message': 'Análise simulada - Vercel não suporta OpenCV/MediaPipe',
        'graphs_generated': ['ombros', 'quadris', 'coluna', 'assimetrias']
    }

def generate_video_urls(analysis_id, uploaded_files):
    """Gera URLs para os vídeos"""
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
    metrics = {
        'posture_score': 78,
        'symmetry_score': 85,
        'overall_health': 80
    }
    
    if 'transversal' in uploaded_files:
        metrics['gait_quality'] = 72
    else:
        metrics['gait_quality'] = 0
    
    return metrics

@app.route('/api/analysis/<analysis_id>')
def get_analysis(analysis_id):
    """Retorna dados da análise"""
    try:
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
            }
        }
        
        return jsonify(analysis_data)
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar análise: {str(e)}")
        return jsonify({'error': str(e)}), 404

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'environment': 'vercel',
        'timestamp': datetime.now().isoformat()
    })

# 🔥 Handler para Vercel Functions
def handler(request):
    from flask import make_response
    
    with app.app_context():
        response = make_response()
        response = app.full_dispatch_request()
        return response

if __name__ == '__main__':
    logger.info("🚀 Servidor Flask rodando localmente...")
    app.run(debug=True, port=5000)
