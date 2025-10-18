# site/api/app.py

import os
import uuid
import json
import tempfile
import traceback
import numpy as np
import cv2
import mediapipe as mp

# Importações de Flask
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Diretórios para armazenamento temporário de vídeos e resultados
BASE_DIR = tempfile.gettempdir()
RESULT_DIR = os.path.join(BASE_DIR, "analysis_results")
VIDEO_DIR = os.path.join(BASE_DIR, "analysis_videos")
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print(f"✅ Backend iniciado. Resultados em: {RESULT_DIR}, Vídeos em: {VIDEO_DIR}")

# Instâncias do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# --- CONFIGURAÇÃO DE VÍDEO ---
VIDEO_FOURCC = 'VP80' 
VIDEO_EXTENSION = '.webm'
VIDEO_MIN_SIZE_BYTES = 1000

# --- MATRIZ DE PRECISÃO E LÓGICA DE DECISÃO ---

# Define qual plano é otimizado (P1) para cada métrica
BIOMECHANICAL_PRIORITY_MATRIX = {
    'Angulos_Ombros': 'transversal',
    'Angulos_Quadris': 'transversal',
    'Angulos_Joelhos': 'transversal',
    'Angulo_Coluna': 'transversal',
    'Assimetria_Ombros': 'coronal',
    'Oscilacao_Vertical_Quadril': 'coronal',
    'Oscilacao_Horizontal_Quadril': 'coronal'
}

CONFIDENCE_THRESHOLD = 0.7 # Limite mínimo de confiança

def calculate_distribution_data(temporal_data):
    """
    Calcula dados agregados para gráficos de distribuição a partir dos dados temporais.
    """
    distribution_data = {}
    
    if not temporal_data:
        return distribution_data
    
    # Coleta todos os valores de cada métrica
    metrics_data = {}
    for frame in temporal_data:
        for key, value in frame.items():
            if key not in ['frame', 'tempo_segundos'] and isinstance(value, (int, float)):
                if key not in metrics_data:
                    metrics_data[key] = []
                metrics_data[key].append(value)
    
    # Distribuição de Ângulos (histograma)
    angle_metrics = ['angulo_ombro_esquerdo', 'angulo_ombro_direito', 
                    'angulo_quadril_esquerdo', 'angulo_quadril_direito',
                    'angulo_joelho_esquerdo', 'angulo_joelho_direito', 'angulo_coluna']
    
    all_angles = []
    for metric in angle_metrics:
        if metric in metrics_data:
            all_angles.extend(metrics_data[metric])
    
    if all_angles:
        hist, bins = np.histogram(all_angles, bins=20, range=(0, 180))
        distribution_data['distribuicao_angulos'] = {
            'histogram': hist.tolist(),
            'bins': bins.tolist()
        }
    
    # Histograma de Assimetrias
    asymmetry_metrics = ['assimetria_ombros_vertical']
    all_asymmetries = []
    for metric in asymmetry_metrics:
        if metric in metrics_data:
            all_asymmetries.extend(metrics_data[metric])
    
    if all_asymmetries:
        max_val = max(all_asymmetries) if all_asymmetries else 0.2
        hist, bins = np.histogram(all_asymmetries, bins=15, range=(0, max_val))
        distribution_data['histograma_assimetrias'] = {
            'histogram': hist.tolist(),
            'bins': bins.tolist()
        }
    
    return distribution_data

def apply_precision_matrix(analysis_data):
    """
    Seleciona a melhor fonte de dados (coronal ou transversal) para cada métrica
    baseado na matriz de prioridade e na confiança da detecção.
    """
    final_charts = {}
    coronal_data = analysis_data.get('coronal')
    transversal_data = analysis_data.get('transversal')
    
    coronal_confidence = coronal_data.get('confidence_score', 0) if coronal_data else 0
    transversal_confidence = transversal_data.get('confidence_score', 0) if transversal_data else 0

    available_sources = {}
    if coronal_data: available_sources['coronal'] = coronal_confidence
    if transversal_data: available_sources['transversal'] = transversal_confidence

    if not available_sources:
        return {} # Nenhum dado para processar

    # Determina a melhor fonte geral, caso a P1 falhe
    best_overall_source = max(available_sources, key=available_sources.get)

    for metric, p1_source in BIOMECHANICAL_PRIORITY_MATRIX.items():
        chosen_source = None
        
        # 1. Verifica se o plano otimizado (P1) está disponível e tem confiança suficiente
        if p1_source in available_sources and available_sources[p1_source] >= CONFIDENCE_THRESHOLD:
            chosen_source = p1_source
        # 2. Caso contrário, usa a melhor fonte disponível geral
        else:
            chosen_source = best_overall_source

        # Monta o objeto final para o gráfico
        if chosen_source:
            source_data_key = 'temporal_data'
            source_data_list = analysis_data[chosen_source][source_data_key]
            
            final_charts[metric] = {
                "source": chosen_source,
                "confidence": available_sources[chosen_source],
                "data": source_data_list
            }
            
    return final_charts

# --- FUNÇÕES DE ANÁLISE ---

def calculate_angle(a, b, c):
    """Calcula o ângulo entre 3 pontos (em graus)."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle

def analyze_video(video_path, output_video_path):
    """
    Processa um vídeo, extrai dados de postura e retorna os dados temporais
    junto com uma pontuação de confiança média.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    fourcc = cv2.VideoWriter_fourcc(*VIDEO_FOURCC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    temporal_data, confidence_scores = [], []
    frame_count = 0
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            
            frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                key_points = {
                    'l_shoulder': (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y),
                    'r_shoulder': (landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y),
                    'l_hip': (landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y),
                    'r_hip': (landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y),
                    'l_knee': (landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y),
                    'r_knee': (landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y),
                    'l_ankle': (landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y),
                    'r_ankle': (landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y),
                    'nose': (landmarks[mp_pose.PoseLandmark.NOSE.value].x, landmarks[mp_pose.PoseLandmark.NOSE.value].y)
                }
                
                frame_data['angulo_ombro_esquerdo'] = calculate_angle(key_points['l_hip'], key_points['l_shoulder'], key_points['nose'])
                frame_data['angulo_ombro_direito'] = calculate_angle(key_points['r_hip'], key_points['r_shoulder'], key_points['nose'])
                frame_data['angulo_quadril_esquerdo'] = calculate_angle(key_points['l_shoulder'], key_points['l_hip'], key_points['l_knee'])
                frame_data['angulo_quadril_direito'] = calculate_angle(key_points['r_shoulder'], key_points['r_hip'], key_points['r_knee'])
                frame_data['angulo_joelho_esquerdo'] = calculate_angle(key_points['l_hip'], key_points['l_knee'], key_points['l_ankle'])
                frame_data['angulo_joelho_direito'] = calculate_angle(key_points['r_hip'], key_points['r_knee'], key_points['r_ankle'])
                mid_shoulder = np.mean([key_points['l_shoulder'], key_points['r_shoulder']], axis=0)
                mid_hip = np.mean([key_points['l_hip'], key_points['r_hip']], axis=0)
                frame_data['angulo_coluna'] = calculate_angle(mid_hip, mid_shoulder, key_points['nose'])
                frame_data['assimetria_ombros_vertical'] = abs(key_points['l_shoulder'][1] - key_points['r_shoulder'][1])
                frame_data['oscilacao_vertical_quadril'] = mid_hip[1]
                frame_data['oscilacao_horizontal_quadril'] = mid_hip[0]
                
                temporal_data.append(frame_data)
                
                visibilities = [landmarks[i].visibility for i in range(len(landmarks))]
                confidence_scores.append(np.mean(visibilities))
                
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            out.write(frame)
            frame_count += 1
            
    cap.release()
    out.release()
    
    avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
    
    return {"temporal_data": temporal_data, "confidence_score": float(avg_confidence)}

# --- ROTAS DA API ---

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """Endpoint simples para verificação de saúde (health check)."""
    return jsonify({"status": "ok", "message": "Servidor de análise no ar."})

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    print(f"\nIniciando nova análise ID: {analysis_id}")
    
    video_coronal = request.files.get('video_coronal')
    video_transversal = request.files.get('video_transversal')

    if not video_coronal:
        return jsonify({"success": False, "error": "O vídeo do plano coronal é obrigatório."}), 400

    analysis_results = {"analysis_id": analysis_id, "analyzed_data": {}}

    try:
        # Processa Plano Coronal (Obrigatório)
        coronal_original_path = os.path.join(VIDEO_DIR, f"{analysis_id}_coronal_original.mp4")
        video_coronal.save(coronal_original_path)
        coronal_processed_filename = f"{analysis_id}_coronal{VIDEO_EXTENSION}"
        coronal_processed_path = os.path.join(VIDEO_DIR, coronal_processed_filename)
        coronal_analysis = analyze_video(coronal_original_path, coronal_processed_path)
        analysis_results["analyzed_data"]["coronal"] = {
            **coronal_analysis,
            "video_original": os.path.basename(coronal_original_path),
            "video_processed": coronal_processed_filename if os.path.exists(coronal_processed_path) and os.path.getsize(coronal_processed_path) > VIDEO_MIN_SIZE_BYTES else None
        }

        # Processa Plano Transversal (Opcional)
        if video_transversal:
            transversal_original_path = os.path.join(VIDEO_DIR, f"{analysis_id}_transversal_original.mp4")
            video_transversal.save(transversal_original_path)
            transversal_processed_filename = f"{analysis_id}_transversal{VIDEO_EXTENSION}"
            transversal_processed_path = os.path.join(VIDEO_DIR, transversal_processed_filename)
            transversal_analysis = analyze_video(transversal_original_path, transversal_processed_path)
            analysis_results["analyzed_data"]["transversal"] = {
                **transversal_analysis,
                "video_original": os.path.basename(transversal_original_path),
                "video_processed": transversal_processed_filename if os.path.exists(transversal_processed_path) and os.path.getsize(transversal_processed_path) > VIDEO_MIN_SIZE_BYTES else None
            }

        # Aplica a matriz de decisão para gráficos temporais
        analysis_results["final_charts"] = apply_precision_matrix(analysis_results["analyzed_data"])
        
        # Calcula dados de distribuição a partir do melhor plano
        best_source = 'coronal'
        if analysis_results["analyzed_data"].get('transversal') and analysis_results["analyzed_data"]['transversal'].get('confidence_score', 0) > analysis_results["analyzed_data"]['coronal'].get('confidence_score', 0):
            best_source = 'transversal'
        
        best_temporal_data = analysis_results["analyzed_data"][best_source]['temporal_data']
        analysis_results["distribution_data"] = calculate_distribution_data(best_temporal_data)
        
        # Salva o resultado final
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump({"success": True, "data": analysis_results}, f)
        
        print(f"✅ Análise {analysis_id} concluída.")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Erro crítico na análise {analysis_id}: {e}\n{error_trace}")
        return jsonify({"success": False, "error": f"Erro interno: {e}", "details": error_trace}), 500

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    """Serve o arquivo JSON com os dados da análise."""
    try:
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        if not os.path.exists(result_filepath):
            return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        with open(result_filepath, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video/<video_filename>', methods=['GET'])
def get_video_route(video_filename):
    """Serve os arquivos de vídeo com o Content-Type correto."""
    try:
        if not os.path.normpath(os.path.join(VIDEO_DIR, video_filename)).startswith(os.path.realpath(VIDEO_DIR)):
            abort(403)

        mimetype = 'video/webm' if video_filename.endswith('.webm') else 'video/mp4'
        response = send_from_directory(VIDEO_DIR, video_filename, mimetype=mimetype, as_attachment=False)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        print(f"❌ Erro ao servir vídeo '{video_filename}': {e}")
        abort(500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
