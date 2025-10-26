# site/api/app.py

import os
import uuid
import json
import tempfile
import traceback
import numpy as np
import cv2
import mediapipe as mp
from collections import defaultdict

# Importações de Flask
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
# Esta linha habilita o CORS. Agora ela funcionará para /api/callback
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Diretórios para armazenamento temporário de vídeos e resultados
BASE_DIR = tempfile.gettempdir()
RESULT_DIR = os.path.join(BASE_DIR, "analysis_results")
VIDEO_DIR = os.path.join(BASE_DIR, "analysis_videos")
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)

print(f"✅ Backend iniciado. Resultados em: {RESULT_DIR}, Vídeos em: {VIDEO_DIR}")

# Instâncias do MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- CONFIGURAÇÃO DE VÍDEO ---
VIDEO_FOURCC = 'VP80' 
VIDEO_EXTENSION = '.webm'
VIDEO_MIN_SIZE_BYTES = 1000

# --- MATRIZ DE PRECISÃO E LÓGICA DE DECISÃO ---

# Define qual plano é otimizado (P1) para cada métrica
BIOMECHANICAL_PRIORITY_MATRIX = {
    'Angulos_Ombros': 'transversal',
    'Angulos_Quadris': 'transversal',
    'Angulos_Joelhos': 'transversal',
    'Angulo_Coluna': 'transversal',
    'Assimetria_Ombros': 'coronal',
    'Oscilacao_Vertical_Quadril': 'coronal',
    'Oscilacao_Horizontal_Quadril': 'coronal'
}

CONFIDENCE_THRESHOLD = 0.7 # Limite mínimo de confiança

def calculate_distribution_data(temporal_data):
    """
    Calcula dados agregados para gráficos de distribuição a partir dos dados temporais.
    """
    distribution_data = {}
    
    if not temporal_data:
        return distribution_data
    
    # Coleta todos os valores de cada métrica
    metrics_data = {}
    for frame in temporal_data:
        for key, value in frame.items():
            if key not in ['frame', 'tempo_segundos'] and isinstance(value, (int, float)):
                if key not in metrics_data:
                    if key not in metrics_data:
                        metrics_data[key] = []
                    metrics_data[key].append(value)
    
    # Distribuição de Ângulos (histograma)
    angle_metrics = ['angulo_ombro_esquerdo', 'angulo_ombro_direito', 
                    'angulo_quadril_esquerdo', 'angulo_quadril_direito',
                    'angulo_joelho_esquerdo', 'angulo_joelho_direito', 'angulo_coluna']
    
    all_angles = []
    for metric in angle_metrics:
        if metric in metrics_data:
            all_angles.extend(metrics_data[metric])
    
    if all_angles:
        hist, bins = np.histogram(all_angles, bins=20, range=(0, 180))
        distribution_data['distribuicao_angulos'] = {
            'histogram': hist.tolist(),
            'bins': bins.tolist()
        }
    
    # Histograma de Assimetrias
    asymmetry_metrics = ['assimetria_ombros_vertical']
    all_asymmetries = []
    for metric in asymmetry_metrics:
        if metric in metrics_data:
            all_asymmetries.extend(metrics_data[metric])
    
    if all_asymmetries:
        max_val = max(all_asymmetries) if all_asymmetries else 0.2
        hist, bins = np.histogram(all_asymmetries, bins=15, range=(0, max_val))
        distribution_data['histograma_assimetrias'] = {
            'histogram': hist.tolist(),
            'bins': bins.tolist()
        }
    
    return distribution_data

def apply_precision_matrix(analysis_data):
    """
    Seleciona a melhor fonte de dados (coronal ou transversal) para cada métrica
    baseado na matriz de prioridade e na confiança da detecção.
    """
    final_charts = {}
    coronal_data = analysis_data.get('coronal')
    transversal_data = analysis_data.get('transversal')
    
    coronal_confidence = coronal_data.get('confidence_score', 0) if coronal_data else 0
    transversal_confidence = transversal_data.get('confidence_score', 0) if transversal_data else 0

    available_sources = {}
    if coronal_data: available_sources['coronal'] = coronal_confidence
    if transversal_data: available_sources['transversal'] = transversal_confidence

    if not available_sources:
        return {} # Nenhum dado para processar

    # Determina a melhor fonte geral, caso a P1 falhe
    best_overall_source = max(available_sources, key=available_sources.get)

    for metric, p1_source in BIOMECHANICAL_PRIORITY_MATRIX.items():
        chosen_source = None
        
        # 1. Verifica se o plano otimizado (P1) está disponível e tem confiança suficiente
        if p1_source in available_sources and available_sources[p1_source] >= CONFIDENCE_THRESHOLD:
            chosen_source = p1_source
        # 2. Caso contrário, usa a melhor fonte disponível geral
        else:
            chosen_source = best_overall_source

        # Monta o objeto final para o gráfico
        if chosen_source:
            source_data_key = 'temporal_data'
            source_data_list = analysis_data[chosen_source][source_data_key]
            
            final_charts[metric] = {
                "source": chosen_source,
                "confidence": available_sources[chosen_source],
                "data": source_data_list
            }
            
    return final_charts

# --- FUNÇÕES DE ANÁLISE ---

def calculate_angle(a, b, c):
    """Calcula o ângulo entre 3 pontos (em graus)."""
    try:
        a, b, c = np.array(a), np.array(b), np.array(c)
        
        # Verifica se os pontos são válidos
        if np.any(np.isnan(a)) or np.any(np.isnan(b)) or np.any(np.isnan(c)):
            return 0.0
            
        # Vetores BA e BC
        ba = a - b
        bc = c - b
        
        # Produto escalar
        dot_product = np.dot(ba, bc)
        
        # Magnitudes
        mag_ba = np.linalg.norm(ba)
        mag_bc = np.linalg.norm(bc)
        
        # Evita divisão por zero
        if mag_ba == 0 or mag_bc == 0:
            return 0.0
            
        # Cosseno do ângulo
        cosine_angle = dot_product / (mag_ba * mag_bc)
        
        # Limita o valor entre -1 e 1 para evitar erros numéricos
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        
        # Ângulo em graus
        angle = np.degrees(np.arccos(cosine_angle))
        
        return float(angle)
    except Exception as e:
        print(f"Erro no cálculo do ângulo: {e}")
        return 0.0

def analyze_video(video_path, output_video_path):
    """
    Processa um vídeo, extrai dados de postura e retorna os dados temporais
    junto com uma pontuação de confiança média.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

    fourcc = cv2.VideoWriter_fourcc(*VIDEO_FOURCC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    temporal_data, confidence_scores = [], []
    frame_count = 0
    
    with mp_pose.Pose(
        min_detection_confidence=0.5, 
        min_tracking_confidence=0.5,
        model_complexity=1
    ) as pose:
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            # Converte BGR para RGB
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            
            # Processa a imagem com MediaPipe
            results = pose.process(image_rgb)
            
            # Prepara dados do frame
            frame_data = {"frame": frame_count, "tempo_segundos": frame_count / fps}

            # Converte de volta para BGR para desenho
            image_rgb.flags.writeable = True
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # Extrai coordenadas normalizadas
                try:
                    # Ombros
                    l_shoulder = (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, 
                                 landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y)
                    r_shoulder = (landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, 
                                 landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y)
                    
                    # Quadris
                    l_hip = (landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, 
                            landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y)
                    r_hip = (landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, 
                            landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y)
                    
                    # Joelhos
                    l_knee = (landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, 
                             landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y)
                    r_knee = (landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, 
                             landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y)
                    
                    # Tornozelos
                    l_ankle = (landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, 
                              landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y)
                    r_ankle = (landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, 
                              landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y)
                    
                    # Nariz
                    nose = (landmarks[mp_pose.PoseLandmark.NOSE.value].x, 
                           landmarks[mp_pose.PoseLandmark.NOSE.value].y)
                    
                    # Cotovelos (para melhor cálculo de ângulos)
                    l_elbow = (landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, 
                              landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y)
                    r_elbow = (landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, 
                              landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y)
                    
                    # Pontos médios
                    mid_shoulder = ((l_shoulder[0] + r_shoulder[0]) / 2, 
                                   (l_shoulder[1] + r_shoulder[1]) / 2)
                    mid_hip = ((l_hip[0] + r_hip[0]) / 2, 
                              (l_hip[1] + r_hip[1]) / 2)
                    
                    # CÁLCULO DOS ÂNGULOS CORRIGIDOS:
                    
                    # Ângulos dos Ombros (cotovelo - ombro - quadril)
                    frame_data['angulo_ombro_esquerdo'] = calculate_angle(l_elbow, l_shoulder, l_hip)
                    frame_data['angulo_ombro_direito'] = calculate_angle(r_elbow, r_shoulder, r_hip)
                    
                    # Ângulos dos Quadris (ombro - quadril - joelho)
                    frame_data['angulo_quadril_esquerdo'] = calculate_angle(l_shoulder, l_hip, l_knee)
                    frame_data['angulo_quadril_direito'] = calculate_angle(r_shoulder, r_hip, r_knee)
                    
                    # Ângulos dos Joelhos (quadril - joelho - tornozelo)
                    frame_data['angulo_joelho_esquerdo'] = calculate_angle(l_hip, l_knee, l_ankle)
                    frame_data['angulo_joelho_direito'] = calculate_angle(r_hip, r_knee, r_ankle)
                    
                    # Ângulo da Coluna (quadril médio - ombro médio - nariz)
                    frame_data['angulo_coluna'] = calculate_angle(mid_hip, mid_shoulder, nose)
                    
                    # Assimetrias e Oscilações
                    frame_data['assimetria_ombros_vertical'] = abs(l_shoulder[1] - r_shoulder[1])
                    frame_data['oscilacao_vertical_quadril'] = mid_hip[1]
                    frame_data['oscilacao_horizontal_quadril'] = mid_hip[0]
                    
                except Exception as e:
                    print(f"Erro no processamento dos landmarks do frame {frame_count}: {e}")
                    # Valores padrão em caso de erro
                    frame_data.update({
                        'angulo_ombro_esquerdo': 0, 'angulo_ombro_direito': 0,
                        'angulo_quadril_esquerdo': 0, 'angulo_quadril_direito': 0,
                        'angulo_joelho_esquerdo': 0, 'angulo_joelho_direito': 0,
                        'angulo_coluna': 0,
                        'assimetria_ombros_vertical': 0,
                        'oscilacao_vertical_quadril': 0,
                        'oscilacao_horizontal_quadril': 0
                    })
                
                temporal_data.append(frame_data)
                
                # Calcula confiança média
                visibilities = [landmarks[i].visibility for i in range(len(landmarks))]
                confidence_scores.append(np.mean(visibilities))
                
                # Desenha landmarks no frame com cores e estilos melhorados
                mp_drawing.draw_landmarks(
                    image_bgr,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(
                        color=(0, 255, 0), thickness=3, circle_radius=3
                    ),
                    connection_drawing_spec=mp_drawing.DrawingSpec(
                        color=(255, 0, 0), thickness=2, circle_radius=2
                    )
                )
                
                # Adiciona texto com informações do frame
                cv2.putText(image_bgr, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(image_bgr, f"Tempo: {frame_count/fps:.1f}s", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            else:
                # Frame sem landmarks detectados
                frame_data.update({
                    'angulo_ombro_esquerdo': 0, 'angulo_ombro_direito': 0,
                    'angulo_quadril_esquerdo': 0, 'angulo_quadril_direito': 0,
                    'angulo_joelho_esquerdo': 0, 'angulo_joelho_direito': 0,
                    'angulo_coluna': 0,
                    'assimetria_ombros_vertical': 0,
                    'oscilacao_vertical_quadril': 0,
                    'oscilacao_horizontal_quadril': 0
                })
                temporal_data.append(frame_data)
                confidence_scores.append(0)
                
                # Mensagem de nenhum landmark detectado
                cv2.putText(image_bgr, "Nenhum landmark detectado", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Escreve o frame processado no vídeo de saída
            out.write(image_bgr)
            frame_count += 1
            
    cap.release()
    out.release()
    
    avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
    
    print(f"✅ Vídeo processado: {frame_count} frames, confiança média: {avg_confidence:.3f}")
    
    return {"temporal_data": temporal_data, "confidence_score": float(avg_confidence)}

# --- ROTAS DA API ---

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """Endpoint simples para verificação de saúde (health check)."""
    return jsonify({"status": "ok", "message": "Servidor de análise no ar."})

# --- CORREÇÃO DE SSO / ROTA DE CALLBACK (POST) ---
# Esta rota estava faltando, e o navegador não recebia um 200 OK no pré-voo OPTIONS,
# resultando no erro de CORS.

@app.route('/api/callback', methods=['POST'])
def google_sso_callback():
    """
    Recebe o ID Token do Google One Tap e o processa (POST).
    """
    try:
        # Pega a credencial enviada pelo frontend (login.js)
        credential_data = request.get_json() 
        token = credential_data.get('credential')
        
        if not token:
            return jsonify({"success": False, "error": "Token de credencial do Google ausente."}), 400
        
        # ----------------------------------------------------------------------
        # TODO DE SEGURANÇA CRÍTICO: SUBSTITUIR ESTE BLOCO
        # Você deve usar uma biblioteca como google-auth para:
        # 1. Validar a assinatura do ID Token.
        # 2. Verificar se o Audience (seu CLIENT_ID) está correto.
        # 3. Extrair os dados do usuário (email, nome, etc.).
        # 4. Criar uma sessão de login/JWT da sua aplicação e retornar.
        # ----------------------------------------------------------------------
        
        # Resposta de exemplo que resolve o erro de CORS/Pré-Voo:
        return jsonify({
            "success": True, 
            "message": "Credencial recebida e rota funcional.",
            "session_token": "TOKEN_DE_SESSAO_A_SER_GERADO_AQUI" 
        }), 200

    except Exception as e:
        print(f"❌ Erro no callback do Google: {e}")
        return jsonify({"success": False, "error": f"Erro interno do servidor no callback: {e}"}), 500

# --- FIM DA CORREÇÃO ---

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis_route():
    analysis_id = str(uuid.uuid4())
    print(f"\nIniciando nova análise ID: {analysis_id}")
    
    video_coronal = request.files.get('video_coronal')
    video_transversal = request.files.get('video_transversal')

    if not video_coronal:
        return jsonify({"success": False, "error": "O vídeo do plano coronal é obrigatório."}), 400

    analysis_results = {"analysis_id": analysis_id, "analyzed_data": {}}

    try:
        # Processa Plano Coronal (Obrigatório)
        print("📹 Processando vídeo coronal...")
        coronal_original_path = os.path.join(VIDEO_DIR, f"{analysis_id}_coronal_original.mp4")
        video_coronal.save(coronal_original_path)
        coronal_processed_filename = f"{analysis_id}_coronal{VIDEO_EXTENSION}"
        coronal_processed_path = os.path.join(VIDEO_DIR, coronal_processed_filename)
        coronal_analysis = analyze_video(coronal_original_path, coronal_processed_path)
        analysis_results["analyzed_data"]["coronal"] = {
            **coronal_analysis,
            "video_original": os.path.basename(coronal_original_path),
            "video_processed": coronal_processed_filename if os.path.exists(coronal_processed_path) and os.path.getsize(coronal_processed_path) > VIDEO_MIN_SIZE_BYTES else None
        }
        print(f"✅ Coronal processado - Confiança: {coronal_analysis['confidence_score']:.3f}")

        # Processa Plano Transversal (Opcional)
        if video_transversal:
            print("📹 Processando vídeo transversal...")
            transversal_original_path = os.path.join(VIDEO_DIR, f"{analysis_id}_transversal_original.mp4")
            video_transversal.save(transversal_original_path)
            transversal_processed_filename = f"{analysis_id}_transversal{VIDEO_EXTENSION}"
            transversal_processed_path = os.path.join(VIDEO_DIR, transversal_processed_filename)
            transversal_analysis = analyze_video(transversal_original_path, transversal_processed_path)
            analysis_results["analyzed_data"]["transversal"] = {
                **transversal_analysis,
                "video_original": os.path.basename(transversal_original_path),
                "video_processed": transversal_processed_filename if os.path.exists(transversal_processed_path) and os.path.getsize(transversal_processed_path) > VIDEO_MIN_SIZE_BYTES else None
            }
            print(f"✅ Transversal processado - Confiança: {transversal_analysis['confidence_score']:.3f}")
        else:
            print("ℹ️  Nenhum vídeo transversal fornecido")

        # Aplica a matriz de decisão para gráficos temporais
        print("📊 Aplicando matriz de precisão...")
        analysis_results["final_charts"] = apply_precision_matrix(analysis_results["analyzed_data"])
        
        # Calcula dados de distribuição a partir do melhor plano
        best_source = 'coronal'
        if analysis_results["analyzed_data"].get('transversal') and analysis_results["analyzed_data"]['transversal'].get('confidence_score', 0) > analysis_results["analyzed_data"]['coronal'].get('confidence_score', 0):
            best_source = 'transversal'
        
        print(f"📈 Calculando distribuições do plano {best_source}...")
        best_temporal_data = analysis_results["analyzed_data"][best_source]['temporal_data']
        analysis_results["distribution_data"] = calculate_distribution_data(best_temporal_data)
        
        # Salva o resultado final
        result_filepath = os.path.join(RESULT_DIR, f"{analysis_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump({"success": True, "data": analysis_results}, f)
        
        print(f"✅ Análise {analysis_id} concluída com sucesso!")
        return jsonify({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Erro crítico na análise {analysis_id}: {e}\n{error_trace}")
        return jsonify({"success": False, "error": f"Erro interno: {e}", "details": error_trace}), 500

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis_route(analysis_id):
    """Serve o arquivo JSON com os dados da análise."""
    try:
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
    """Serve os arquivos de vídeo com o Content-Type correto."""
    try:
        if not os.path.normpath(os.path.join(VIDEO_DIR, video_filename)).startswith(os.path.realpath(VIDEO_DIR)):
            abort(403)

        mimetype = 'video/webm' if video_filename.endswith('.webm') else 'video/mp4'
        response = send_from_directory(VIDEO_DIR, video_filename, mimetype=mimetype, as_attachment=False)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        print(f"❌ Erro ao servir vídeo '{video_filename}': {e}")
        abort(500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
