# app.py - SERVIÇO UNIFICADO E COMPLETO
# Contém todas as funções de análise temporal e estática para o dashboard.

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

app = Flask(__name__)

# =================================================================
# 🔥 CONFIGURAÇÃO CRÍTICA DO CORS PARA O VERCEL (FRONTEND)
# =================================================================
CORS(app, resources={r"/api/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",
    "http://localhost:8080", "http://127.0.0.1:5000", "http://localhost:5000"
], "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"], "supports_credentials": True }})

print("✅ Serviço Unificado Completo - Análise Postural e API Routes Iniciado!")

# ----------------------------------------------------------------
# ** TRATAMENTO MANUAL DO PREFLIGHT OPTIONS (Crucial para o CORS) **
@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        headers = { 'Access-Control-Allow-Origin': request.headers.get('Origin'), 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Allow-Credentials': 'true' }
        return make_response('', 204, headers)
# ----------------------------------------------------------------

# =================================================================
# FUNÇÕES DE ANÁLISE POSTURAL COMPLETAS
# =================================================================

# Inicialização do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calcular_angulo(a, b, c):
    """Calcula o ângulo entre 3 pontos (em graus)."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def get_landmark_coords(landmarks, landmark_enum, frame_shape):
    """Extrai as coordenadas (x, y) de um landmark específico."""
    if not landmarks: return None
    lm = landmarks[landmark_enum.value]
    return (lm.x * frame_shape[1], lm.y * frame_shape[0])

def analyze_video_complete(video_path):
    """
    Função principal que processa um vídeo inteiro, frame a frame,
    e retorna tanto a análise temporal quanto um vídeo processado em Base64.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    # Configurações do vídeo de saída
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
            if not ret:
                break

            # Processamento do frame
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                shape = frame.shape

                # Extrai coordenadas dos pontos principais
                l_shoulder = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
                r_shoulder = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
                l_hip = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_HIP, shape)
                r_hip = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_HIP, shape)
                l_knee = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_KNEE, shape)
                r_knee = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_KNEE, shape)
                l_ankle = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE, shape)
                r_ankle = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
                nose = get_landmark_coords(landmarks, mp_pose.PoseLandmark.NOSE, shape)
                
                # --- Cálculos para os gráficos ---
                if all([l_shoulder, r_shoulder, l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle]):
                    # Ângulos Articulares
                    frame_data["angulo_ombro_esquerdo"] = calcular_angulo(l_hip, l_shoulder, l_knee)
                    frame_data["angulo_ombro_direito"] = calcular_angulo(r_hip, r_shoulder, r_knee)
                    frame_data["angulo_quadril_esquerdo"] = calcular_angulo(l_shoulder, l_hip, l_knee)
                    frame_data["angulo_quadril_direito"] = calcular_angulo(r_shoulder, r_hip, r_knee)
                    frame_data["angulo_joelho_esquerdo"] = calcular_angulo(l_hip, l_knee, l_ankle)
                    frame_data["angulo_joelho_direito"] = calcular_angulo(r_hip, r_knee, r_ankle)

                    # Simetria Corporal (diferença vertical em pixels)
                    frame_data["assimetria_ombros_metros"] = abs(l_shoulder[1] - r_shoulder[1]) / height # Normalizado pela altura
                    frame_data["assimetria_quadris_metros"] = abs(l_hip[1] - r_hip[1]) / height

                    # Análise Temporal (oscilação vertical)
                    frame_data["LEFT_HIP_y_metros"] = l_hip[1] / height
                    frame_data["RIGHT_HIP_y_metros"] = r_hip[1] / height
                
                # Ângulos da Coluna (proxy)
                if all([nose, l_shoulder, r_shoulder, l_hip, r_hip]):
                    mid_shoulder = ((l_shoulder[0] + r_shoulder[0])/2, (l_shoulder[1] + r_shoulder[1])/2)
                    mid_hip = ((l_hip[0] + r_hip[0])/2, (l_hip[1] + r_hip[1])/2)
                    frame_data["angulo_coluna_cervical"] = calcular_angulo(mid_hip, mid_shoulder, nose)
                    frame_data["angulo_coluna_toracica"] = calcular_angulo(l_shoulder, mid_hip, r_shoulder)

                # Desenha os landmarks no frame
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                          mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                                          mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2))
            
            temporal_data.append(frame_data)
            out.write(frame) # Escreve o frame processado no vídeo de saída
            frame_count += 1
    
    cap.release()
    out.release()
    
    # Codifica o vídeo de saída para Base64
    with open(temp_output_path, "rb") as video_file:
        video_base64 = base64.b64encode(video_file.read()).decode('utf-8')
    
    os.unlink(temp_output_path) # Limpa o arquivo de vídeo temporário

    return temporal_data, video_base64


def generate_static_recommendations(temporal_data):
    """Gera recomendações com base no primeiro frame com dados."""
    first_frame = next((frame for frame in temporal_data if "angulo_ombro_esquerdo" in frame), None)
    if not first_frame:
        return ["Não foi possível gerar recomendações, poucos dados detectados."]

    recomendacoes = []
    if first_frame.get("assimetria_ombros_metros", 0) * 100 > 3: # >3% da altura
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
    return jsonify({"success": True, "message": "Serviço UNIFICADO e COMPLETO está funcionando"}), 200

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    video_path = None
    
    try:
        if 'frontalImage' not in request.files:
            return jsonify({"success": False, "error": "Arquivo 'frontalImage' é obrigatório."}), 400
        
        video_file = request.files['frontalImage'] # Por enquanto, focamos em um vídeo

        # Salva o arquivo temporariamente
        _, ext = os.path.splitext(video_file.filename)
        if not ext: ext = '.mp4'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        video_file.save(temp_file.name)
        video_path = temp_file.name
        temp_file.close()
        print(f"✅ Arquivo salvo temporariamente: {video_path}")

        # --- LÓGICA DE ANÁLISE COMPLETA ---
        temporal_data, video_base64 = analyze_video_complete(video_path)
        
        if not temporal_data:
            raise ValueError("A análise de vídeo não produziu dados.")

        recomendacoes = generate_static_recommendations(temporal_data)
        
        print(f"✅ Análise {analysis_id} concluída com sucesso. Frames processados: {len(temporal_data)}")
        
        return jsonify({
            "success": True,
            "message": "Análise postural completa concluída!",
            "analysis_id": analysis_id,
            "data": {
                "temporal_data": temporal_data,
                "video_processed_b64": video_base64,
                "recommendations": recomendacoes
            }
        })
        
    except Exception as e:
        print(f"❌ Erro geral na análise: {e}")
        return jsonify({"success": False, "error": f"Erro interno do servidor: {str(e)}"}), 500
    finally:
        if video_path and os.path.exists(video_path):
            os.unlink(video_path)
            print(f"🗑️ Arquivo temporário removido: {video_path}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
