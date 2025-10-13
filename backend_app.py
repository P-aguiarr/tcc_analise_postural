# backend_app.py - VERSÃO FINAL COMPLETA COM CORREÇÕES DE CORS E LÓGICA DE ANÁLISE

from flask import Flask, request, jsonify, render_template, send_from_directory
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
# matplotlib e pandas não são estritamente necessários para esta versão, 
# mas mantidos por precaução caso você reintroduza a plotagem de gráficos.
import matplotlib
matplotlib.use('Agg') 
import numpy as np 
# from scipy.signal import savgol_filter # Removido por não ser usado

# Imports necessários para a validação do token Google
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# ==========================================================
# CONFIGURAÇÃO DA APLICAÇÃO FLASK (CRUCIAL)
# ==========================================================
app = Flask(__name__, template_folder='site', static_folder='site')

# --- CONFIGURAÇÃO EXPLÍCITA DO CORS (CORREÇÃO DE BLOQUEIO) ---
# Lê a origem do VERCEL da variável de ambiente ou usa um fallback
VERCEL_ORIGIN = os.environ.get('VERCEL_ORIGIN', "https://ttc-analise-postural.vercel.app")

# Garante que o CORS permite a origem Vercel e a origem de desenvolvimento local
CORS(app, resources={r"/*": {"origins": [VERCEL_ORIGIN, "http://localhost:3000"]}})
print(f"✅ CORS configurado para permitir a origem: {VERCEL_ORIGIN}")


# ==========================================================
# CONFIGURAÇÕES DE AMBIENTE E VARIÁVEIS DO RAILWAY
# ==========================================================
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

if not GOOGLE_CLIENT_ID:
    print("❌ ERRO: A variável de ambiente GOOGLE_CLIENT_ID deve ser definida no Railway.")
else:
    print("✅ Configurações de Google Auth carregadas com sucesso.")

# Inicialização do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

print("✅ Backend Railway - Análise Postural Avançado Iniciado!")

# ==========================================================
# ROTAS DE SERVIÇO DE ARQUIVOS HTML (Templates na pasta 'site')
# ==========================================================

@app.route('/')
def home_page():
    """Rota padrão que redireciona ou serve a página de login."""
    return login_page()

@app.route('/login')
def login_page():
    """Rota explícita para o arquivo login.html."""
    try:
        return render_template('login.html') 
    except Exception as e:
        return f"Erro ao renderizar 'login.html'. Verifique se ele está na pasta 'site'. Detalhe: {str(e)}", 500

@app.route('/poslogin')
def poslogin_page():
    """Rota para a página pós-login."""
    try:
        return render_template('poslogin.html')
    except Exception as e:
        return f"Erro ao renderizar 'poslogin.html'. Verifique se ele está na pasta 'site'.", 500

@app.route('/configuracoes')
def configuracoes_page():
    """Rota para a página de configurações."""
    try:
        return render_template('configuracoes.html')
    except Exception as e:
        return f"Erro ao renderizar 'configuracoes.html'. Verifique se ele está na pasta 'site'.", 500

# ==========================================================
# ENDPOINTS DE AUTENTICAÇÃO E CONFIGURAÇÃO
# ==========================================================

@app.route('/ping', methods=['GET'], strict_slashes=False)
def ping():
    """Endpoint de health check."""
    return jsonify({
        "status": "ok",
        "message": "API está no ar! (Rota direta)"
    })

@app.route('/config', methods=['GET'], strict_slashes=False)
def get_config():
    """Endpoint para fornecer o GOOGLE_CLIENT_ID ao frontend."""
    if not GOOGLE_CLIENT_ID:
        return jsonify({
            "success": False,
            "error": "GOOGLE_CLIENT_ID não encontrado nas variáveis de ambiente."
        }), 500
        
    return jsonify({
        "success": True,
        "client_id": GOOGLE_CLIENT_ID # O frontend espera esta chave
    })

@app.route('/auth/callback', methods=['POST'], strict_slashes=False)
def auth_callback():
    """
    Endpoint chamado pelo frontend após o login do Google.
    Recebe o 'id_token' e o valida.
    """
    data = request.get_json()
    # O frontend pode enviar 'token' ou 'id_token' dependendo da biblioteca
    token = data.get('token') or data.get('id_token') 
        
    if not token:
        return jsonify({"success": False, "error": "Token de credencial do Google ausente."}), 400
        
    if not GOOGLE_CLIENT_ID:
        return jsonify({"success": False, "error": "Configuração de autenticação faltando no servidor (Client ID)."}), 500

    try:
        # 1. Validação do ID Token com o Google
        id_info = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID 
        )
            
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Token inválido: Emissor incorreto.')
            
        user_id = id_info['sub']
        user_email = id_info['email']
        user_name = id_info.get('name', 'Usuário')
            
        print(f"✅ Usuário autenticado: {user_email} (ID: {user_id})")
            
        # 2. Retorno ao Frontend
        return jsonify({
            "success": True, 
            "message": "Autenticação e validação do token bem-sucedidas.", 
            "user_info": {"id": user_id, "email": user_email, "name": user_name},
            "token": "JWT_TOKEN_PARA_USO_FUTURO" # Retorna um token de sessão (mockado)
        }), 200

    except ValueError as e:
        print(f"❌ Erro de validação do token: {str(e)}")
        return jsonify({"success": False, "error": f"Falha na validação do token: {str(e)}"}), 401
    except Exception as e:
        print(f"❌ Erro inesperado no callback de autenticação: {str(e)}")
        return jsonify({"success": False, "error": "Erro interno do servidor durante a autenticação."}), 500

# ==========================================================
# FUNÇÕES DE ANÁLISE POSTURAL
# ==========================================================

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
    # Garante que o valor esteja entre -1 e 1
    cos_angle = max(min(cos_angle, 1), -1) 
    angle = math.acos(cos_angle)
    return math.degrees(angle)

def draw_landmarks(image, results):
    """Desenha os landmarks detectados na imagem."""
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
        )
    return image

def analyze_posture(image_path, view):
    """Realiza a análise postural principal e retorna os ângulos e a imagem processada."""
    
    # É CRÍTICO que o cv2 consiga ler o arquivo temporário
    cap = cv2.VideoCapture(image_path)
    if not cap.isOpened():
        # Tenta ler diretamente como imagem estática
        frame = cv2.imread(image_path)
        if frame is None:
            raise IOError(f"Não foi possível abrir ou ler a imagem: {image_path}")
        # Como é uma imagem estática, não há cap.release()
    else:
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            raise IOError("Não foi possível ler o frame da imagem.")
        
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        results = pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            raise ValueError("Não foi possível detectar landmarks na imagem.")

        landmarks = results.pose_landmarks.landmark
        
        H, W, _ = frame.shape
        coords = {}
        # Mapeia as coordenadas (x, y) de cada landmark para pixels
        for i, lm in enumerate(landmarks):
            coords[i] = (lm.x * W, lm.y * H)

        angles = {}
        
        if view == 'frontal':
            # Ângulos e desvios para análise frontal
            # Ex: Desvio lateral de tronco (ângulo entre ombro, quadril e vertical)
            angles['shoulder_hip_L'] = calcular_angulo(coords[11], coords[23], (coords[23][0], 0))
            angles['shoulder_hip_R'] = calcular_angulo(coords[12], coords[24], (coords[24][0], 0))
            
            # Nível de ombro (diferença de altura em pixels)
            angles['shoulder_level_diff'] = abs(coords[11][1] - coords[12][1])
            # Nível de quadril (diferença de altura em pixels)
            angles['hip_level_diff'] = abs(coords[23][1] - coords[24][1])

            # Exemplo de Alinhamento da cabeça em relação ao centro dos ombros
            mid_shoulder_x = (coords[11][0] + coords[12][0]) / 2
            mid_shoulder_y = (coords[11][1] + coords[12][1]) / 2
            angles['head_alignment'] = calcular_angulo(coords[0], (mid_shoulder_x, mid_shoulder_y), (mid_shoulder_x, 0))

        elif view == 'lateral':
            # Ângulos para análise lateral
            # Ângulo Tronco-Quadril-Joelho (Projeção da postura geral do tronco)
            angles['trunk_hip_knee'] = calcular_angulo(coords[11], coords[23], coords[25])
            
            # Ângulo Lombar/Sacral (proxy: ângulo Quadril-Joelho-Tornozelo)
            angles['lumbar_proxy'] = calcular_angulo(coords[23], coords[25], coords[27])
            
            # Postura da Cabeça (Head Forward Posture) - Ângulo Ombro-Quadril-Orelha
            # Usando Orelha (0) no lugar de Nariz (0) ou Olho (2)
            angles['head_forward'] = calcular_angulo(coords[23], coords[11], coords[0])

        
        # Arredonda todos os ângulos
        for key, value in angles.items():
            if isinstance(value, (int, float)):
                 angles[key] = round(value, 2)
            else:
                 # Mantém as diferenças de pixel como estão
                 angles[key] = round(value, 2)
                 
        marked_image = draw_landmarks(frame, results)
        
        # Converte a imagem processada para Base64
        _, buffer = cv2.imencode('.png', cv2.cvtColor(marked_image, cv2.COLOR_RGB2BGR))
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return angles, image_base64


def generate_analysis_data(angles, view):
    """Gera um dicionário de análise e recomendações com base nos ângulos."""
    analise = {}
    recomendacoes = []
    
    if view == 'frontal':
        # Assumindo um desnível de 30 pixels (ou mais) é significativo (precisa ser calibrado)
        if angles.get('shoulder_level_diff', 0) > 30: 
            analise['shoulder_level'] = f"Desnível dos ombros detectado ({angles['shoulder_level_diff']}px)."
            recomendacoes.append("Exercícios para fortalecimento dos músculos do pescoço e trapézio (laterais).")
            
        # Assumindo que o ângulo ombro-quadril-vertical deve ser próximo a 90 (o valor exato depende da sua calibração)
        if angles.get('shoulder_hip_L', 0) < 85 or angles.get('shoulder_hip_R', 0) < 85: 
             analise['trunk_lateral_deviation'] = "Desvio lateral de tronco (assimetria detectada)."
             recomendacoes.append("Alongamentos e fortalecimento assimétrico do core (prancha lateral).")

    elif view == 'lateral':
        
        # Ângulos acima de 170 e abaixo de 180 são geralmente considerados neutros ou próximos
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
        
    return {
        "analise": analise,
        # Usa set para garantir que as recomendações não se repitam
        "recomendacoes": list(set(recomendacoes)) 
    }

# ==========================================================
# ENDPOINTS PRINCIPAIS DA APLICAÇÃO (Análise)
# ==========================================================

@app.route('/analyze', methods=['POST'], strict_slashes=False)
def analyze_images():
    """Endpoint principal para análise postural."""
    analysis_id = str(uuid.uuid4())
    frontal_path = None
    transversal_path = None
    
    try:
        data = request.get_json()
        
        frontal_base64 = data.get('frontalImage')
        transversal_base64 = data.get('transversalImage')
        
        if not frontal_base64:
            return jsonify({"success": False, "error": "Imagem frontal é obrigatória."}), 400
        
        def save_base64_to_temp_file(base64_string, prefix):
            """Função utilitária para decodificar e salvar o Base64 temporariamente."""
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            image_data = base64.b64decode(base64_string)
            # CRÍTICO: usa tempfile para criar um arquivo temporário seguro
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=prefix)
            temp_file.write(image_data)
            temp_file.close()
            return temp_file.name

        # 1. Salvar as imagens
        frontal_path = save_base64_to_temp_file(frontal_base64, f"f_{analysis_id}")
        transversal_path = save_base64_to_temp_file(transversal_base64, f"t_{analysis_id}") if transversal_base64 else None
        
        resultados = {
            "id": analysis_id,
            "timestamp": datetime.now().isoformat(),
            "frontal": None,
            "lateral": None,
            "recomendacoes": [],
            "analise_geral": {}
        }

        # 2. Análise da Vista Frontal
        try:
            angles_f, image_b64_f = analyze_posture(frontal_path, 'frontal')
            analise_f = generate_analysis_data(angles_f, 'frontal')
            
            resultados['frontal'] = {
                "angles": angles_f,
                "analise": analise_f['analise'],
                "image_b64": image_b64_f
            }
            resultados['recomendacoes'].extend(analise_f['recomendacoes'])
            resultados['analise_geral'].update(analise_f['analise'])
            
        except (IOError, ValueError) as e:
            print(f"❌ Erro na análise frontal: {str(e)}")
            resultados['frontal'] = {"error": str(e)}

        # 3. Análise da Vista Lateral (se fornecida)
        if transversal_path:
            try:
                angles_l, image_b64_l = analyze_posture(transversal_path, 'lateral')
                analise_l = generate_analysis_data(angles_l, 'lateral')
                
                resultados['lateral'] = {
                    "angles": angles_l,
                    "analise": analise_l['analise'],
                    "image_b64": image_b64_l
                }
                resultados['recomendacoes'].extend(analise_l['recomendacoes'])
                resultados['analise_geral'].update(analise_l['analise'])
                
            except (IOError, ValueError) as e:
                print(f"❌ Erro na análise lateral: {str(e)}")
                resultados['lateral'] = {"error": str(e)}
        
        # 4. Finalização e limpeza
        resultados['recomendacoes'] = list(set(resultados['recomendacoes']))
        
        if not resultados['recomendacoes']:
            resultados['recomendacoes'] = [
                "Os resultados preliminares são bons. Mantenha os hábitos posturais saudáveis e faça exercícios de fortalecimento do core abdominal."
            ]
        
        # Tenta limpar arquivos temporários (CRÍTICO)
        try:
            os.unlink(frontal_path)
            if transversal_path:
                os.unlink(transversal_path)
        except Exception as e:
            print(f"❌ Aviso: Não foi possível deletar arquivos temporários: {str(e)}")
            pass
        
        print(f"✅ Análise {analysis_id} concluída com sucesso!")
        
        return jsonify({
            "success": True,
            "message": "Análise postural concluída!",
            "analysis_id": analysis_id,
            "data": resultados
        })
        
    except Exception as e:
        print(f"❌ Erro na análise: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"Erro no processamento: {str(e)}"
        }), 500

@app.route('/analysis/<analysis_id>', methods=['GET'], strict_slashes=False)
def get_analysis(analysis_id):
    """Endpoint para recuperar análise existente (simulado)."""
    # Esta rota pode ser expandida no futuro para buscar dados em um banco de dados.
    return jsonify({
        "analysis_id": analysis_id,
        "status": "completed",
        "message": "Análise recuperada com sucesso (dados simulados)."
    })

# ==========================================================
# EXECUÇÃO DO FLASK (PYTHON PURO)
# ==========================================================

if __name__ == '__main__':
    # Esta é a configuração obrigatória para Railway/Docker/Outros hosts (PYTHON PURO)
    port = int(os.environ.get('PORT', 8080))
    print(f"🌐 Servidor Railway rodando na porta {port} (Modo Python Puro)")
    app.run(host='0.0.0.0', port=port) 
