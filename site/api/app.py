# app.py - VERSÃO FINAL COM PERSISTÊNCIA DE ARQUIVOS

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import uuid
from datetime import datetime
import base64
import os
import tempfile
import math
import cv2
import mediapipe as mp
import numpy as np
import json # Importamos a biblioteca JSON

app = Flask(__name__)

# =================================================================
# CONFIGURAÇÃO DO CORS
# =================================================================
CORS(app, resources={r"/api/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",
    "http://localhost:8080", "http://127.0.0.1:5000", "http://localhost:5000"
], "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"], "supports_credentials": True }})

# --- Diretório para salvar os resultados temporários ---
# Usamos /tmp que é um diretório padrão em ambientes Linux (como o do Railway)
RESULT_DIR = "/tmp/analysis_results"
if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)

print("✅ Serviço Unificado Final - Com Persistência de Resultados!")

@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        headers = { 'Access-Control-Allow-Origin': request.headers.get('Origin'), 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' }
        return make_response('', 204, headers)

# =================================================================
# FUNÇÕES DE ANÁLISE POSTURAL COMPLETAS
# =================================================================

# Inicialização do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calcular_angulo(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0: angle = 360 - angle
    return angle

def get_landmark_coords(landmarks, landmark_enum, frame_shape):
    if not landmarks: return None
    lm = landmarks[landmark_enum.value]
    return (lm.x * frame_shape[1], lm.y * frame_shape[0])

def analyze_video_complete(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    temp_output_path = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

    temporal_data = []
    frame_count = 0

    with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                shape = frame.shape
                l_shoulder = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
                r_shoulder = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
                l_hip = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_HIP, shape)
                r_hip = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_HIP, shape)
                l_knee = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_KNEE, shape)
                r_knee = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_KNEE, shape)
                l_ankle = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE, shape)
                r_ankle = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
                nose = get_landmark_coords(landmarks, mp_pose.PoseLandmark.NOSE, shape)
                
                if all([l_shoulder, r_shoulder, l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle]):
                    frame_data["angulo_ombro_esquerdo"] = calcular_angulo(l_hip, l_shoulder, l_knee)
                    frame_data["angulo_ombro_direito"] = calcular_angulo(r_hip, r_shoulder, r_knee)
                    frame_data["angulo_quadril_esquerdo"] = calcular_angulo(l_shoulder, l_hip, l_knee)
                    frame_data["angulo_quadril_direito"] = calcular_angulo(r_shoulder, r_hip, r_knee)
                    frame_data["angulo_joelho_esquerdo"] = calcular_angulo(l_hip, l_knee, l_ankle)
                    frame_data["angulo_joelho_direito"] = calcular_angulo(r_hip, r_knee, r_ankle)
                    frame_data["assimetria_ombros_metros"] = abs(l_shoulder[1] - r_shoulder[1]) / height
                    frame_data["assimetria_quadris_metros"] = abs(l_hip[1] - r_hip[1]) / height
                    frame_data["LEFT_HIP_y_metros"] = l_hip[1] / height
                    frame_data["RIGHT_HIP_y_metros"] = r_hip[1] / height
                
                if all([nose, l_shoulder, r_shoulder, l_hip, r_hip]):
                    mid_shoulder = ((l_shoulder[0] + r_shoulder[0])/2, (l_shoulder[1] + r_shoulder[1])/2)
                    mid_hip = ((l_hip[0] + r_hip[0])/2, (l_hip[1] + r_hip[1])/2)
                    frame_data["angulo_coluna_cervical"] = calcular_angulo(mid_hip, mid_shoulder, nose)
                    frame_data["angulo_coluna_toracica"] = calcular_angulo(l_shoulder, mid_hip, r_shoulder)
                
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            temporal_data.append(frame_data)
            out.write(frame)
            frame_count += 1
    
    cap.release(); out.release()
    
    with open(temp_output_path, "rb") as video_file:
        video_base64 = base64.b64encode(video_file.read()).decode('utf-8')
    os.unlink(temp_output_path)
    return temporal_data, video_base64

def generate_static_recommendations(temporal_data):
    first_frame = next((frame for frame in temporal_data if "angulo_ombro_esquerdo" in frame), None)
    if not first_frame: return ["Não foi possível gerar recomendações."]
    recomendacoes = []
    if first_frame.get("assimetria_ombros_metros", 0) * 100 > 3:
        recomendacoes.append("Desnível dos ombros detectado. Considere exercícios para fortalecimento do trapézio.")
    if first_frame.get("angulo_coluna_cervical", 180) < 160:
        recomendacoes.append("Protrusão de cabeça detectada. Pratique exercícios de retração cervical.")
    if not recomendacoes:
        recomendacoes.append("Boa postura estática inicial detectada. Mantenha os hábitos saudáveis.")
    return list(set(recomendacoes))

# =================================================================
# ROTAS DA API
# =================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"success": True, "message": "Serviço está funcionando"}), 200

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    video_path = None
    try:
        if 'frontalImage' not in request.files: return jsonify({"success": False, "error": "Arquivo 'frontalImage' é obrigatório."}), 400
        video_file = request.files['frontalImage']
        _, ext = os.path.splitext(video_file.filename); ext = ext if ext else '.mp4'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext); video_path = temp_file.name
        video_file.save(video_path); temp_file.close()

        temporal_data, video_base64 = analyze_video_complete(video_path)
        recomendacoes = generate_static_recommendations(temporal_data)

        full_result = {
            "success": True, "message": "Análise concluída!", "analysis_id": analysis_id,
            "data": { "temporal_data": temporal_data, "video_processed_b64": video_base64, "recommendations": recomendacoes }
        }
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f: json.dump(full_result, f)
        
        print(f"✅ Análise {analysis_id} concluída e resultado salvo.")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return jsonify({"success": False, "error": f"Erro interno do servidor: {str(e)}"}), 500
    finally:
        if video_path and os.path.exists(video_path): os.unlink(video_path)

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    try:
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        if not os.path.exists(result_filepath): return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        
        with open(result_filepath, 'r') as f: data = json.load(f)
        
        print(f"✅ Resultado da análise {analysis_id} recuperado.")
        return jsonify(data)
    except Exception as e:
        print(f"❌ Erro ao recuperar {analysis_id}: {e}")
        return jsonify({"success": False, "error": "Erro ao recuperar dados da análise."}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
