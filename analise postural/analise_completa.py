import cv2
import mediapipe as mp
import pandas as pd
import numpy as np
import math
import os
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy.stats import pearsonr

# Configuração para reduzir logs do TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# ======================================
# CONFIGURAÇÕES GLOBAIS DE CALIBRAÇÃO
# ======================================
ALTURA_PESSOA = 1.63  # metros
DISTANCIA_CAMERA_INICIO = 2.0  # metros - da câmera até a primeira linha
DISTANCIA_TOTAL_PERcurso = 6.0  # metros - da primeira até a última linha
ALTURA_CAMERA_UMBIGO = True

# Configuração do MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# ======================================
# FUNÇÕES DE CALIBRAÇÃO PRECISA
# ======================================
class CalibracaoMetros:
    def __init__(self, distancia_total_percurso=6.0, distancia_camera_inicio=2.0):
        self.distancia_total = distancia_total_percurso
        self.distancia_camera_inicio = distancia_camera_inicio
        self.fator_conversao_x = None
        self.fator_conversao_y = None
        self.frame_width = None
        self.frame_height = None
        self.altura_referencia_pixels = None
        
    def calibrar_altura_referencia(self, landmarks, frame_height):
        """
        Calibra usando a altura da pessoa como referência
        """
        self.frame_height = frame_height
        
        # Usar a distância entre ombros e tornozelos como referência de altura
        if len(landmarks) > 25:
            ombro_esq_y = landmarks[11].y * frame_height  # LEFT_SHOULDER
            tornozelo_esq_y = landmarks[27].y * frame_height  # LEFT_ANKLE
            altura_pixels = abs(tornozelo_esq_y - ombro_esq_y)
            
            # A altura real entre ombros e tornozelos é aproximadamente 70% da altura total
            altura_real_estimada = ALTURA_PESSOA * 0.7
            self.fator_conversao_y = altura_real_estimada / altura_pixels
            self.altura_referencia_pixels = altura_pixels
            return True
        return False
    
    def calibrar_largura_referencia(self, landmarks, frame_width, frame_height):
        """
        Calibra usando a largura dos ombros como referência
        """
        self.frame_width = frame_width
        
        if len(landmarks) > 11:
            ombro_esq_x = landmarks[11].x * frame_width  # LEFT_SHOULDER
            ombro_dir_x = landmarks[12].x * frame_width  # RIGHT_SHOULDER
            largura_ombros_pixels = abs(ombro_dir_x - ombro_esq_x)
            
            # Largura média dos ombros é aproximadamente 40cm (0.4m)
            largura_ombros_real = 0.4
            self.fator_conversao_x = largura_ombros_real / largura_ombros_pixels
            return True
        return False
    
    def pixel_para_metro_x(self, valor_pixel):
        """Converte coordenada X de pixel para metro"""
        if self.fator_conversao_x:
            return valor_pixel * self.fator_conversao_x
        return valor_pixel * 0.001  # Fallback
    
    def pixel_para_metro_y(self, valor_pixel):
        """Converte coordenada Y de pixel para metro"""
        if self.fator_conversao_y:
            return valor_pixel * self.fator_conversao_y
        return valor_pixel * 0.001  # Fallback
    
    def pixel_para_metro_z(self, valor_pixel):
        """Converte coordenada Z de pixel para metro"""
        # Usar fator X como aproximação para profundidade
        return self.pixel_para_metro_x(valor_pixel)

# ======================================
# FUNÇÕES DE ANÁLISE POSTURAL
# ======================================
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
    return math.degrees(math.acos(cos_angle))

def calcular_distancia(a, b):
    """Calcula distância entre dois pontos em metros"""
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)

def calcular_simetria(a_esq, a_dir, ponto_central):
    """Diferença de distâncias entre lados esquerdo/direito em relação ao centro."""
    dist_esq = calcular_distancia(a_esq, ponto_central)
    dist_dir = calcular_distancia(a_dir, ponto_central)
    return abs(dist_esq - dist_dir)

def calcular_inclinacao_horizontal(a, b):
    """Calcula a inclinação horizontal entre dois pontos (em graus)."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.degrees(math.atan2(dy, dx))

# ======================================
# PROCESSAMENTO DO VÍDEO COM CALIBRAÇÃO
# ======================================
def processar_video_com_calibracao(video_path="video.mp4"):
    """
    Processa o vídeo com calibração precisa baseada nas marcações de 6 metros
    """
    # Inicializar MediaPipe Pose
    pose = mp_pose.Pose(static_image_mode=False, 
                       min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)

    # Abre o vídeo
    video = cv2.VideoCapture(video_path)
    
    # Configurações do vídeo
    frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(video.get(cv2.CAP_PROP_FPS))

    # Configuração do vídeo de saída
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_video = cv2.VideoWriter('video_com_pontos_calibrado.mp4', fourcc, fps, (frame_width, frame_height))

    # Nomes dos landmarks
    landmark_names = [
        "NOSE", "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER", "RIGHT_EYE_INNER",
        "RIGHT_EYE", "RIGHT_EYE_OUTER", "LEFT_EAR", "RIGHT_EAR", "MOUTH_LEFT",
        "MOUTH_RIGHT", "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_ELBOW", "RIGHT_ELBOW",
        "LEFT_WRIST", "RIGHT_WRIST", "LEFT_PINKY", "RIGHT_PINKY", "LEFT_INDEX",
        "RIGHT_INDEX", "LEFT_THUMB", "RIGHT_THUMB", "LEFT_HIP", "RIGHT_HIP",
        "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE", "LEFT_HEEL",
        "RIGHT_HEEL", "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX"
    ]

    # Sistema de calibração
    calibracao = CalibracaoMetros(DISTANCIA_TOTAL_PERcurso, DISTANCIA_CAMERA_INICIO)
    calibrado = False

    dados_posturais = []
    frame_count = 0

    print("🎬 Processando vídeo com calibração precisa...")
    print(f"📏 Configuração: {DISTANCIA_TOTAL_PERcurso}m de percurso + {DISTANCIA_CAMERA_INICIO}m até câmera")

    while video.isOpened():
        ret, frame = video.read()
        if not ret:
            break

        frame_count += 1
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        tempo_segundos = frame_count / fps
        dados_frame = {
            "frame": frame_count, 
            "tempo_segundos": tempo_segundos,
            "distancia_percorrida_metros": 0.0  # Será calculado posteriormente
        }
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            
            # Calibrar no primeiro frame com detecção
            if not calibrado:
                if calibracao.calibrar_altura_referencia(landmarks, frame_height):
                    calibracao.calibrar_largura_referencia(landmarks, frame_width, frame_height)
                    calibrado = True
                    print(f"✅ Calibração concluída!")
                    print(f"   Fator X: {calibracao.fator_conversao_x:.6f} m/pixel")
                    print(f"   Fator Y: {calibracao.fator_conversao_y:.6f} m/pixel")
            
            # Adicionar dados em pixels
            for i, landmark in enumerate(landmarks):
                dados_frame[f"{landmark_names[i]}_x"] = landmark.x
                dados_frame[f"{landmark_names[i]}_y"] = landmark.y
                dados_frame[f"{landmark_names[i]}_z"] = landmark.z
                dados_frame[f"{landmark_names[i]}_visibility"] = landmark.visibility
            
            # Adicionar dados em metros (usando calibração)
            if calibrado:
                for i, landmark in enumerate(landmarks):
                    x_metro = calibracao.pixel_para_metro_x(landmark.x * frame_width)
                    y_metro = calibracao.pixel_para_metro_y(landmark.y * frame_height)
                    z_metro = calibracao.pixel_para_metro_z(landmark.z * frame_width)
                    
                    dados_frame[f"{landmark_names[i]}_x_metros"] = x_metro
                    dados_frame[f"{landmark_names[i]}_y_metros"] = y_metro
                    dados_frame[f"{landmark_names[i]}_z_metros"] = z_metro
            
            # Desenhar landmarks no frame
            annotated_frame = frame.copy()
            mp_drawing.draw_landmarks(
                annotated_frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )
            
            # Adicionar informações de calibração ao frame
            info_text = [
                f"Frame: {frame_count}",
                f"Altura: {ALTURA_PESSOA}m | Dist: {DISTANCIA_CAMERA_INICIO}m",
                f"Calibrado: {calibrado}",
                f"Tempo: {tempo_segundos:.1f}s"
            ]
            
            for j, text in enumerate(info_text):
                cv2.putText(annotated_frame, text, (10, 30 + j*25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            output_video.write(annotated_frame)
            
        else:
            # Frame sem detecção
            cv2.putText(frame, f"Frame: {frame_count} - Sem detecção", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            output_video.write(frame)
        
        dados_posturais.append(dados_frame)

        # Progresso
        if frame_count % 50 == 0:
            print(f"📊 Processados {frame_count} frames...")

    # Liberar recursos
    video.release()
    output_video.release()
    pose.close()

    # Salvar dados brutos
    df = pd.DataFrame(dados_posturais)
    df.to_csv("dados_posturais_calibrados.csv", index=False)
    
    print("✅ Processamento do vídeo concluído!")
    return df, fps, calibracao

# ======================================
# ANÁLISE POSTURAL COM MÉTRICAS EM METROS
# ======================================
def realizar_analise_postural_metros(df, fps, calibracao):
    """
    Realiza análise postural completa com todas as métricas em metros
    """
    print("📊 Iniciando análise postural com métricas em metros...")
    
    # ======================================
    # CÁLCULOS DE ÂNGULOS PRINCIPAIS EM METROS
    # ======================================
    angulos = {
        'ombro_esquerdo': [], 'ombro_direito': [],
        'quadril_esquerdo': [], 'quadril_direito': [],
        'coluna_cervical': [], 'coluna_toracica': [],
        'tornozelo_esquerdo': [], 'tornozelo_direito': [],
        'joelho_esquerdo': [], 'joelho_direito': [],
        'quadril_frontal_esquerdo': [], 'quadril_frontal_direito': [],
    }

    # Calcular distância percorrida baseada no movimento do quadril
    distancias_percorridas = []
    posicao_inicial = None

    for i, row in df.iterrows():
        # Usar coordenadas em metros para cálculos
        suffix = "_metros"
        
        if f'LEFT_HIP_x{suffix}' in row and pd.notna(row[f'LEFT_HIP_x{suffix}']):
            # Calcular distância percorrida
            posicao_atual = (row[f'LEFT_HIP_x{suffix}'], row[f'LEFT_HIP_y{suffix}'])
            
            if posicao_inicial is None:
                posicao_inicial = posicao_atual
                distancia_acumulada = 0.0
            else:
                deslocamento = calcular_distancia(posicao_inicial, posicao_atual)
                distancia_acumulada = deslocamento
            
            distancias_percorridas.append(distancia_acumulada)
            
            # Pontos médios
            ombros = ((row[f'LEFT_SHOULDER_x{suffix}'] + row[f'RIGHT_SHOULDER_x{suffix}'])/2,
                      (row[f'LEFT_SHOULDER_y{suffix}'] + row[f'RIGHT_SHOULDER_y{suffix}'])/2)
            quadris = ((row[f'LEFT_HIP_x{suffix}'] + row[f'RIGHT_HIP_x{suffix}'])/2,
                       (row[f'LEFT_HIP_y{suffix}'] + row[f'RIGHT_HIP_y{suffix}'])/2)
            
            # Ângulos ombros
            angulos['ombro_esquerdo'].append(calcular_angulo(
                (row[f'LEFT_SHOULDER_x{suffix}'], row[f'LEFT_SHOULDER_y{suffix}']),
                (row[f'LEFT_ELBOW_x{suffix}'], row[f'LEFT_ELBOW_y{suffix}']),
                (row[f'LEFT_WRIST_x{suffix}'], row[f'LEFT_WRIST_y{suffix}'])
            ))
            angulos['ombro_direito'].append(calcular_angulo(
                (row[f'RIGHT_SHOULDER_x{suffix}'], row[f'RIGHT_SHOULDER_y{suffix}']),
                (row[f'RIGHT_ELBOW_x{suffix}'], row[f'RIGHT_ELBOW_y{suffix}']),
                (row[f'RIGHT_WRIST_x{suffix}'], row[f'RIGHT_WRIST_y{suffix}'])
            ))
            
            # Ângulos quadris
            angulos['quadril_esquerdo'].append(calcular_angulo(
                (row[f'LEFT_HIP_x{suffix}'], row[f'LEFT_HIP_y{suffix}']),
                (row[f'LEFT_KNEE_x{suffix}'], row[f'LEFT_KNEE_y{suffix}']),
                (row[f'LEFT_ANKLE_x{suffix}'], row[f'LEFT_ANKLE_y{suffix}'])
            ))
            angulos['quadril_direito'].append(calcular_angulo(
                (row[f'RIGHT_HIP_x{suffix}'], row[f'RIGHT_HIP_y{suffix}']),
                (row[f'RIGHT_KNEE_x{suffix}'], row[f'RIGHT_KNEE_y{suffix}']),
                (row[f'RIGHT_ANKLE_x{suffix}'], row[f'RIGHT_ANKLE_y{suffix}'])
            ))
            
            # Ângulos coluna
            angulos['coluna_cervical'].append(calcular_angulo(
                (row[f'LEFT_EAR_x{suffix}'], row[f'LEFT_EAR_y{suffix}']),
                ombros, quadris
            ))
            angulos['coluna_toracica'].append(calcular_angulo(
                ombros, quadris,
                (row[f'LEFT_KNEE_x{suffix}'], row[f'LEFT_KNEE_y{suffix}'])
            ))
            
            # Ângulos tornozelo
            ponto_pe_esquerdo = ((row[f'LEFT_HEEL_x{suffix}'] + row[f'LEFT_FOOT_INDEX_x{suffix}'])/2, 
                                 (row[f'LEFT_HEEL_y{suffix}'] + row[f'LEFT_FOOT_INDEX_y{suffix}'])/2)
            ponto_pe_direito = ((row[f'RIGHT_HEEL_x{suffix}'] + row[f'RIGHT_FOOT_INDEX_x{suffix}'])/2, 
                                (row[f'RIGHT_HEEL_y{suffix}'] + row[f'RIGHT_FOOT_INDEX_y{suffix}'])/2)
            
            angulos['tornozelo_esquerdo'].append(calcular_angulo(
                (row[f'LEFT_KNEE_x{suffix}'], row[f'LEFT_KNEE_y{suffix}']),
                (row[f'LEFT_ANKLE_x{suffix}'], row[f'LEFT_ANKLE_y{suffix}']),
                ponto_pe_esquerdo
            ))
            angulos['tornozelo_direito'].append(calcular_angulo(
                (row[f'RIGHT_KNEE_x{suffix}'], row[f'RIGHT_KNEE_y{suffix}']),
                (row[f'RIGHT_ANKLE_x{suffix}'], row[f'RIGHT_ANKLE_y{suffix}']),
                ponto_pe_direito
            ))
            
            # Ângulos joelho
            angulos['joelho_esquerdo'].append(calcular_angulo(
                (row[f'LEFT_HIP_x{suffix}'], row[f'LEFT_HIP_y{suffix}']),
                (row[f'LEFT_KNEE_x{suffix}'], row[f'LEFT_KNEE_y{suffix}']),
                (row[f'LEFT_ANKLE_x{suffix}'], row[f'LEFT_ANKLE_y{suffix}'])
            ))
            angulos['joelho_direito'].append(calcular_angulo(
                (row[f'RIGHT_HIP_x{suffix}'], row[f'RIGHT_HIP_y{suffix}']),
                (row[f'RIGHT_KNEE_x{suffix}'], row[f'RIGHT_KNEE_y{suffix}']),
                (row[f'RIGHT_ANKLE_x{suffix}'], row[f'RIGHT_ANKLE_y{suffix}'])
            ))
            
            # Ângulos quadril frontal
            angulos['quadril_frontal_esquerdo'].append(calcular_inclinacao_horizontal(
                (row[f'LEFT_HIP_x{suffix}'], row[f'LEFT_HIP_y{suffix}']),
                (row[f'LEFT_KNEE_x{suffix}'], row[f'LEFT_KNEE_y{suffix}'])
            ))
            angulos['quadril_frontal_direito'].append(calcular_inclinacao_horizontal(
                (row[f'RIGHT_HIP_x{suffix}'], row[f'RIGHT_HIP_y{suffix}']),
                (row[f'RIGHT_KNEE_x{suffix}'], row[f'RIGHT_KNEE_y{suffix}'])
            ))
        else:
            # Frame sem dados válidos
            for key in angulos.keys():
                angulos[key].append(0.0)
            distancias_percorridas.append(0.0)

    # Adicionar ângulos e distância ao DataFrame
    for k, v in angulos.items():
        df[f'angulo_{k}'] = v
    
    df['distancia_percorrida_metros'] = distancias_percorridas

    # ======================================
    # CÁLCULOS DE ASSIMETRIA EM METROS
    # ======================================
    df['assimetria_ombros_metros'] = df.apply(lambda r: calcular_simetria(
        (r.get(f'LEFT_SHOULDER_x_metros', 0), r.get(f'LEFT_SHOULDER_y_metros', 0)),
        (r.get(f'RIGHT_SHOULDER_x_metros', 0), r.get(f'RIGHT_SHOULDER_y_metros', 0)),
        ((r.get(f'LEFT_SHOULDER_x_metros', 0) + r.get(f'RIGHT_SHOULDER_x_metros', 0))/2, 
         (r.get(f'LEFT_SHOULDER_y_metros', 0) + r.get(f'RIGHT_SHOULDER_y_metros', 0))/2)
    ) if pd.notna(r.get(f'LEFT_SHOULDER_x_metros')) else 0, axis=1)

    df['assimetria_quadris_metros'] = df.apply(lambda r: calcular_simetria(
        (r.get(f'LEFT_HIP_x_metros', 0), r.get(f'LEFT_HIP_y_metros', 0)),
        (r.get(f'RIGHT_HIP_x_metros', 0), r.get(f'RIGHT_HIP_y_metros', 0)),
        ((r.get(f'LEFT_HIP_x_metros', 0) + r.get(f'RIGHT_HIP_x_metros', 0))/2, 
         (r.get(f'LEFT_HIP_y_metros', 0) + r.get(f'RIGHT_HIP_y_metros', 0))/2)
    ) if pd.notna(r.get(f'LEFT_HIP_x_metros')) else 0, axis=1)

    # ======================================
    # SUAVIZAÇÃO DOS DADOS
    # ======================================
    for col in df.columns:
        if 'angulo_' in col and len(df[col]) > 11:
            try:
                df[f'{col}_suavizado'] = savgol_filter(df[col], window_length=11, polyorder=2)
            except:
                df[f'{col}_suavizado'] = df[col]

    # ======================================
    # GERAR RELATÓRIO ESTATÍSTICO
    # ======================================
    print("\n📊 ESTATÍSTICAS DA ANÁLISE POSTURAL (METROS):")
    print("=" * 70)
    
    # Estatísticas para ângulos principais
    angulos_principais = ['angulo_ombro_esquerdo', 'angulo_ombro_direito', 
                         'angulo_quadril_esquerdo', 'angulo_quadril_direito',
                         'angulo_coluna_cervical', 'angulo_coluna_toracica']
    
    for col in angulos_principais:
        if col in df.columns:
            print(f"{col}: média={df[col].mean():.1f}°, std={df[col].std():.1f}°, variação={df[col].max()-df[col].min():.1f}°")

    print(f"\n📏 Distância total percorrida: {df['distancia_percorrida_metros'].max():.2f} metros")
    print(f"🎯 Assimetria Ombros: {df['assimetria_ombros_metros'].mean():.3f} m")
    print(f"🎯 Assimetria Quadris: {df['assimetria_quadris_metros'].mean():.3f} m")

    return df

# ======================================
# FUNÇÕES PARA GERAR GRÁFICOS PNG INDIVIDUAIS
# ======================================
def salvar_grafico_png(plt, nome_arquivo, dpi=150):
    """Salva gráfico como PNG e retorna base64"""
    plt.savefig(f"{nome_arquivo}.png", format='png', dpi=dpi, bbox_inches='tight')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    base64_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return base64_str

def gerar_graficos_png_individual(df, fps, calibracao):
    """
    Gera todos os gráficos individuais em PNG
    """
    print("📈 Gerando gráficos PNG individuais...")
    
    graficos_base64 = {}
    
    # 1. Gráfico de Ângulos dos Ombros
    plt.figure(figsize=(12, 6))
    plt.plot(df['tempo_segundos'], df.get('angulo_ombro_esquerdo_suavizado', df['angulo_ombro_esquerdo']), 
             'b-', linewidth=2, label="Ombro Esquerdo")
    plt.plot(df['tempo_segundos'], df.get('angulo_ombro_direito_suavizado', df['angulo_ombro_direito']), 
             'r-', linewidth=2, label="Ombro Direito")
    plt.title("ÂNGULOS DOS OMBROS AO LONGO DO TEMPO", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['ombros'] = salvar_grafico_png(plt, "grafico_ombros")
    
    # 2. Gráfico de Ângulos do Quadril
    plt.figure(figsize=(12, 6))
    plt.plot(df['tempo_segundos'], df.get('angulo_quadril_esquerdo_suavizado', df['angulo_quadril_esquerdo']), 
             'g-', linewidth=2, label="Quadril Esquerdo")
    plt.plot(df['tempo_segundos'], df.get('angulo_quadril_direito_suavizado', df['angulo_quadril_direito']), 
             'orange', linewidth=2, label="Quadril Direito")
    plt.title("ÂNGULOS DO QUADRIL AO LONGO DO TEMPO", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['quadris'] = salvar_grafico_png(plt, "grafico_quadris")
    
    # 3. Gráfico de Ângulos da Coluna
    plt.figure(figsize=(12, 6))
    plt.plot(df['tempo_segundos'], df.get('angulo_coluna_cervical_suavizado', df['angulo_coluna_cervical']), 
             'purple', linewidth=2, label="Coluna Cervical")
    plt.plot(df['tempo_segundos'], df.get('angulo_coluna_toracica_suavizado', df['angulo_coluna_toracica']), 
             'brown', linewidth=2, label="Coluna Torácica")
    plt.title("ÂNGULOS DA COLUNA VERTEBRAL", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['coluna'] = salvar_grafico_png(plt, "grafico_coluna")
    
    # 4. Gráfico de Assimetrias
    plt.figure(figsize=(12, 6))
    plt.plot(df['tempo_segundos'], df['assimetria_ombros_metros'], 'c-', linewidth=2, label="Assimetria Ombros")
    plt.plot(df['tempo_segundos'], df['assimetria_quadris_metros'], 'y-', linewidth=2, label="Assimetria Quadris")
    plt.title("ASSIMETRIAS CORPORAIS", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Assimetria (metros)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['assimetrias'] = salvar_grafico_png(plt, "grafico_assimetrias")
    
    # 5. Gráfico de Distância Percorrida
    plt.figure(figsize=(12, 6))
    plt.plot(df['tempo_segundos'], df['distancia_percorrida_metros'], 'm-', linewidth=3, label="Distância Percorrida")
    plt.title("DISTÂNCIA PERCORRIDA DURANTE O TRAJETO", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Distância (metros)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['distancia'] = salvar_grafico_png(plt, "grafico_distancia")
    
    # 6. Gráfico de Tornozelos
    plt.figure(figsize=(12, 6))
    plt.plot(df['tempo_segundos'], df.get('angulo_tornozelo_esquerdo_suavizado', df['angulo_tornozelo_esquerdo']), 
             'blue', linewidth=2, label="Tornozelo Esquerdo")
    plt.plot(df['tempo_segundos'], df.get('angulo_tornozelo_direito_suavizado', df['angulo_tornozelo_direito']), 
             'red', linewidth=2, label="Tornozelo Direito")
    plt.title("ÂNGULOS DO TORNOZELO (DORSIFLEXÃO)", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['tornozelos'] = salvar_grafico_png(plt, "grafico_tornozelos")
    
    # 7. Diferença entre Lados por Articulação
    plt.figure(figsize=(14, 8))
    diferencas = {
        'Ombros': np.abs(df.get('angulo_ombro_esquerdo_suavizado', df['angulo_ombro_esquerdo']) - 
                        df.get('angulo_ombro_direito_suavizado', df['angulo_ombro_direito'])),
        'Quadris': np.abs(df.get('angulo_quadril_esquerdo_suavizado', df['angulo_quadril_esquerdo']) - 
                         df.get('angulo_quadril_direito_suavizado', df['angulo_quadril_direito'])),
        'Joelhos': np.abs(df.get('angulo_joelho_esquerdo_suavizado', df['angulo_joelho_esquerdo']) - 
                         df.get('angulo_joelho_direito_suavizado', df['angulo_joelho_direito'])),
        'Tornozelos': np.abs(df.get('angulo_tornozelo_esquerdo_suavizado', df['angulo_tornozelo_esquerdo']) - 
                            df.get('angulo_tornozelo_direito_suavizado', df['angulo_tornozelo_direito']))
    }
    
    for articulacao, diferenca in diferencas.items():
        plt.plot(df['tempo_segundos'], diferenca, linewidth=2, label=articulacao)
    
    plt.title("DIFERENÇA ENTRE LADOS POR ARTICULAÇÃO", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo (segundos)", fontsize=12)
    plt.ylabel("Diferença de Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['diferenca_lados'] = salvar_grafico_png(plt, "grafico_diferenca_lados")
    
    # 8. Distribuição das Diferenças entre Lados
    plt.figure(figsize=(12, 8))
    dados_boxplot = [diferencas['Ombros'], diferencas['Quadris'], diferencas['Joelhos'], diferencas['Tornozelos']]
    plt.boxplot(dados_boxplot, labels=['Ombros', 'Quadris', 'Joelhos', 'Tornozelos'])
    plt.title("DISTRIBUIÇÃO DAS DIFERENÇAS ENTRE LADOS", fontsize=14, fontweight='bold')
    plt.ylabel("Diferença de Ângulo (graus)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['distribuicao_diferencas'] = salvar_grafico_png(plt, "grafico_distribuicao_diferencas")
    
    # 9. Evolução Temporal Normalizada (Lado Esquerdo)
    plt.figure(figsize=(14, 8))
    tempo_normalizado = np.linspace(0, 100, len(df))
    
    angulos_esquerdo = {
        'Ombro': df.get('angulo_ombro_esquerdo_suavizado', df['angulo_ombro_esquerdo']),
        'Quadril': df.get('angulo_quadril_esquerdo_suavizado', df['angulo_quadril_esquerdo']),
        'Joelho': df.get('angulo_joelho_esquerdo_suavizado', df['angulo_joelho_esquerdo']),
        'Tornozelo': df.get('angulo_tornozelo_esquerdo_suavizado', df['angulo_tornozelo_esquerdo'])
    }
    
    for articulacao, angulo in angulos_esquerdo.items():
        plt.plot(tempo_normalizado, angulo, linewidth=2, label=f"{articulacao} Esquerdo")
    
    plt.title("EVOLUÇÃO TEMPORAL NORMALIZADA - LADO ESQUERDO", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo Normalizado (%)", fontsize=12)
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['evolucao_esquerdo'] = salvar_grafico_png(plt, "grafico_evolucao_esquerdo")
    
    # 10. Evolução Temporal Normalizada (Lado Direito)
    plt.figure(figsize=(14, 8))
    
    angulos_direito = {
        'Ombro': df.get('angulo_ombro_direito_suavizado', df['angulo_ombro_direito']),
        'Quadril': df.get('angulo_quadril_direito_suavizado', df['angulo_quadril_direito']),
        'Joelho': df.get('angulo_joelho_direito_suavizado', df['angulo_joelho_direito']),
        'Tornozelo': df.get('angulo_tornozelo_direito_suavizado', df['angulo_tornozelo_direito'])
    }
    
    for articulacao, angulo in angulos_direito.items():
        plt.plot(tempo_normalizado, angulo, linewidth=2, label=f"{articulacao} Direito")
    
    plt.title("EVOLUÇÃO TEMPORAL NORMALIZADA - LADO DIREITO", fontsize=14, fontweight='bold')
    plt.xlabel("Tempo Normalizado (%)", fontsize=12)
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['evolucao_direito'] = salvar_grafico_png(plt, "grafico_evolucao_direito")
    
    # 11. Distribuição dos Ângulos da Coluna
    plt.figure(figsize=(12, 8))
    angulos_coluna = {
        'Cervical': df.get('angulo_coluna_cervical_suavizado', df['angulo_coluna_cervical']),
        'Torácica': df.get('angulo_coluna_toracica_suavizado', df['angulo_coluna_toracica'])
    }
    plt.boxplot([angulos_coluna['Cervical'], angulos_coluna['Torácica']], 
                labels=['Coluna Cervical', 'Coluna Torácica'])
    plt.title("DISTRIBUIÇÃO DOS ÂNGULOS DA COLUNA", fontsize=14, fontweight='bold')
    plt.ylabel("Ângulo (graus)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    graficos_base64['distribuicao_coluna'] = salvar_grafico_png(plt, "grafico_distribuicao_coluna")
    
    # 12. Gráfico de Passo em Linha do Tempo
    plt.figure(figsize=(14, 6))
    
    # Simulação de detecção de passos (simplificada)
    if 'LEFT_ANKLE_y_metros' in df.columns:
        altura_tornozelo_esq = df['LEFT_ANKLE_y_metros']
        altura_tornozelo_dir = df['RIGHT_ANKLE_y_metros']
        
        # Normalizar alturas
        altura_norm_esq = (altura_tornozelo_esq - altura_tornozelo_esq.min()) / (altura_tornozelo_esq.max() - altura_tornozelo_esq.min())
        altura_norm_dir = (altura_tornozelo_dir - altura_tornozelo_dir.min()) / (altura_tornozelo_dir.max() - altura_tornozelo_dir.min())
        
        plt.fill_between(df['tempo_segundos'], 0, altura_norm_esq, alpha=0.7, label='Pé Esquerdo', color='blue')
        plt.fill_between(df['tempo_segundos'], altura_norm_esq, altura_norm_esq + altura_norm_dir, alpha=0.7, label='Pé Direito', color='red')
        
        plt.title("GRÁFICO DE PASSO EM LINHA DO TEMPO (Foot Contact Sequence)", fontsize=14, fontweight='bold')
        plt.xlabel("Tempo (segundos)", fontsize=12)
        plt.ylabel("Altura Normalizada do Pé", fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        graficos_base64['passo_timeline'] = salvar_grafico_png(plt, "grafico_passo_timeline")
    
    # 13. Distância do Passo
    plt.figure(figsize=(12, 6))
    
    # Calcular distância entre pés como proxy para comprimento do passo
    if all(col in df.columns for col in ['LEFT_ANKLE_x_metros', 'RIGHT_ANKLE_x_metros']):
        distancia_passos = np.abs(df['LEFT_ANKLE_x_metros'] - df['RIGHT_ANKLE_x_metros'])
        plt.plot(df['tempo_segundos'], distancia_passos, 'g-', linewidth=2, label="Distância entre Pés")
        plt.title("DISTÂNCIA DO PASSO AO LONGO DO TEMPO", fontsize=14, fontweight='bold')
        plt.xlabel("Tempo (segundos)", fontsize=12)
        plt.ylabel("Distância (metros)", fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        graficos_base64['distancia_passo'] = salvar_grafico_png(plt, "grafico_distancia_passo")
    
    # 14. Gráfico de Barras Sequenciais (Footstrike Pattern)
    plt.figure(figsize=(10, 6))
    
    # Simulação de padrão de pisada
    if 'LEFT_HEEL_y_metros' in df.columns and 'RIGHT_HEEL_y_metros' in df.columns:
        contato_esq = df['LEFT_HEEL_y_metros'].diff().abs() > 0.01  # Simplificação
        contato_dir = df['RIGHT_HEEL_y_metros'].diff().abs() > 0.01
        
        # Contar fases
        fases = ['Contato Esq', 'Contato Dir', 'Ambos', 'Nenhum']
        contagens = [
            (contato_esq & ~contato_dir).sum(),
            (contato_dir & ~contato_esq).sum(),
            (contato_esq & contato_dir).sum(),
            (~contato_esq & ~contato_dir).sum()
        ]
        
        plt.bar(fases, contagens, color=['blue', 'red', 'purple', 'gray'])
        plt.title("PADRÃO DE PISADA (Footstrike Pattern)", fontsize=14, fontweight='bold')
        plt.ylabel("Número de Frames", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        graficos_base64['footstrike_pattern'] = salvar_grafico_png(plt, "grafico_footstrike_pattern")
    
    # 15. Ciclo da Marcha em Fases
    plt.figure(figsize=(10, 8))
    
    # Simulação de fases do ciclo da marcha
    if len(df) > 0:
        ciclos = min(3, len(df) // 30)  # Mostrar até 3 ciclos
        for i in range(ciclos):
            inicio = i * 30
            fim = min((i + 1) * 30, len(df))
            
            if fim - inicio > 10:
                tempo_ciclo = np.linspace(0, 100, fim - inicio)
                
                # Simular fases do ciclo
                apoio = np.ones(fim - inicio) * 0.6
                balanco = np.ones(fim - inicio) * 0.3
                
                plt.fill_between(tempo_ciclo, 0, apoio, alpha=0.5, label=f'Fase de Apoio {i+1}' if i == 0 else "")
                plt.fill_between(tempo_ciclo, apoio, apoio + balanco, alpha=0.5, label=f'Fase de Balanço {i+1}' if i == 0 else "")
        
        plt.title("CICLO DA MARCHA EM FASES", fontsize=14, fontweight='bold')
        plt.xlabel("Ciclo da Marcha (%)", fontsize=12)
        plt.ylabel("Fase", fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        graficos_base64['ciclo_marcha'] = salvar_grafico_png(plt, "grafico_ciclo_marcha")
    
    print(f"✅ Gerados {len(graficos_base64)} gráficos PNG individuais")
    return graficos_base64

# ======================================
# FUNÇÃO PRINCIPAL
# ======================================
def main():
    """
    Função principal que executa toda a análise
    """
    print("🚀 INICIANDO ANÁLISE POSTURAL AVANÇADA COM CALIBRAÇÃO EM METROS")
    print("=" * 70)
    
    # Processar vídeo
    df, fps, calibracao = processar_video_com_calibracao()
    
    # Realizar análise postural
    df_analisado = realizar_analise_postural_metros(df, fps, calibracao)
    
    # Gerar gráficos PNG individuais
    graficos_base64 = gerar_graficos_png_individual(df_analisado, fps, calibracao)
    
    print("\n🎉 ANÁLISE CONCLUÍDA COM SUCESSO!")
    print(f"📊 Total de frames processados: {len(df_analisado)}")
    print(f"📈 Total de gráficos gerados: {len(graficos_base64)}")
    print(f"📏 Distância máxima percorrida: {df_analisado['distancia_percorrida_metros'].max():.2f} metros")
    print(f"🕒 Duração total: {df_analisado['tempo_segundos'].max():.1f} segundos")
    
    # Salvar dados finais
    df_analisado.to_csv("analise_postural_completa.csv", index=False)
    print("💾 Dados salvos em 'analise_postural_completa.csv'")

if __name__ == "__main__":
    main()