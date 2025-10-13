# app.py - SERVIÇO UNIFICADO (BACKEND E ROTAS EM UM SÓ ARQUIVO)
# ESTE CÓDIGO CONTÉM AS FUNÇÕES DE ANÁLISE E AS ROTAS DE API.

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import uuid
from datetime import datetime
import base64
import os
import tempfile
import math

# Imports de Visão Computacional e Análise
import cv2
import mediapipe as mp
import matplotlib
matplotlib.use('Agg') 
import numpy as np 

app = Flask(__name__)

# =================================================================
# 🔥 CONFIGURAÇÃO CRÍTICA DO CORS PARA O VERCEL (FRONTEND)
# =================================================================
CORS(app, resources={r"/api/*": {"origins": [
    "https://ttc-analise-postural.vercel.app",   # Seu domínio Vercel
    "http://localhost:8080",                     # Desenvolvimento local
    "http://127.0.0.1:5000",
    "http://localhost:5000"
], 
"methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
"allow_headers": ["Content-Type", "Authorization"], 
"supports_credentials": True 
}})

print("✅ Serviço Unificado - Análise Postural e API Routes Iniciado!")

# ----------------------------------------------------------------
# ** TRATAMENTO MANUAL DO PREFLIGHT OPTIONS (Crucial para o CORS) **
@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        headers = {
            'Access-Control-Allow-Origin': request.headers.get('Origin'),
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
        return make_response('', 204, headers)
# ----------------------------------------------------------------


# =================================================================
# FUNÇÕES DE ANÁLISE POSTURAL (INTEGRADAS DO backend_app.py)
# =================================================================

def calcular_angulo(a, b, c):
    """Calcula ângulo entre 3 pontos (em graus)."""
    ba_x, ba_y = a[0]-b[0], a[1]-b[1]
    bc_x, bc_y = c[0]-b[0], c[1]-b[1]
    produto_escalar = ba_x*bc_x + ba_y*bc_y
    mag_ba = math.sqrt(ba_x**2 + ba_y**2)
    mag_bc = math.sqrt(bc_x**2 + bc_y**2)
    if mag_ba * mag_bc == 0:
        return 0
    cos_angle = produto_escalar / (mag_ba * mag_bc)
    cos_angle = max(min(cos_angle, 1), -1) 
    angle_rad = math.acos(cos_angle)
    return math.degrees(angle_rad)

def draw_landmarks(image, results):
    """Desenha os landmarks detectados na imagem."""
    if results.pose_landmarks:
        mp.solutions.drawing_utils.draw_landmarks(
            image, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
            mp.solutions.drawing_utils.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
            mp.solutions.drawing_utils.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
        )
    return image

def analyze_posture(image_path, view):
    """Realiza a análise postural principal e retorna os ângulos e a imagem processada."""
    
    cap = cv2.VideoCapture(image_path)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir ou ler a imagem/vídeo: {image_path}")
    
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise IOError("Não foi possível ler o primeiro frame do vídeo.")
        
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    with mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        results = pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            raise ValueError("Não foi possível detectar landmarks na imagem.")

        landmarks = results.pose_landmarks.landmark
        
        H, W, _ = frame.shape
        coords = {}
        for i, lm in enumerate(landmarks):
            coords[i] = (lm.x * W, lm.y * H)

        angles = {}
        
        if view == 'frontal':
            angles['shoulder_hip_L'] = calcular_angulo(coords[11], coords[23], (coords[23][0], 0))
            angles['shoulder_hip_R'] = calcular_angulo(coords[12], coords[24], (coords[24][0], 0))
            angles['shoulder_level_diff'] = abs(coords[11][1] - coords[12][1])
            angles['hip_level_diff'] = abs(coords[23][1] - coords[24][1])
            mid_shoulder_x = (coords[11][0] + coords[12][0]) / 2
            mid_shoulder_y = (coords[11][1] + coords[12][1]) / 2
            angles['head_alignment'] = calcular_angulo(coords[0], (mid_shoulder_x, mid_shoulder_y), (mid_shoulder_x, 0))

        elif view == 'lateral':
            angles['trunk_hip_knee'] = calcular_angulo(coords[11], coords[23], coords[25])
            angles['lumbar_proxy'] = calcular_angulo(coords[23], coords[25], coords[27])
            angles['head_forward'] = calcular_angulo(coords[23], coords[11], coords[0])

        for key, value in angles.items():
            if isinstance(value, (int, float)):
                 angles[key] = round(value, 2)
                 
        marked_image = draw_landmarks(frame, results)
        
        _, buffer = cv2.imencode('.png', cv2.cvtColor(marked_image, cv2.COLOR_RGB2BGR))
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return angles, image_base64


def generate_analysis_data(angles, view):
    """Gera um dicionário de análise e recomendações com base nos ângulos."""
    analise = {}
    recomendacoes = []
    
    if view == 'frontal':
        if angles.get('shoulder_level_diff', 0) > 30: 
            analise['shoulder_level'] = f"Desnível dos ombros detectado ({angles['shoulder_level_diff']:.2f}px)."
            recomendacoes.append("Exercícios para fortalecimento dos músculos do pescoço e trapézio (laterais).")
        if angles.get('shoulder_hip_L', 0) < 85 or angles.get('shoulder_hip_R', 0) < 85: 
             analise['trunk_lateral_deviation'] = "Desvio lateral de tronco (assimetria detectada)."
             recomendacoes.append("Alongamentos e fortalecimento assimétrico do core (prancha lateral).")

    elif view == 'lateral':
        if angles.get('trunk_hip_knee', 0) < 165: 
            analise['thoracic_kyphosis'] = "Postura com ombros protraídos (cifose aumentada)."
            recomendacoes.append("Fortalecimento da musculatura das costas (remadas) e alongamento peitoral.")
        if angles.get('lumbar_proxy', 0) > 175: 
            analise['lumbar_lordosis'] = "Possível aumento da Lordose Lombar (Tilt Pélvico Anterior)."
            recomendacoes.append("Fortalecimento do core abdominal e alongamento dos flexores do quadril e isquiotibiais.")
        if angles.get('head_forward', 0) < 165: 
            analise['head_forward_posture'] = "Protrusão de cabeça detectada."
            recomendacoes.append("Exercícios de retração cervical e alinhamento de pescoço.")
    
    if not analise:
        analise['geral'] = "Nenhuma alteração postural significativa detectada nesta vista."
        recomendacoes.append("Continue monitorando sua postura e pratique atividades físicas regularmente.")
        
    return {"analise": analise, "recomendacoes": list(set(recomendacoes))}

# =================================================================
# ROTAS DA API (Unificadas)
# =================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"success": True, "message": "Serviço UNIFICADO está funcionando"}), 200 

# ... (suas outras rotas como /api/auth/callback podem continuar aqui se precisar) ...

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    frontal_path = None
    transversal_path = None
    
    try:
        if 'frontalImage' not in request.files:
            return jsonify({"success": False, "error": "Arquivo 'frontalImage' é obrigatório."}), 400
        
        frontal_file = request.files['frontalImage']
        transversal_file = request.files.get('transversalImage')

        def save_file_to_temp(file_storage, prefix):
            if not file_storage or not file_storage.filename: return None
            _, ext = os.path.splitext(file_storage.filename)
            if not ext: ext = '.mp4'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix=prefix)
            file_storage.save(temp_file.name)
            temp_file.close()
            print(f"✅ Arquivo salvo temporariamente: {temp_file.name}")
            return temp_file.name

        frontal_path = save_file_to_temp(frontal_file, f"f_{analysis_id}")
        transversal_path = save_file_to_temp(transversal_file, f"t_{analysis_id}") if transversal_file else None

        # --- LÓGICA DE ANÁLISE REAL ---
        resultados = {
            "id": analysis_id,
            "timestamp": datetime.now().isoformat(),
            "frontal": None,
            "lateral": None,
            "recomendacoes": [],
            "analise_geral": {}
        }

        if frontal_path:
            angles_f, image_b64_f = analyze_posture(frontal_path, 'frontal')
            analise_f = generate_analysis_data(angles_f, 'frontal')
            resultados['frontal'] = {"angles": angles_f, "analise": analise_f['analise'], "image_b64": image_b64_f}
            resultados['recomendacoes'].extend(analise_f['recomendacoes'])
            resultados['analise_geral'].update(analise_f['analise'])
        
        if transversal_path:
            angles_l, image_b64_l = analyze_posture(transversal_path, 'lateral')
            analise_l = generate_analysis_data(angles_l, 'lateral')
            resultados['lateral'] = {"angles": angles_l, "analise": analise_l['analise'], "image_b64": image_b64_l}
            resultados['recomendacoes'].extend(analise_l['recomendacoes'])
            resultados['analise_geral'].update(analise_l['analise'])
        # --- FIM DA LÓGICA DE ANÁLISE ---

        resultados['recomendacoes'] = list(set(resultados['recomendacoes']))
        print(f"✅ Análise {analysis_id} concluída com sucesso!")
        
        return jsonify({
            "success": True,
            "message": "Análise postural concluída!",
            "analysis_id": analysis_id,
            "data": resultados
        })
        
    except Exception as e:
        print(f"❌ Erro geral na análise: {str(e)}")
        return jsonify({"success": False, "error": f"Erro interno do servidor: {str(e)}"}), 500
    finally:
        try:
            if frontal_path and os.path.exists(frontal_path): os.unlink(frontal_path)
            if transversal_path and os.path.exists(transversal_path): os.unlink(transversal_path)
        except Exception as e:
            print(f"⚠️ Aviso: Falha ao limpar arquivos temporários: {e}")

# ... (sua rota /api/analysis/<analysis_id> pode continuar aqui) ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Servidor Flask All-in-One rodando em http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
