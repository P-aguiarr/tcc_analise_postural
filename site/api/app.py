# site/api/app.py
from flask import Flask, request, jsonify, send_file, send_from_directory
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
CORS(app)

# Configurações
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis():
    try:
        logger.info("🎬 ========== INICIANDO PROCESSAMENTO ==========")
        logger.info(f"📦 Headers: {dict(request.headers)}")
        logger.info(f"📦 Files: {list(request.files.keys())}")
        logger.info(f"📦 Form: {list(request.form.keys())}")
        
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
            
            # Verificar se arquivo foi salvo
            if os.path.exists(frontal_path):
                file_size = os.path.getsize(frontal_path)
                logger.info(f"✅ Frontal salvo - Tamanho: {file_size} bytes")
                uploaded_files.append('frontal')
                file_paths['frontal'] = frontal_path
            else:
                logger.error("❌ Falha ao salvar arquivo frontal")
        
        # Processar vídeo transversal
        if transversal_file and transversal_file.filename:
            transversal_path = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_transversal.mp4")
            logger.info(f"💾 Salvando transversal em: {transversal_path}")
            transversal_file.save(transversal_path)
            
            # Verificar se arquivo foi salvo
            if os.path.exists(transversal_path):
                file_size = os.path.getsize(transversal_path)
                logger.info(f"✅ Transversal salvo - Tamanho: {file_size} bytes")
                uploaded_files.append('transversal')
                file_paths['transversal'] = transversal_path
            else:
                logger.error("❌ Falha ao salvar arquivo transversal")
        
        logger.info(f"📋 Arquivos processados: {uploaded_files}")
        
        # Executar análise Python
        analysis_results = execute_python_analysis(analysis_id, file_paths)
        
        result_data = {
            'analysis_id': analysis_id,
            'uploaded_files': uploaded_files,
            'file_paths': file_paths,
            'python_analysis': analysis_results,
            'videos': generate_video_urls(analysis_id, uploaded_files),
            'metrics': generate_metrics(uploaded_files),
            'debug_info': {
                'upload_folder': UPLOAD_FOLDER,
                'results_folder': RESULTS_FOLDER,
                'files_received': [f.filename for f in request.files.values() if f.filename],
                'files_saved': uploaded_files
            }
        }
        
        logger.info("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        return jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"💥 ERRO NO PROCESSAMENTO: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e),
            'debug_info': {
                'exception_type': type(e).__name__,
                'traceback': str(e.__traceback__)
            }
        }), 500

def execute_python_analysis(analysis_id, file_paths):
    """Executa o script Python de análise"""
    try:
        logger.info("🐍 INICIANDO EXECUÇÃO DO analise_completa.py")
        
        # Verificar se os arquivos existem
        for file_type, path in file_paths.items():
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                logger.info(f"📁 {file_type}: {path} ({file_size} bytes)")
            else:
                logger.error(f"❌ Arquivo não encontrado: {path}")
        
        # Construir comando para executar o script
        script_path = "../analise postural/analise_completa.py"
        
        # Verificar se o script existe
        if not os.path.exists(script_path):
            logger.warning("⚠️ Script analise_completa.py não encontrado, usando simulação")
            return {'status': 'simulated', 'reason': 'script_not_found'}
        
        # Preparar argumentos
        cmd = ["python", script_path]
        
        if 'frontal' in file_paths:
            cmd.extend(["--frontal", file_paths['frontal']])
        if 'transversal' in file_paths:
            cmd.extend(["--transversal", file_paths['transversal']])
        
        cmd.extend(["--output", os.path.join(RESULTS_FOLDER, analysis_id)])
        
        logger.info(f"🖥️ Executando comando: {' '.join(cmd)}")
        
        # Executar (por enquanto só simular)
        # result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Simular execução por enquanto
        logger.info("🔧 Execução do Python simulada (substituir por subprocess.run)")
        
        return {
            'status': 'simulated_success',
            'message': 'Análise simulada - integrar com subprocess.run depois',
            'graphs_generated': ['ombros', 'quadris', 'coluna', 'assimetrias']
        }
        
    except Exception as e:
        logger.error(f"❌ ERRO na execução Python: {str(e)}")
        return {'status': 'error', 'error': str(e)}

def generate_video_urls(analysis_id, uploaded_files):
    """Gera URLs para os vídeos processados"""
    videos = {}
    
    if 'frontal' in uploaded_files:
        videos['frontal_original'] = f'/api/videos/{analysis_id}_frontal.mp4'
        videos['frontal_processed'] = f'/api/videos/{analysis_id}_frontal_processed.mp4'
    
    if 'transversal' in uploaded_files:
        videos['transversal_original'] = f'/api/videos/{analysis_id}_transversal.mp4'
        videos['transversal_processed'] = f'/api/videos/{analysis_id}_transversal_processed.mp4'
    
    logger.info(f"🎥 URLs geradas: {list(videos.keys())}")
    return videos

def generate_metrics(uploaded_files):
    """Gera métricas baseadas nos arquivos enviados"""
    metrics = {
        'posture_score': 78,
        'symmetry_score': 85,
        'overall_health': 80
    }
    
    if 'transversal' in uploaded_files:
        metrics['gait_quality'] = 72
        metrics['march_analysis'] = 75
    else:
        metrics['gait_quality'] = 0
        metrics['march_analysis'] = 'Não disponível'
    
    logger.info(f"📊 Métricas geradas: {metrics}")
    return metrics

@app.route('/api/analysis/<analysis_id>')
def get_analysis(analysis_id):
    """Retorna dados da análise específica"""
    try:
        logger.info(f"📂 Buscando análise: {analysis_id}")
        
        # Simular dados (depois carregar do arquivo real)
        analysis_data = {
            'analysis_id': analysis_id,
            'status': 'completed',
            'uploaded_files': ['frontal', 'transversal'],  # Simulado
            'videos': {
                'frontal_original': f'/api/videos/{analysis_id}_frontal.mp4',
                'frontal_processed': f'/api/videos/{analysis_id}_frontal_processed.mp4',
                'transversal_original': f'/api/videos/{analysis_id}_transversal.mp4',
                'transversal_processed': f'/api/videos/{analysis_id}_transversal_processed.mp4'
            },
            'metrics': {
                'posture_score': 78,
                'symmetry_score': 85,
                'gait_quality': 72,
                'overall_health': 80
            },
            'debug': {
                'endpoint_called': f'/api/analysis/{analysis_id}',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return jsonify(analysis_data)
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar análise: {str(e)}")
        return jsonify({'error': str(e)}), 404

@app.route('/api/videos/<video_name>')
def get_video(video_name):
    """Serve vídeos processados"""
    try:
        logger.info(f"🎬 Servindo vídeo: {video_name}")
        return send_from_directory(UPLOAD_FOLDER, video_name)
    except Exception as e:
        logger.error(f"❌ Erro ao servir vídeo {video_name}: {str(e)}")
        return jsonify({'error': f'Vídeo não encontrado: {video_name}'}), 404

@app.route('/api/debug/info')
def debug_info():
    """Endpoint para informações de debug"""
    return jsonify({
        'upload_folder': UPLOAD_FOLDER,
        'results_folder': RESULTS_FOLDER,
        'upload_files': os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else [],
        'results_files': os.listdir(RESULTS_FOLDER) if os.path.exists(RESULTS_FOLDER) else [],
        'python_version': sys.version,
        'working_directory': os.getcwd()
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    logger.info("🚀 Iniciando servidor Flask...")
    logger.info(f"📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    logger.info(f"📁 Results folder: {os.path.abspath(RESULTS_FOLDER)}")
    logger.info(f"🐍 Python path: {sys.executable}")
    
    app.run(debug=True, port=5000, host='0.0.0.0')
