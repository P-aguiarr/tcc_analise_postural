# site/api/app.py - TENTATIVA DE CODEC MP4V PADRÃO

import os
import uuid
import json
import tempfile
import traceback
import numpy as np
import cv2
import mediapipe as mp

# Importações de Flask e CORS
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Importações para o Google SSO
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
# Configura CORS para permitir chamadas de qualquer origem
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Variáveis de Ambiente do Google (CRÍTICO para o SSO)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
# GOOGLE_CLIENT_SECRET não é usado para validação do token ID.

if not GOOGLE_CLIENT_ID:
    print("🚨 ERRO: A variável de ambiente GOOGLE_CLIENT_ID não está configurada.")
else:
    print(f"✅ GOOGLE_CLIENT_ID configurado: {GOOGLE_CLIENT_ID}")


# Diretórios para salvar os resultados e vídeos
BASE_DIR = tempfile.gettempdir()
RESULT_DIR = os.path.join(BASE_DIR, "analysis_results")
VIDEO_DIR = os.path.join(BASE_DIR, "analysis_videos")
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print(f"✅ Backend iniciado. Resultados em: {RESULT_DIR}, Vídeos em: {VIDEO_DIR}")

# Instâncias do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# --- FUNÇÕES DE ANÁLISE ---

def calculate_angle(a, b, c):
    """Calcula o ângulo entre 3 pontos (em graus)"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    # Apenas pontos X e Y são usados para a análise 2D no plano
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def analyze_video_and_extract_data(video_path, output_video_path):
    """
    Processa um vídeo para extrair dados de postura frame a frame e, ao mesmo tempo,
    gera um novo vídeo com os landmarks (pontos corporais) desenhados.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Erro ao abrir vídeo: {video_path}")
        # Retorna lista vazia se não conseguir abrir o vídeo
        return []

    # RETORNANDO AO MP4V PADRÃO (Compatibilidade com Web/Railway)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Verifica se a largura/altura é válida antes de criar o VideoWriter
    if width <= 0 or height <= 0:
        print(f"❌ Erro: Largura ({width}) ou Altura ({height}) inválida.")
        cap.release()
        return []
        
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    temporal_data = []
    frame_count = 0
    
    print(f"--- DEBUG: Iniciando análise de vídeo. Codec: MP4V ---")
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Usar try-except para isolar erros de processamento por frame
            try:
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(image_rgb)
                
                frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    
                    # Extração de Landmarks para o JSON (Coordenadas normalizadas 0-1)
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

                    # Cálculo de Ângulos (usando coordenadas normalizadas 0-1)
                    frame_data['angulo_ombro_esquerdo'] = calculate_angle(l_hip, l_shoulder, l_ear)
                    frame_data['angulo_ombro_direito'] = calculate_angle(r_hip, r_shoulder, l_ear)
                    frame_data['angulo_quadril_esquerdo'] = calculate_angle(l_shoulder, l_hip, l_knee)
                    frame_data['angulo_quadril_direito'] = calculate_angle(r_shoulder, r_hip, r_knee)
                    frame_data['angulo_joelho_esquerdo'] = calculate_angle(l_hip, l_knee, l_ankle)
                    frame_data['angulo_joelho_direito'] = calculate_angle(r_hip, r_knee, r_ankle)
                    
                    mid_shoulder = [(l_shoulder[0] + r_shoulder[0])/2, (l_shoulder[1] + r_shoulder[1])/2]
                    mid_hip = [(l_hip[0] + r_hip[0])/2, (l_hip[1] + r_hip[1])/2]
                    frame_data['angulo_coluna_cervical'] = calculate_angle(mid_hip, mid_shoulder, nose)

                    # Simetria e Posição (usando coordenadas normalizadas 0-1)
                    frame_data['assimetria_ombros_vertical'] = abs(l_shoulder[1] - r_shoulder[1])
                    frame_data['oscilacao_vertical_quadril'] = mid_hip[1]
                    frame_data['posicao_horizontal_quadril'] = mid_hip[0]
                    
                temporal_data.append(frame_data)
                
                # Desenha os landmarks no frame para o vídeo de saída
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                          mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                                          mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))
                out.write(frame)
                
            except Exception as e:
                # Loga o erro, mas continua processando o próximo frame
                print(f"⚠️ Aviso: Erro de processamento no frame {frame_count}: {e}")
                # Escreve o frame original no vídeo de saída para evitar quebra
                out.write(frame) 
                
            frame_count += 1
            
    cap.release()
    out.release()
    
    print(f"--- DEBUG: ANÁLISE COMPLETA. Arquivo de saída: {output_video_path} ---")

    return temporal_data

# --- ROTAS DA API (ENDPOINTS) ---

@app.route('/api/callback', methods=['POST'])
def google_sso_callback():
    """
    Rota de callback para validar o ID Token do Google e retornar dados do usuário.
    Essa rota é chamada pelo login.html.
    """
    if not GOOGLE_CLIENT_ID:
        print("❌ SSO ERRO: GOOGLE_CLIENT_ID ausente.")
        return jsonify({"success": False, "error": "Configuração do servidor incompleta (CLIENT ID)."}), 500

    data = request.get_json()
    id_token_jwt = data.get('id_token')

    if not id_token_jwt:
        print("❌ SSO ERRO: Token ID não recebido.")
        return jsonify({"success": False, "error": "Token de autenticação não recebido."}), 400

    try:
        # 1. Especifica o ID do cliente que a app de destino usa
        id_info = id_token.verify_oauth2_token(
            id_token_jwt, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        # 2. Verifica se o token foi emitido para seu domínio (opcional, mas recomendado)
        # if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
        #     raise ValueError('Token incorreto (issuer inválido).')

        # 3. Extrai as informações do usuário
        user_id = id_info['sub']
        user_email = id_info.get('email', 'N/A')
        user_name = id_info.get('name', 'Usuário Google')
        user_picture = id_info.get('picture', '')

        user_data = {
            "id": user_id,
            "email": user_email,
            "name": user_name,
            "picture": user_picture
        }
        
        print(f"✅ Login Google bem-sucedido para: {user_email}")
        return jsonify({"success": True, "user": user_data})

    except ValueError as e:
        print(f"❌ SSO ERRO (Validação de Token): {e}")
        return jsonify({"success": False, "error": "Falha na validação do token do Google.", "details": str(e)}), 401
    except Exception as e:
        print(f"❌ SSO ERRO (Geral): {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": "Erro interno ao processar o login."}), 500


@app.route('/', methods=['GET'])
def root_health_check():
    """Rota raiz para o health check da Railway."""
    return jsonify({"status": "ok", "message": "Servidor de análise postural no ar!"})

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """Rota de health check legada, caso seja necessária."""
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
        
        # MANTENDO .MP4 para o original
        original_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal_original.mp4")
        
        # Salva o vídeo original no diretório de vídeos
        video_file.save(original_video_path)
        print(f"-> Vídeo frontal original recebido e salvo em: {original_video_path}")

        # SAÍDA .MP4 para o processado
        output_video_path = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal.mp4") 
        
        # Executa a análise que extrai os dados e gera o vídeo com landmarks
        temporal_data = analyze_video_and_extract_data(original_video_path, output_video_path)
        
        # Monta o JSON final com os resultados
        full_result = {
            "success": True,
            "analysis_id": analysis_id,
            "data": {
                # Dados que o frontend espera (os ângulos calculados no analyze_video_and_extract_data)
                "temporal_data_frontal": temporal_data
                # Em um cenário ideal, você faria uma análise mais completa aqui, como em analise_completa.py
            }
        }
        
        # Salva o arquivo JSON com os resultados
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump(full_result, f)
        
        print(f"✅ Análise {analysis_id} concluída. JSON salvo em: {result_filepath}")
        
        # Se temporal_data estiver vazio, significa que o vídeo não pôde ser processado (problema de codec ou arquivo)
        if not temporal_data:
             return jsonify({"success": False, "error": "O vídeo não pôde ser processado (verifique o formato/codec).", "analysis_id": analysis_id}), 500

        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        print(f"❌ Erro crítico na análise {analysis_id}: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": f"Erro interno no servidor: {e}", "analysis_id": analysis_id}), 500
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
            # Loga o erro internamente
            print(f"❌ Erro 404: Análise ID '{analysis_id}' não encontrada no disco.")
            return jsonify({"success": False, "error": "Análise não encontrada."}), 404
        
        with open(result_filepath, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        # Loga o erro internamente
        print(f"❌ Erro ao servir análise JSON '{analysis_id}': {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video/<video_filename>', methods=['GET'])
def get_video_route(video_filename):
    """Serve os arquivos de vídeo processados. Sem log na resposta HTTP."""
    try:
        if '..' in video_filename or '/' in video_filename:
            # Loga a tentativa de acesso inválida
            print(f"❌ Tentativa de acesso de vídeo inválida: {video_filename}")
            return "", 400
            
        # Tenta servir o arquivo
        return send_from_directory(VIDEO_DIR, video_filename)
        
    except FileNotFoundError:
        # Loga 404 internamente, mas retorna uma resposta vazia e silenciosa no HTTP
        print(f"❌ Aviso 404: Vídeo '{video_filename}' não encontrado.")
        return "", 404 
    except Exception as e:
        # Loga o erro geral internamente, mas retorna 500 silencioso
        print(f"❌ Erro ao servir vídeo '{video_filename}': {e}")
        return "", 500


@app.route('/api/delete-analysis/<analysis_id>', methods=['DELETE'])
def delete_analysis_route(analysis_id):
    """Rota para deletar o JSON da análise e os vídeos relacionados."""
    try:
        if '..' in analysis_id or '/' in analysis_id:
            return jsonify({"success": False, "error": "ID inválido."}), 400
        
        # Caminhos dos arquivos
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        video_original_filepath = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal_original.mp4")
        video_processed_mp4_filepath = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal.mp4") 
        video_processed_avi_filepath = os.path.join(VIDEO_DIR, f"{analysis_id}_frontal.avi") # Limpa .avi de tentativas anteriores

        def safe_delete(filepath):
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False

        # Deleta os arquivos
        deleted_count = 0
        if safe_delete(result_filepath): deleted_count += 1
        if safe_delete(video_original_filepath): deleted_count += 1
        if safe_delete(video_processed_mp4_filepath): deleted_count += 1
        if safe_delete(video_processed_avi_filepath): deleted_count += 1
             
        print(f"🗑️ Análise {analysis_id} e {deleted_count} arquivos deletados.")
        return jsonify({"success": True, "message": "Arquivos de análise deletados com sucesso."})

    except Exception as e:
        print(f"❌ Erro ao deletar análise {analysis_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- EXECUÇÃO ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
