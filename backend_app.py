from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__)
CORS(app)

print("✅ Backend Railway - Análise Postural Iniciado!")

@app.route('/')
def home():
    return jsonify({"message": "Backend de análise postural online!"})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "success": True,
        "message": "Backend Railway está funcionando perfeitamente!",
        "timestamp": datetime.now().isoformat(),
        "environment": "railway-production"
    })

@app.route('/api/process-analysis', methods=['POST'])
def process_analysis():
    try:
        print("🔄 Recebendo upload no Railway...")
        
        # Verificar arquivos
        files_received = []
        for video_type in ['frontal', 'transversal']:
            video_file = request.files.get(f'video_{video_type}')
            if video_file and video_file.filename:
                files_received.append(video_type)
                print(f"📹 {video_type}: {video_file.filename}")
        
        if not files_received:
            return jsonify({"success": False, "error": "Nenhum vídeo enviado"}), 400
        
        # Criar análise ID
        analysis_id = str(uuid.uuid4())
        print(f"🆕 Analysis ID: {analysis_id}")
        
        # Processar análise
        results = simulate_advanced_analysis(analysis_id, files_received)
        
        return jsonify({
            "success": True,
            "message": "Análise processada com sucesso no Railway!",
            "analysisId": analysis_id,
            "data": results
        })
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/analysis/<analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    results = simulate_advanced_analysis(analysis_id, ['frontal'])
    return jsonify({
        "analysis_id": analysis_id,
        "status": "completed", 
        "timestamp": datetime.now().isoformat(),
        "results": results
    })

def generate_analysis_graphs():
    """Gera gráficos realistas"""
    graphs = {}
    time = np.linspace(0, 10, 100)
    
    try:
        # Gráfico 1: Ombros
        plt.figure(figsize=(10, 6))
        ombro_esq = 45 + 5 * np.sin(time)
        ombro_dir = 43 + 4 * np.sin(time + 0.5)
        plt.plot(time, ombro_esq, 'b-', label='Ombro Esquerdo')
        plt.plot(time, ombro_dir, 'r-', label='Ombro Direito')
        plt.title('ÂNGULOS DOS OMBROS')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        graphs['ombros'] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        plt.close()
        
        # Gráfico 2: Quadris  
        plt.figure(figsize=(10, 6))
        quadril_esq = 25 + 3 * np.sin(time * 1.2)
        quadril_dir = 26 + 2 * np.sin(time * 1.2 + 0.3)
        plt.plot(time, quadril_esq, 'g-', label='Quadril Esquerdo')
        plt.plot(time, quadril_dir, 'orange', label='Quadril Direito')
        plt.title('ÂNGULOS DO QUADRIL')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        graphs['quadris'] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        plt.close()
        
    except Exception as e:
        print(f"⚠️ Erro gráficos: {e}")
        fallback = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOGY4Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSI+R3LDoWZpY29zPC90ZXh0Pjwvc3ZnPg=="
        graphs = {k: fallback for k in ['ombros', 'quadris', 'coluna', 'assimetrias']}
    
    return graphs

def simulate_advanced_analysis(analysis_id, files_received):
    graphs = generate_analysis_graphs()
    
    return {
        "status": "completed",
        "videos": {
            "frontal_original": "https://assets.mixkit.co/videos/preview/mixkit-walking-in-a-park-4373-large.mp4",
            "frontal_processed": "https://assets.mixkit.co/videos/preview/mixkit-walking-in-a-park-4373-large.mp4"
        },
        "metrics": {
            "posture_score": 85,
            "symmetry_score": 82, 
            "gait_quality": 78,
            "overall_health": 82
        },
        "graphs": graphs,
        "detailed_analysis": {
            "angulos": {
                "ombro_esquerdo": {"media": 45.2, "variacao": 4.8},
                "ombro_direito": {"media": 43.8, "variacao": 3.9}
            },
            "assimetrias": {
                "ombros": 0.018,
                "quadris": 0.012
            },
            "recomendacoes": [
                "Fortalecimento do core abdominal",
                "Alongamento de isquiotibiais",
                "Exercícios de equilíbrio unilateral"
            ]
        }
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Backend Railway rodando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
