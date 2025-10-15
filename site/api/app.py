# site/api/app.py - Codificação WebM (VP80) para máxima compatibilidade web

import os
import uuid
import json
import tempfile
import traceback
import numpy as np
import cv2
import mediapipe as mp
import mimetypes 

# Importações de Flask e CORS
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS

# Importações para o Google SSO
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

if not GOOGLE_CLIENT_ID:
    print("🚨 ERRO: A variável de ambiente GOOGLE_CLIENT_ID não está configurada.")
else:
    print(f"✅ GOOGLE_CLIENT_ID configurado: {GOOGLE_CLIENT_ID}")

BASE_DIR = tempfile.gettempdir()
RESULT_DIR = os.path.join(BASE_DIR, "analysis_results")
VIDEO_DIR = os.path.join(BASE_DIR, "analysis_videos")
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print(f"✅ Backend iniciado. Resultados em: {RESULT_DIR}, Vídeos em: {VIDEO_DIR}")

# Instâncias do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# --- CONFIGURAÇÃO DE CÓDEC (VP80 - WEB STANDARD) ---
# CRÍTICO: Codec WebM/VP8 para máxima compatibilidade nativa no navegador.
VIDEO_FOURCC = 'VP80' 
VIDEO_EXTENSION = '.webm'
VIDEO_MIN_SIZE_BYTES = 1000 

# --- FUNÇÕES DE ANÁLISE ---

def calculate_angle(a, b, c):
    """Calcula o ângulo entre 3 pontos (em graus)"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def analyze_video_and_extract_data(video_path, output_video_path):
    """
    Processa um vídeo para extrair dados de postura e gera um novo vídeo 
    com os landmarks (pontos corporais) desenhados usando o codec VP80.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    # Tenta usar o codec VP80
    try:
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_FOURCC) 
    except Exception as e:
        print(f"❌ Erro ao inicializar fourcc com {VIDEO_FOURCC}: {e}")
        cap.release()
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if width <= 0 or height <= 0:
        print(f"❌ Erro: Largura ({width}) ou Altura ({height}) inválida.")
        cap.release()
        return []
        
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    temporal_data = []
    frame_count = 0
    
    print(f"--- DEBUG: Iniciando análise de {cap.get(cv2.CAP_PROP_FRAME_COUNT)} frames. Codec: {VIDEO_FOURCC} ({VIDEO_EXTENSION}) ---")
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            try:
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(image_rgb)
                
                frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    
                    # Cálculo de Ângulos 
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

                    frame_data['angulo_ombro_esquerdo'] = calculate_angle(l_hip, l_shoulder, l_ear)
                    frame_data['angulo_ombro_direito'] = calculate_angle(r_hip, r_shoulder, l_ear)
                    frame_data['angulo_quadril_esquerdo'] = calculate_angle(l_shoulder, l_hip, l_knee)
                    frame_data['angulo_quadril_direito'] = calculate_angle(r_shoulder, r_hip, r_knee)
                    frame_data['angulo_joelho_esquerdo'] = calculate_angle(l_hip, l_knee, l_ankle)
                    frame_data['angulo_joelho_direito'] = calculate_angle(r_hip, r_knee, r_ankle)
                    
                    mid_shoulder = [(l_shoulder[0] + r_shoulder[0])/2, (l_shoulder[1] + r_shoulder[1])/2]
                    mid_hip = [(l_hip[0] + r_hip[0])/2, (l_hip[1] + r_hip[1])/2]
                    frame_data['angulo_coluna_cervical'] = calculate_angle(mid_hip, mid_shoulder, nose)

                    frame_data['assimetria_ombros_vertical'] = abs(l_shoulder[1] - r_shoulder[1])
                    frame_data['oscilacao_vertical_quadril'] = mid_hip[1]
                    frame_data['posicao_horizontal_quadril'] = mid_hip[0]
                    
                    temporal_data.append(frame_data)
                    
                    # Desenha os landmarks no frame para o vídeo de saída
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                              mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                                              mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))
                    out.write(frame)
                else:
                    out.write(frame) 
                    
            except Exception as e:
                print(f"⚠️ Aviso: Erro de processamento no frame {frame_count}: {e}")
                out.write(frame) 
                
            frame_count += 1
            
    cap.release()
    out.release()
    
    print(f"--- DEBUG: ANÁLISE CONCLUÍDA. Arquivo de saída: {output_video_path} ---")

    return temporal_data

# --- ROTAS DA API (ENDPOINTS) ---

@app.route('/api/callback', methods=['POST'])
def google_sso_callback():
    if not GOOGLE_CLIENT_ID:
        print("❌ SSO ERRO: GOOGLE_CLIENT_ID ausente.")
        return jsonify({"success": False, "error": "Configuração do servidor incompleta (CLIENT ID)."}), 500

    data = request.get_json()
    id_token_jwt = data.get('id_token')

    if not id_token_jwt:
        print("❌ SSO ERRO: Token ID não recebido.")
        return jsonify({"success": False, "error": "Token de autenticação não recebido."}), 400

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_jwt, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        user_data = {
            "id": id_info['sub'],
            "email": id_info.get('email', 'N/A'),
            "name": id_info.get('name', 'Usuário Google'),
            "picture": id_info.get('picture', '')
        }
        
        print(f"✅ Login Google bem-sucedido para: {user_data['email']}")
        return jsonify({"success": True, "user": user_data})

    except Exception as e:
        print(f"❌ SSO ERRO (Geral): {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": "Erro interno ao processar o login."}), 500


@app.route('/', methods=['GET'])
def root_health_check():
    return jsonify({"status": "ok", "message": "Servidor de análise postural no ar!"})

@app.route('/api/health', methods=['GET'])
def api_health_check():
    sso_status = "Configurado" if GOOGLE_CLIENT_ID else "CLIENT_ID Ausente"
    return jsonify({"status": "ok", "sso_status": sso_status})

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    if 'frontalImage' not in request.files:
        return jsonify({"success": False, "error": "Arquivo 'frontalImage' é obrigatório."}), 400

    analysis_id = str(uuid.uuid4())
    print(f"\nIniciando nova análise ID: {analysis_id}")
    
    try:
        video_file = request.files['frontalImage']
        
        original_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal_original.mp4")
        video_file.save(original_video_path)
        print(f"-> Vídeo frontal original recebido e salvo em: {original_video_path}")

        output_video_filename = f"{analysis_id}_frontal{VIDEO_EXTENSION}"
        output_video_path = os.path.join(VIDEO_DIR, output_video_filename)
        
        temporal_data = analyze_video_and_extract_data(original_video_path, output_video_path)

        video_size = os.path.getsize(output_video_path) if os.path.exists(output_video_path) else 0

        # --- DEBUG: Verifica se a codificação WebM falhou ---
        if video_size < VIDEO_MIN_SIZE_BYTES:
             # Retorna o erro detalhado para o frontend se a codificação falhar
             error_message = f"O vídeo de landmarks não pôde ser gerado (Tamanho: {video_size} bytes). O servidor não suporta codificação de vídeo com {VIDEO_FOURCC}. Verifique o FFmpeg no Railway."
             print(f"❌ Erro de processamento/arquivo: {error_message}")
             
             full_result = {
                "success": True, 
                "analysis_id": analysis_id,
                "data": {
                    "temporal_data_frontal": temporal_data,
                    "video_processed_filename": None,
                    "error_details": error_message
                }
            }
        else:
             full_result = {
                "success": True,
                "analysis_id": analysis_id,
                "data": {
                    "temporal_data_frontal": temporal_data,
                    "video_processed_filename": output_video_filename 
                }
            }
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump(full_result, f)
        
        print(f"✅ Análise {analysis_id} concluída. Vídeo final: {output_video_filename if video_size >= VIDEO_MIN_SIZE_BYTES else 'FALHOU'}")
        
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        # Se houver um erro antes da verificação de tamanho, retorna 500
        error_trace = traceback.format_exc()
        print(f"❌ Erro crítico na análise {analysis_id}: {e}\n{error_trace}")
        return jsonify({"success": False, "error": f"Erro interno: {e}", "details": error_trace}), 500
    finally:
        pass

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    """Serve o arquivo JSON com os dados da análise."""
    try:
        if '..' in analysis_id or '/' in analysis_id:
            return jsonify({"success": False, "error": "ID inválido."}), 400
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        if not os.path.exists(result_filepath):
            print(f"❌ Erro 404: Análise ID '{analysis_id}' não encontrada no disco.")
            return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        
        with open(result_filepath, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"❌ Erro ao servir análise JSON '{analysis_id}': {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video/<video_filename>', methods=['GET'])
def get_video_route(video_filename):
    """
    Serve os arquivos de vídeo. (Garantindo Content-Type para WebM)
    """
    try:
        if '..' in video_filename or '/' in video_filename:
            print(f"❌ Tentativa de acesso de vídeo inválida: {video_filename}")
            abort(400) # Bad Request
        
        filepath = os.path.join(VIDEO_DIR, video_filename)
        
        if not os.path.exists(filepath):
            print(f"❌ Aviso 404: Vídeo '{video_filename}' não encontrado no disco.")
            abort(404)
        
        # Define MIME Type baseado na extensão para compatibilidade
        if video_filename.endswith('.webm'):
            mimetype = 'video/webm'
        elif video_filename.endswith('.mp4'):
            mimetype = 'video/mp4'
        else:
            mimetype = 'application/octet-stream' # Fallback
            
        # Retorna o arquivo com o MIME type forçado e desativa o cache
        response = send_from_directory(
            VIDEO_DIR, 
            video_filename, 
            mimetype=mimetype, 
            as_attachment=False
        )
        # CRÍTICO: Desativa o cache do navegador para evitar problemas com arquivos corrompidos
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
        
    except FileNotFoundError:
        print(f"❌ Aviso 404 (Tratado): Vídeo '{video_filename}' não encontrado.")
        abort(404)
    except Exception as e:
        print(f"❌ Erro Crítico ao servir vídeo '{video_filename}': {e}")
        print(traceback.format_exc())
        abort(500) # Internal Server Error

@app.route('/api/delete-analysis/<analysis_id>', methods=['DELETE'])
def delete_analysis_route(analysis_id):
    """Rota para deletar o JSON da análise e os vídeos relacionados."""
    try:
        if '..' in analysis_id or '/' in analysis_id:
            return jsonify({"success": False, "error": "ID inválido."}), 400
        
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        video_original_filepath = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal_original.mp4")
        
        # Limpa .mp4 e .webm
        video_processed_mp4_filepath = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal.mp4") 
        video_processed_webm_filepath = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal.webm") 
        
        def safe_delete(filepath):
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False

        deleted_count = 0
        if safe_delete(result_filepath): deleted_count += 1
        if safe_delete(video_original_filepath): deleted_count += 1
        if safe_delete(video_processed_mp4_filepath): deleted_count += 1
        if safe_delete(video_processed_webm_filepath): deleted_count += 1
                 
        print(f"🗑️ Análise {analysis_id} e {deleted_count} arquivos deletados.")
        return jsonify({"success": True, "message": "Arquivos de análise deletados com sucesso."})

    except Exception as e:
        print(f"❌ Erro ao deletar análise {analysis_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- EXECUÇÃO ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
