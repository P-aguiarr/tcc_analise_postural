# site/api/app.py
from flask import Flask, request, jsonify
import os
import json
from datetime import datetime
import logging
import sys

# Configurar logging para ver no Vercel
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS simples
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', '*')
    return response

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    try:
        logger.info("🔍 Health check chamado")
        
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
            
        return jsonify({
            'status': 'healthy',
            'environment': 'vercel',
            'python_version': sys.version,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"💥 Erro no health check: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-analysis', methods=['POST', 'OPTIONS'])
def process_analysis():
    try:
        logger.info("🎬 INICIANDO PROCESSAMENTO")
        
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
            
        logger.info(f"📦 Headers: {dict(request.headers)}")
        logger.info(f"📦 Content-Type: {request.content_type}")
        logger.info(f"📦 Content-Length: {request.content_length}")
        
        # Verificar se tem files
        if not request.files:
            logger.error("❌ Nenhum arquivo recebido")
            return jsonify({'success': False, 'error': 'Nenhum arquivo recebido'}), 400
        
        files_info = {key: file.filename for key, file in request.files.items() if file.filename}
        logger.info(f"📹 Arquivos recebidos: {files_info}")
        
        frontal_file = request.files.get('video_frontal')
        transversal_file = request.files.get('video_transversal')
        
        logger.info(f"📹 Frontal: {frontal_file.filename if frontal_file else 'None'}")
        logger.info(f"📹 Transversal: {transversal_file.filename if transversal_file else 'None'}")
        
        if not frontal_file and not transversal_file:
            logger.error("❌ Nenhum vídeo válido")
            return jsonify({'success': False, 'error': 'Nenhum vídeo válido enviado'}), 400
        
        # Verificar tamanho
        content_length = request.content_length or 0
        max_size = 4 * 1024 * 1024  # 4MB
        
        logger.info(f"📏 Tamanho do request: {content_length} bytes")
        
        if content_length > max_size:
            logger.error(f"❌ Arquivo muito grande: {content_length} bytes")
            return jsonify({
                'success': False, 
                'error': f'Arquivo muito grande ({content_length} bytes). Máximo: 4MB'
            }), 413
        
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        uploaded_files = []
        
        # Processar arquivos
        if frontal_file and frontal_file.filename:
            file_size = len(frontal_file.read())
            frontal_file.seek(0)  # Reset
            logger.info(f"✅ Frontal processado - {file_size} bytes")
            uploaded_files.append('frontal')
        
        if transversal_file and transversal_file.filename:
            file_size = len(transversal_file.read())
            transversal_file.seek(0)
            logger.info(f"✅ Transversal processado - {file_size} bytes")
            uploaded_files.append('transversal')
        
        logger.info(f"📋 Arquivos processados: {uploaded_files}")
        
        # Gerar resposta
        videos = {}
        if 'frontal' in uploaded_files:
            videos['frontal_original'] = f'/api/videos/{analysis_id}_frontal.mp4'
            videos['frontal_processed'] = f'/api/videos/{analysis_id}_frontal_processed.mp4'
        
        if 'transversal' in uploaded_files:
            videos['transversal_original'] = f'/api/videos/{analysis_id}_transversal.mp4'
            videos['transversal_processed'] = f'/api/videos/{analysis_id}_transversal_processed.mp4'
        
        result_data = {
            'analysis_id': analysis_id,
            'uploaded_files': uploaded_files,
            'videos': videos,
            'metrics': {
                'posture_score': 78,
                'symmetry_score': 85,
                'gait_quality': 72 if 'transversal' in uploaded_files else 0,
                'overall_health': 80
            },
            'debug': {
                'environment': 'vercel',
                'file_sizes': {
                    'frontal': len(frontal_file.read()) if frontal_file else 0,
                    'transversal': len(transversal_file.read()) if transversal_file else 0
                }
            }
        }
        
        logger.info("🎉 PROCESSAMENTO CONCLUÍDO!")
        
        return jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"💥 ERRO NO PROCESSAMENTO: {str(e)}")
        import traceback
        logger.error(f"📝 Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/analysis/<analysis_id>', methods=['GET', 'OPTIONS'])
def get_analysis(analysis_id):
    try:
        logger.info(f"📂 Buscando análise: {analysis_id}")
        
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
            
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
        logger.error(f"❌ Erro ao buscar análise: {str(e)}")
        return jsonify({'error': str(e)}), 404

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
