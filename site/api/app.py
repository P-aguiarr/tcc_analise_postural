from flask import Flask, request, jsonify, send_file
import subprocess
import os
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/processar-analise', methods=['POST'])
def processar_analise():
    try:
        data = request.json
        user_id = data.get('userId')
        video_frontal = data.get('videoFrontal')
        video_transversal = data.get('videoTransversal')
        
        # Gera ID único para a análise
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        
        # Executa o script Python de análise
        script_path = "analise postural/analise_completa.py"
        
        # Prepara os argumentos para o script
        cmd = [
            "python", script_path,
            "--frontal", video_frontal,
            "--transversal", video_transversal,
            "--output", f"results/{analysis_id}",
            "--user", user_id
        ]
        
        # Executa o script
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'analysisId': analysis_id,
                'message': 'Análise processada com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analysis/<analysis_id>')
def get_analysis_results(analysis_id):
    try:
        # Carrega os resultados da análise
        results_path = f"results/{analysis_id}/analysis_results.json"
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/videos/<video_name>')
def get_video(video_name):
    try:
        return send_file(f"results/videos/{video_name}")
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    # Cria diretório de resultados se não existir
    os.makedirs("results", exist_ok=True)
    app.run(debug=True)
