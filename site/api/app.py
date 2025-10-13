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
CORS(app, resources={r"/api/*": {"origins": "https://ttc-analise-postural.vercel.app"}})

# Diretórios para salvar os resultados temporários
RESULT_DIR = "/tmp/analysis_results"
VIDEO_DIR = "/tmp/analysis_videos"
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print("✅ Backend Definitivo - Pronto para Análise!")

@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        headers = { 'Access-Control-Allow-Origin': request.headers.get('Origin'), 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' }
        return make_response('', 204, headers)

# =================================================================
# FUNÇÕES DE ANÁLISE POSTURAL
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
    if not cap.isOpened(): raise IOError(f"Não foi possível abrir: {video_path}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    temporal_data = []
    frame_count = 0
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
                    # Tenta calcular todos os pontos. Falhas são ignoradas para não quebrar o processo.
                    if all(points.get(p) for p in [mp_pose.PoseLandmark.LEFT_HIP, mp_pose.PoseLandmark.LEFT_SHOULDER, mp_pose.PoseLandmark.LEFT_KNEE]):
                        frame_data["angulo_quadril_esquerdo"] = calcular_angulo(points[mp_pose.PoseLandmark.LEFT_SHOULDER], points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.LEFT_KNEE])
                    if all(points.get(p) for p in [mp_pose.PoseLandmark.RIGHT_HIP, mp_pose.PoseLandmark.RIGHT_SHOULDER, mp_pose.PoseLandmark.RIGHT_KNEE]):
                        frame_data["angulo_quadril_direito"] = calcular_angulo(points[mp_pose.PoseLandmark.RIGHT_SHOULDER], points[mp_pose.PoseLandmark.RIGHT_HIP], points[mp_pose.PoseLandmark.RIGHT_KNEE])
                    
                    mid_shoulder = np.mean([points[mp_pose.PoseLandmark.LEFT_SHOULDER], points[mp_pose.PoseLandmark.RIGHT_SHOULDER]], axis=0)
                    mid_hip = np.mean([points[mp_pose.PoseLandmark.LEFT_HIP], points[mp_pose.PoseLandmark.RIGHT_HIP]], axis=0)
                    if all(p is not None for p in [mid_shoulder, mid_hip, points[mp_pose.PoseLandmark.NOSE]]):
                         frame_data["angulo_coluna_cervical"] = calcular_angulo(mid_hip, mid_shoulder, points[mp_pose.PoseLandmark.NOSE])

                    frame_data["assimetria_ombros_metros"] = abs(points[mp_pose.PoseLandmark.LEFT_SHOULDER][1] - points[mp_pose.PoseLandmark.RIGHT_SHOULDER][1]) / height
                    frame_data["LEFT_HIP_y_metros"] = points[mp_pose.PoseLandmark.LEFT_HIP][1] / height
                except (TypeError, IndexError, KeyError):
                    pass 

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
    return jsonify({"status": "ok"}), 200

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    frontal_video_path, transversal_video_path = None, None
    try:
        if 'frontalImage' not in request.files: return jsonify({"success": False, "error": "'frontalImage' é obrigatório."}), 400
        
        # Processa vídeo frontal
        frontal_file = request.files['frontalImage']
        ext_f = os.path.splitext(frontal_file.filename)[1] or '.mp4'
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext_f) as temp_f:
            frontal_video_path = temp_f.name
            frontal_file.save(frontal_video_path)
        output_frontal_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal.mp4")
        temporal_data_frontal = analyze_video_complete(frontal_video_path, output_frontal_video_path)

        # Processa vídeo transversal se existir
        temporal_data_transversal = None
        if 'transversalImage' in request.files:
            transversal_file = request.files['transversalImage']
            ext_t = os.path.splitext(transversal_file.filename)[1] or '.mp4'
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext_t) as temp_t:
                transversal_video_path = temp_t.name
                transversal_file.save(transversal_video_path)
            output_transversal_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_transversal.mp4")
            temporal_data_transversal = analyze_video_complete(transversal_video_path, output_transversal_video_path)

        full_result = { 
            "success": True, "analysis_id": analysis_id, 
            "data": { 
                "temporal_data_frontal": temporal_data_frontal,
                "temporal_data_transversal": temporal_data_transversal
            } 
        }
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f: json.dump(full_result, f)
        
        print(f"✅ Análise {analysis_id} concluída. Dados e vídeos salvos.")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if frontal_video_path and os.path.exists(frontal_video_path): os.unlink(frontal_video_path)
        if transversal_video_path and os.path.exists(transversal_video_path): os.unlink(transversal_video_path)

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    # ... (código mantido igual)
    try:
        if '..' in analysis_id or '/' in analysis_id: return jsonify({"success": False, "error": "ID inválido."}), 400
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        if not os.path.exists(result_filepath): return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        with open(result_filepath, 'r') as f: data = json.load(f)
        return jsonify(data)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video/<video_filename>', methods=['GET'])
def get_video_route(video_filename):
    # ... (código mantido igual)
    try:
        if '..' in video_filename or '/' in video_filename: return "Nome de arquivo inválido", 400
        return send_from_directory(VIDEO_DIR, video_filename, as_attachment=False)
    except FileNotFoundError: return "Vídeo não encontrado.", 404
    except Exception as e: return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
