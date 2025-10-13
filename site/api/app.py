# site/api/app.py - VERSÃO FINAL E DEFINITIVA (COM CÁLCULOS COMPLETOS)

from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
import uuid
import os
import tempfile
import cv2
import mediapipe as mp
import numpy as np
import json
import traceback

app = Flask(__name__)

# Configuração do CORS (ajuste a origin se o seu frontend estiver em outro domínio)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Diretórios para salvar os resultados
BASE_DIR = tempfile.gettempdir()
RESULT_DIR = os.path.join(BASE_DIR, "analysis_results")
VIDEO_DIR = os.path.join(BASE_DIR, "analysis_videos")
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print(f"✅ Backend iniciado. Resultados em: {RESULT_DIR}, Vídeos em: {VIDEO_DIR}")

# Instâncias do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(a, b, c):
    """Calcula o ângulo entre 3 pontos (em graus)"""
    a = np.array(a) # Primeiro ponto
    b = np.array(b) # Vértice
    c = np.array(c) # Terceiro ponto
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def analyze_video_and_extract_data(video_path, output_video_path):
    """
    Processa o vídeo para extrair dados frame a frame e gerar um vídeo com landmarks.
    Retorna uma lista de dicionários, cada um contendo os dados de um frame.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    temporal_data = []
    frame_count = 0
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Processamento da imagem
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            
            frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}

            # Extração de dados se landmarks forem detectados
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # --- Coordenadas dos pontos principais ---
                l_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                r_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                l_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                r_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
                l_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                r_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
                l_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                r_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
                l_ear = [landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].x, landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].y]
                nose = [landmarks[mp_pose.PoseLandmark.NOSE.value].x, landmarks[mp_pose.PoseLandmark.NOSE.value].y]

                # --- 1. CÁLCULO DOS ÂNGULOS ARTICULARES ---
                frame_data['angulo_ombro_esquerdo'] = calculate_angle(l_hip, l_shoulder, l_ear)
                frame_data['angulo_ombro_direito'] = calculate_angle(r_hip, r_shoulder, l_ear) # Usando l_ear como ref
                frame_data['angulo_quadril_esquerdo'] = calculate_angle(l_shoulder, l_hip, l_knee)
                frame_data['angulo_quadril_direito'] = calculate_angle(r_shoulder, r_hip, r_knee)
                frame_data['angulo_joelho_esquerdo'] = calculate_angle(l_hip, l_knee, l_ankle)
                frame_data['angulo_joelho_direito'] = calculate_angle(r_hip, r_knee, r_ankle)
                
                # Ângulo da coluna (cervical) - aproximação
                mid_shoulder = [(l_shoulder[0] + r_shoulder[0])/2, (l_shoulder[1] + r_shoulder[1])/2]
                mid_hip = [(l_hip[0] + r_hip[0])/2, (l_hip[1] + r_hip[1])/2]
                frame_data['angulo_coluna_cervical'] = calculate_angle(mid_hip, mid_shoulder, nose)

                # --- 2. CÁLCULO DE SIMETRIA CORPORAL ---
                # Assimetria vertical dos ombros (diferença na altura)
                frame_data['assimetria_ombros_vertical'] = abs(l_shoulder[1] - r_shoulder[1])
                # Assimetria vertical dos quadris
                frame_data['assimetria_quadris_vertical'] = abs(l_hip[1] - r_hip[1])
                
                # --- 3. ANÁLISE TEMPORAL ---
                # Oscilação vertical do quadril (usando o ponto médio)
                frame_data['oscilacao_vertical_quadril'] = mid_hip[1]
                # Posição horizontal do quadril para cálculo de velocidade
                frame_data['posicao_horizontal_quadril'] = mid_hip[0]


            temporal_data.append(frame_data)
            
            # Desenha os landmarks no frame para o vídeo de saída
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                      mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                                      mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2))
            out.write(frame)
            frame_count += 1
            
    cap.release()
    out.release()
    print(f"📹 Vídeo com landmarks salvo em: {output_video_path}")
    return temporal_data


@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    print(f"\n\nIniciando nova análise ID: {analysis_id}")
    
    files_to_process = []
    
    # Processa arquivo frontal (obrigatório)
    if 'frontalImage' in request.files:
        files_to_process.append(('frontal', request.files['frontalImage']))
    else:
        return jsonify({"success": False, "error": "Arquivo 'frontalImage' é obrigatório."}), 400
        
    # Processa arquivo transversal (opcional)
    if 'transversalImage' in request.files:
        files_to_process.append(('transversal', request.files['transversalImage']))

    analysis_results = {"success": True, "analysis_id": analysis_id, "data": {}}
    
    try:
        for plane, video_file in files_to_process:
            print(f"-> Processando vídeo do plano: {plane}")
            
            ext = os.path.splitext(video_file.filename)[1] or '.mp4'
            
            # Salva o vídeo original
            original_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_{plane}_original{ext}")
            video_file.save(original_video_path)
            print(f"   - Vídeo original salvo em: {original_video_path}")

            # Caminho para o vídeo com landmarks
            output_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_{plane}.mp4")
            
            # A MÁGICA ACONTECE AQUI
            temporal_data = analyze_video_and_extract_data(original_video_path, output_video_path)
            
            analysis_results["data"][f"temporal_data_{plane}"] = temporal_data
            print(f"   - Dados do plano '{plane}' extraídos com sucesso ({len(temporal_data)} frames).")

        # Salva o JSON com todos os dados
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump(analysis_results, f)
        
        print(f"✅ Análise {analysis_id} concluída e JSON salvo.")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        print(f"❌ Erro crítico na análise {analysis_id}: {e}")
        print(traceback.format_exc()) # Log completo do erro
        return jsonify({"success": False, "error": f"Erro interno no servidor: {e}"}), 500


@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    try:
        if '..' in analysis_id or '/' in analysis_id:
            return jsonify({"success": False, "error": "ID inválido."}), 400
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
    try:
        if '..' in video_filename or '/' in video_filename:
            return "Nome de arquivo inválido", 400
        return send_from_directory(VIDEO_DIR, video_filename, as_attachment=False)
    except FileNotFoundError:
        return "Vídeo não encontrado.", 404
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
