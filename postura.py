import cv2
import mediapipe as mp
import pandas as pd

# Configurações para evitar warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Silencia TensorFlow

# Configuração do MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)

# Abre o vídeo
video = cv2.VideoCapture("seu_video.mp4")  # Substitua pelo seu vídeo
dados_posturais = []

while video.isOpened():
    ret, frame = video.read()
    if not ret:
        break

    # Processamento do frame
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        dados_frame = {
            "frame": int(video.get(cv2.CAP_PROP_POS_FRAMES)),
            "ombro_esquerdo_x": landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x,
            "ombro_esquerdo_y": landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y,
            # Adicione outros landmarks conforme necessário
        }
        dados_posturais.append(dados_frame)

video.release()

# Salva os dados
df = pd.DataFrame(dados_posturais)
df.to_csv("dados_posturais.csv", index=False)
print("Dados salvos em 'dados_posturais.csv'!")