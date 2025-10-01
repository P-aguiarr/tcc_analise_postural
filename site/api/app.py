# site/api/app.py
from flask import Flask, request, jsonify, send_file, send_from_directory
import subprocess
import os
import json
import pandas as pd
from datetime import datetime
import sys
import base64

# Adicionar o caminho para a análise postural
sys.path.append('../analise postural')

app = Flask(__name__)

# Diretórios
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis():
    try:
        # Salvar arquivos enviados
        frontal_file = request.files.get('video_frontal')
        transversal_file = request.files.get('video_transversal')
        
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Salvar vídeos
        frontal_path = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_frontal.mp4")
        transversal_path = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_transversal.mp4")
        
        if frontal_file:
            frontal_file.save(frontal_path)
        
        if transversal_file:
            transversal_file.save(transversal_path)
        
        # Executar análise (simulação por enquanto)
        result_data = simulate_analysis(analysis_id, frontal_path, transversal_path)
        
        return jsonify({
            'success': True,
            'analysisId': analysis_id,
            'data': result_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def simulate_analysis(analysis_id, frontal_path, transversal_path):
    """Simula a análise e retorna dados de exemplo"""
    
    # Aqui você integraria com o analise_completa.py real
    # Por enquanto, retornamos dados de exemplo
    
    return {
        'analysis_id': analysis_id,
        'status': 'completed',
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
        'graphs': {
            'ombros': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
            'quadris': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
            'coluna': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
            'assimetrias': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        },
        'detailed_analysis': {
            'angulos': {
                'ombro_esquerdo': {'media': 45, 'variacao': 15},
                'ombro_direito': {'media': 43, 'variacao': 12},
                'quadril_esquerdo': {'media': 25, 'variacao': 8},
                'quadril_direito': {'media': 26, 'variacao': 7}
            },
            'assimetrias': {
                'ombros': 0.02,
                'quadris': 0.01,
                'joelhos': 0.03
            },
            'recomendacoes': [
                'Fortalecimento do core',
                'Alongamento de isquiotibiais',
                'Exercícios de equilíbrio'
            ]
        }
    }

@app.route('/api/analysis/<analysis_id>')
def get_analysis(analysis_id):
    """Retorna dados da análise específica"""
    try:
        # Aqui você carregaria os dados reais do arquivo salvo
        analysis_file = os.path.join(RESULTS_FOLDER, f"{analysis_id}.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r') as f:
                data = json.load(f)
        else:
            # Retorna dados de exemplo
            data = simulate_analysis(analysis_id, None, None)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/videos/<video_name>')
def get_video(video_name):
    """Serve vídeos processados"""
    try:
        return send_from_directory(RESULTS_FOLDER, video_name)
    except:
        # Retorna vídeo placeholder
        return send_file('placeholder_video.mp4', mimetype='video/mp4')

@app.route('/api/graphs/<graph_name>')
def get_graph(graph_name):
    """Serve gráficos específicos"""
    try:
        return send_from_directory(RESULTS_FOLDER, f"{graph_name}.png")
    except:
        return jsonify({'error': 'Graph not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
