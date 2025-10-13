# app.py - VERSÃO FINAL E DEFINITIVA

from flask import Flask, request, jsonify, make_response, send_from_directory
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
VIDEO_DIR = "/tmp/analysis_videos" # Diretório para vídeos processados
if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

print("✅ Backend Definitivo com Health Check - Pronto para Análise!")

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
    try:
        lm = landmarks[landmark_enum.value]
        return (lm.x * shape[1], lm.y * shape[0]) if lm.visibility > 0.5 else None
    except (IndexError, TypeError):
        return None

def analyze_video_complete(video_path, output_video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30
    
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

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
                
                try:
                    if all(points.get(p) for p in [mp_pose.PoseLandmark.LEFT_HIP, mp_pose.PoseLandmark.LEFT_SHOULDER, mp_pose.PoseLandmark.LEFT_ELBOW]):
                        frame_data["angulo_ombro_esquerdo"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.LEFT_SHOULDER], points[mp_pose.PoseLandmark.LEFT_ELBOW])
                    if all(points.get(p) for p in [mp_pose.PoseLandmark.RIGHT_HIP, mp_pose.PoseLandmark.RIGHT_SHOULDER, mp_pose.PoseLandmark.RIGHT_ELBOW]):
                        frame_data["angulo_ombro_direito"] = calcular_angulo(points[mp_pose.PoseLandmark.RIGHT_HIP], points[mp_pose.PoseLandmark.RIGHT_SHOULDER], points[mp_pose.PoseLandmark.RIGHT_ELBOW])
                    # (Adicionar validações similares para outros ângulos se necessário)
                    
                    frame_data["angulo_joelho_esquerdo"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.LEFT_KNEE], points[mp_pose.PoseLandmark.LEFT_ANKLE])
                    frame_data["angulo_joelho_direito"] = calcular_angulo(points[mp_pose.PoseLandmark.RIGHT_HIP], points[mp_pose.PoseLandmark.RIGHT_KNEE], points[mp_pose.PoseLandmark.RIGHT_ANKLE])
                    frame_data["assimetria_ombros_metros"] = abs(points[mp_pose.PoseLandmark.LEFT_SHOULDER][1] - points[mp_pose.PoseLandmark.RIGHT_SHOULDER][1]) / height
                except (TypeError, IndexError):
                    pass # Ignora o cálculo do frame se algum ponto chave estiver faltando

                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            temporal_data.append(frame_data)
            out.write(frame)
            frame_count += 1
    
    cap.release(); out.release()
    return temporal_data

# =================================================================
# ROTAS DA API
# =================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de health check para o Railway."""
    return jsonify({"status": "ok", "message": "Serviço está funcionando"}), 200

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

        output_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}.mp4")
        temporal_data = analyze_video_complete(video_path, output_video_path)

        full_result = { "success": True, "analysis_id": analysis_id, "data": { "temporal_data": temporal_data } }
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f: json.dump(full_result, f)
        
        print(f"✅ Análise {analysis_id} concluída. Dados e vídeo salvos.")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if video_path and os.path.exists(video_path): os.unlink(video_path)

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    try:
        if '..' in analysis_id or '/' in analysis_id: return jsonify({"success": False, "error": "ID inválido."}), 400
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        if not os.path.exists(result_filepath): return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        with open(result_filepath, 'r') as f: data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video/<analysis_id>', methods=['GET'])
def get_video_route(analysis_id):
    try:
        if '..' in analysis_id or '/' in analysis_id: return "ID inválido", 400
        video_filename = f"{analysis_id}.mp4"
        return send_from_directory(VIDEO_DIR, video_filename, as_attachment=False)
    except FileNotFoundError:
        return "Vídeo não encontrado.", 404
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
