import cv2
import mediapipe as mp
import pandas as pd
import numpy as np
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Configuração do MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

pose = mp_pose.Pose(static_image_mode=False, 
                   min_detection_confidence=0.5,
                   min_tracking_confidence=0.5)

# Abre o vídeo
video_path = "seu_video.mp4"  # Substitua pelo seu vídeo
video = cv2.VideoCapture(video_path)

# Configuração do vídeo de saída
frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(video.get(cv2.CAP_PROP_FPS))

# Define o codec e cria o VideoWriter
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output_video = cv2.VideoWriter('video_com_pontos.mp4', fourcc, fps, (frame_width, frame_height))

dados_posturais = []
frame_count = 0

# Nomes dos landmarks para referência
landmark_names = [
    "NOSE", "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER", "RIGHT_EYE_INNER",
    "RIGHT_EYE", "RIGHT_EYE_OUTER", "LEFT_EAR", "RIGHT_EAR", "MOUTH_LEFT",
    "MOUTH_RIGHT", "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST", "LEFT_PINKY", "RIGHT_PINKY", "LEFT_INDEX",
    "RIGHT_INDEX", "LEFT_THUMB", "RIGHT_THUMB", "LEFT_HIP", "RIGHT_HIP",
    "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE", "LEFT_HEEL",
    "RIGHT_HEEL", "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX"
]

while video.isOpened():
    ret, frame = video.read()
    if not ret:
        break

    frame_count += 1
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)

    dados_frame = {"frame": frame_count}
    
    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        
        # Adiciona todos os 33 landmarks aos dados
        for i, landmark in enumerate(landmarks):
            dados_frame[f"{landmark_names[i]}_x"] = landmark.x
            dados_frame[f"{landmark_names[i]}_y"] = landmark.y
            dados_frame[f"{landmark_names[i]}_z"] = landmark.z
            dados_frame[f"{landmark_names[i]}_visibility"] = landmark.visibility
        
        # Desenha os landmarks no frame
        annotated_frame = frame.copy()
        mp_drawing.draw_landmarks(
            annotated_frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        # Adiciona texto com informações
        cv2.putText(annotated_frame, f"Frame: {frame_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_frame, f"Pontos detectados: 33/33", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Escreve o frame no vídeo de saída
        output_video.write(annotated_frame)
        
    else:
        # Se não detectar landmarks, grava o frame original
        cv2.putText(frame, f"Frame: {frame_count} - Nenhum ponto detectado", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        output_video.write(frame)
    
    dados_posturais.append(dados_frame)

# Libera os recursos
video.release()
output_video.release()
pose.close()

# Salva os dados em CSV
df = pd.DataFrame(dados_posturais)
df.to_csv("dados_posturais_completos.csv", index=False)

# Gera um arquivo de resumo
resumo = f"""
ANÁLISE POSTURAL COMPLETA
=========================
Total de frames: {frame_count}
Frames com detecção: {len([x for x in dados_posturais if any('NOSE_x' in key for key in x)])}
Pontos capturados: 33 landmarks por frame

Arquivos gerados:
- dados_posturais_completos.csv (dados detalhados)
- video_com_pontos.mp4 (visualização)

Landmarks capturados:
{', '.join(landmark_names)}
"""

with open("resumo_analise.txt", "w", encoding="utf-8") as f:
    f.write(resumo)

print("Processamento concluído!")
print(resumo)
print("Arquivos salvos:")
print("- dados_posturais_completos.csv")
print("- video_com_pontos.mp4")
print("- resumo_analise.txt")