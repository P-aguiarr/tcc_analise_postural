from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configurações
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_posture(video_path):
    """Função de análise postural usando MediaPipe"""
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
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
    
    # Configuração do vídeo
    cap = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # VideoWriter para output
    output_path = os.path.join(RESULTS_FOLDER, 'video_com_pontos.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    
    dados_posturais = []
    frame_count = 0
    
    with mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)
            
            dados_frame = {"frame": frame_count}
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # Adicionar todos os landmarks aos dados
                for i, landmark in enumerate(landmarks):
                    dados_frame[f"{landmark_names[i]}_x"] = landmark.x
                    dados_frame[f"{landmark_names[i]}_y"] = landmark.y
                    dados_frame[f"{landmark_names[i]}_z"] = landmark.z
                    dados_frame[f"{landmark_names[i]}_visibility"] = landmark.visibility
                
                # Desenhar landmarks no frame
                annotated_frame = frame.copy()
                mp_drawing.draw_landmarks(
                    annotated_frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
                
                out.write(annotated_frame)
            else:
                out.write(frame)
            
            dados_posturais.append(dados_frame)
    
    cap.release()
    out.release()
    
    # Salvar dados em CSV
    csv_path = os.path.join(RESULTS_FOLDER, 'dados_posturais_completos.csv')
    df = pd.DataFrame(dados_posturais)
    df.to_csv(csv_path, index=False)
    
    return {
        'landmarks': dados_posturais,
        'output_video': 'video_com_pontos.mp4',
        'csv_data': 'dados_posturais_completos.csv'
    }

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    if 'video' not in request.files:
        return jsonify({'error': 'Nenhum vídeo enviado'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Processar o vídeo
        results = analyze_posture(filepath)
        
        return jsonify({
            'success': True,
            'results': results,
            'message': 'Análise concluída com sucesso'
        })
    
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

@app.route('/api/results/<filename>')
def get_results(filename):
    """Serve arquivos de resultados"""
    return send_file(os.path.join(app.config['RESULTS_FOLDER'], filename))

if __name__ == '__main__':
    app.run(debug=True, port=5000)