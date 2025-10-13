# app.py - VERSÃO FINAL COM CORREÇÃO DE MEDIAPIPE

from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
import uuid
import os
import tempfile
import math
import cv2
import mediapipe as mp
import numpy as np
import json

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "https://ttc-analise-postural.vercel.app"}})

RESULT_DIR = "/tmp/analysis_results"
VIDEO_DIR = "/tmp/analysis_videos"
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print("✅ Backend Definitivo v2 - Pronto para Análise!")

@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        headers = { 'Access-Control-Allow-Origin': request.headers.get('Origin'), 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' }
        return make_response('', 204, headers)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calcular_angulo(a, b, c):
    if a is None or b is None or c is None: return None
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    return 360 - angle if angle > 180.0 else angle

def get_landmark_coords(landmarks, landmark_enum, shape):
    try:
        lm = landmarks[landmark_enum.value]
        return (lm.x * shape[1], lm.y * shape[0]) if lm.visibility > 0.5 else None
    except:
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
    detection_success_count = 0

    # CORREÇÃO CRÍTICA: Adicionado static_image_mode=True para forçar o uso da CPU
    with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            
            frame_data = { "frame": frame_count, "tempo_segundos": frame_count / fps, "angulo_ombro_esquerdo": None, "angulo_joelho_esquerdo": None, "assimetria_ombros_metros": None }
            
            if results.pose_landmarks:
                detection_success_count += 1
                landmarks, shape = results.pose_landmarks.landmark, frame.shape
                points = {lm: get_landmark_coords(landmarks, lm, shape) for lm in mp_pose.PoseLandmark}
                
                frame_data["angulo_ombro_esquerdo"] = calcular_angulo(points.get(mp_pose.PoseLandmark.LEFT_HIP), points.get(mp_pose.PoseLandmark.LEFT_SHOULDER), points.get(mp_pose.PoseLandmark.LEFT_ELBOW))
                frame_data["angulo_joelho_esquerdo"] = calcular_angulo(points.get(mp_pose.PoseLandmark.LEFT_HIP), points.get(mp_pose.PoseLandmark.LEFT_KNEE), points.get(mp_pose.PoseLandmark.LEFT_ANKLE))
                
                if points.get(mp_pose.PoseLandmark.LEFT_SHOULDER) and points.get(mp_pose.PoseLandmark.RIGHT_SHOULDER):
                    frame_data["assimetria_ombros_metros"] = abs(points[mp_pose.PoseLandmark.LEFT_SHOULDER][1] - points[mp_pose.PoseLandmark.RIGHT_SHOULDER][1]) / height

                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            temporal_data.append(frame_data)
            out.write(frame)
            frame_count += 1
    
    cap.release(); out.release()
    print(f"Análise de vídeo concluída. {detection_success_count} de {frame_count} frames tiveram detecção.")
    return temporal_data

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    video_path = None
    try:
        if 'frontalImage' not in request.files: return jsonify({"success": False, "error": "Arquivo 'frontalImage' é obrigatório."}), 400
        
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
        if '..' in analysis_id or '/' in analysis_id: return jsonify({"success": False, "error": "ID inválido."}), 400
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        if not os.path.exists(result_filepath): return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        with open(result_filepath, 'r') as f: data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video/<video_filename>', methods=['GET'])
def get_video_route(video_filename):
    try:
        if '..' in video_filename or '/' in video_filename: return "Nome de arquivo inválido", 400
        return send_from_directory(VIDEO_DIR, video_filename, as_attachment=False)
    except FileNotFoundError:
        return "Vídeo não encontrado.", 404
    except Exception as e:
        print(f"❌ Erro ao servir vídeo {video_filename}: {e}")
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
