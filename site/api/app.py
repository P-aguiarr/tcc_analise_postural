# app.py - VERSÃO FINAL E DEFINITIVA

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
import json

app = Flask(__name__)

# CONFIGURAÇÃO DO CORS
CORS(app, resources={r"/api/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",
    "http://localhost:8080", "http://127.0.0.1:5000", "http://localhost:5000"
], "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# Diretório para salvar os resultados temporários
RESULT_DIR = "/tmp/analysis_results"
if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)

print("✅ Backend Definitivo - Pronto para Análise!")

@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        headers = { 'Access-Control-Allow-Origin': request.headers.get('Origin'), 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' }
        return make_response('', 204, headers)

# =================================================================
# FUNÇÕES DE ANÁLISE POSTURAL (COMPLETAS)
# =================================================================
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    return 360 - angle if angle > 180.0 else angle

def get_landmark_coords(landmarks, landmark_enum, shape):
    lm = landmarks[landmark_enum.value]
    return (lm.x * shape[1], lm.y * shape[0]) if lm.visibility > 0.5 else None

def analyze_video_complete(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    temp_output_path = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps, width, height = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

    temporal_data = []
    frame_count = 0
    total_distance = 0
    last_hip_center_x = None

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}
            
            if results.pose_landmarks:
                landmarks, shape = results.pose_landmarks.landmark, frame.shape
                points = {lm: get_landmark_coords(landmarks, lm, shape) for lm in mp_pose.PoseLandmark}
                
                if all(points.values()):
                    frame_data["angulo_ombro_esquerdo"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.LEFT_SHOULDER], points[mp_pose.PoseLandmark.LEFT_ELBOW])
                    frame_data["angulo_ombro_direito"] = calcular_angulo(points[mp_pose.PoseLandmark.RIGHT_HIP], points[mp_pose.PoseLandmark.RIGHT_SHOULDER], points[mp_pose.PoseLandmark.RIGHT_ELBOW])
                    frame_data["angulo_quadril_esquerdo"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_SHOULDER], points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.LEFT_KNEE])
                    frame_data["angulo_quadril_direito"] = calcular_angulo(points[mp_pose.PoseLandmark.RIGHT_SHOULDER], points[mp_pose.PoseLandmark.RIGHT_HIP], points[mp_pose.PoseLandmark.RIGHT_KNEE])
                    frame_data["angulo_joelho_esquerdo"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.LEFT_KNEE], points[mp_pose.PoseLandmark.LEFT_ANKLE])
                    frame_data["angulo_joelho_direito"] = calcular_angulo(points[mp_pose.PoseLandmark.RIGHT_HIP], points[mp_pose.PoseLandmark.RIGHT_KNEE], points[mp_pose.PoseLandmark.RIGHT_ANKLE])
                    
                    frame_data["assimetria_ombros_metros"] = abs(points[mp_pose.PoseLandmark.LEFT_SHOULDER][1] - points[mp_pose.PoseLandmark.RIGHT_SHOULDER][1]) / height
                    frame_data["assimetria_quadris_metros"] = abs(points[mp_pose.PoseLandmark.LEFT_HIP][1] - points[mp_pose.PoseLandmark.RIGHT_HIP][1]) / height

                    frame_data["LEFT_HIP_y_metros"] = points[mp_pose.PoseLandmark.LEFT_HIP][1] / height
                    frame_data["RIGHT_HIP_y_metros"] = points[mp_pose.PoseLandmark.RIGHT_HIP][1] / height

                    mid_shoulder = np.mean([points[mp_pose.PoseLandmark.LEFT_SHOULDER], points[mp_pose.PoseLandmark.RIGHT_SHOULDER]], axis=0)
                    mid_hip = np.mean([points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.RIGHT_HIP]], axis=0)
                    frame_data["angulo_coluna_cervical"] = calcular_angulo(mid_hip, mid_shoulder, points[mp_pose.PoseLandmark.NOSE])
                    frame_data["angulo_coluna_toracica"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_SHOULDER], mid_hip, points[mp_pose.PoseLandmark.RIGHT_SHOULDER])

                    current_hip_center_x = mid_hip[0]
                    if last_hip_center_x is not None: total_distance += abs(current_hip_center_x - last_hip_center_x)
                    last_hip_center_x = current_hip_center_x
                    frame_data["distancia_percorrida_metros"] = total_distance / width # Normalizado pela largura

                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            temporal_data.append(frame_data)
            out.write(frame)
            frame_count += 1
    
    cap.release(); out.release()
    
    with open(temp_output_path, "rb") as vf: video_base64 = base64.b64encode(vf.read()).decode('utf-8')
    os.unlink(temp_output_path)
    return temporal_data, video_base64

# =================================================================
# ROTAS DA API
# =================================================================

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    video_path = None
    try:
        if 'frontalImage' not in request.files: return jsonify({"success": False, "error": "'frontalImage' é obrigatório."}), 400
        video_file = request.files['frontalImage']
        ext = os.path.splitext(video_file.filename)[1] or '.mp4'
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            video_path = temp_file.name
            video_file.save(video_path)

        temporal_data, video_base64 = analyze_video_complete(video_path)

        full_result = { "success": True, "analysis_id": analysis_id, "data": { "temporal_data": temporal_data, "video_processed_b64": video_base64 } }
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f: json.dump(full_result, f)
        
        print(f"✅ Análise {analysis_id} concluída e salva.")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
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
