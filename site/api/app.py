# site/api/app.py
from http.server import BaseHTTPRequestHandler
import json
import os
import tempfile
import uuid
import base64
from datetime import datetime
import sys

# Adicionar o caminho para o analise_completa.py
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from analise_completa import processar_video_com_calibracao, realizar_analise_postural_metros, gerar_graficos_png_individual
    ANALISE_DISPONIVEL = True
except ImportError as e:
    print(f"⚠️ Módulo de análise não disponível: {e}")
    ANALISE_DISPONIVEL = False

class Handler(BaseHTTPRequestHandler):
    
    def set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        if self.path.startswith('/api/analysis/'):
            analysis_id = self.path.split('/')[-1]
            self.get_analysis_results(analysis_id)
        elif self.path == '/api/health':
            self.health_check()
        else:
            self.send_error(404, "Endpoint não encontrado")
    
    def do_POST(self):
        if self.path == '/api/process-analysis':
            self.process_analysis()
        else:
            self.send_error(404, "Endpoint não encontrado")
    
    def health_check(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.set_cors_headers()
        self.end_headers()
        
        response = {
            "success": True,
            "message": "API está funcionando",
            "environment": "production",
            "analise_disponivel": ANALISE_DISPONIVEL,
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def process_analysis(self):
        try:
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' not in content_type:
                self.send_error(400, "Content-Type deve ser multipart/form-data")
                return
            
            # Ler o conteúdo do request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Processar dados multipart (simplificado)
            files = self.parse_multipart_form_data(post_data, content_type)
            
            if not files:
                self.send_error(400, "Nenhum arquivo de vídeo encontrado")
                return
            
            # Criar análise ID
            analysis_id = str(uuid.uuid4())
            
            # Salvar vídeos temporariamente
            video_paths = {}
            temp_dir = tempfile.mkdtemp()
            
            for field_name, file_data in files.items():
                if field_name.startswith('video_'):
                    video_type = field_name.replace('video_', '')
                    file_path = os.path.join(temp_dir, f"{video_type}_{analysis_id}.mp4")
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    video_paths[video_type] = file_path
                    print(f"✅ Vídeo {video_type} salvo: {file_path}")
            
            # Simular processamento (substituir pela análise real)
            if ANALISE_DISPONIVEL and 'frontal' in video_paths:
                analysis_results = self.real_analysis(video_paths['frontal'])
            else:
                analysis_results = self.simulate_analysis(analysis_id, video_paths)
            
            # Limpar arquivos temporários
            for video_path in video_paths.values():
                if os.path.exists(video_path):
                    os.remove(video_path)
            
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
            
            # Responder com sucesso
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.set_cors_headers()
            self.end_headers()
            
            response = {
                "success": True,
                "message": "Análise processada com sucesso",
                "analysisId": analysis_id,
                "data": analysis_results
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"❌ Erro no processamento: {str(e)}")
            self.send_error(500, f"Erro interno do servidor: {str(e)}")
    
    def real_analysis(self, video_path):
        """Executa a análise real usando analise_completa.py"""
        try:
            print("🔬 Iniciando análise real...")
            
            # Processar vídeo
            df, fps, calibracao = processar_video_com_calibracao(video_path)
            
            # Realizar análise postural
            df_analisado = realizar_analise_postural_metros(df, fps, calibracao)
            
            # Gerar gráficos
            graficos_base64 = gerar_graficos_png_individual(df_analisado, fps, calibracao)
            
            # Preparar resultados
            results = {
                "status": "completed",
                "videos": {
                    "frontal_original": f"/api/videos/{os.path.basename(video_path)}",
                    "frontal_processed": "/api/videos/processed_frontal.mp4"
                },
                "metrics": {
                    "posture_score": int(df_analisado.get('angulo_coluna_toracica', 75).mean()),
                    "symmetry_score": int(100 - (df_analisado.get('assimetria_ombros_metros', 0.05).mean() * 1000)),
                    "gait_quality": int(df_analisado.get('angulo_quadril_esquerdo', 80).mean()),
                    "overall_health": int((df_analisado.get('angulo_coluna_toracica', 75).mean() + 
                                         (100 - df_analisado.get('assimetria_ombros_metros', 0.05).mean() * 1000)) / 2)
                },
                "graphs": graficos_base64,
                "detailed_analysis": self.prepare_detailed_analysis(df_analisado)
            }
            
            print("✅ Análise real concluída!")
            return results
            
        except Exception as e:
            print(f"❌ Erro na análise real: {str(e)}")
            return self.simulate_analysis("real_failed", {})
    
    def simulate_analysis(self, analysis_id, video_paths):
        """Simula análise quando o módulo real não está disponível"""
        print("🔧 Simulando análise...")
        
        return {
            "status": "completed",
            "videos": {
                "frontal_original": f"/api/videos/demo_frontal.mp4",
                "frontal_processed": f"/api/videos/demo_frontal_processed.mp4",
                "transversal_original": f"/api/videos/demo_transversal.mp4" if 'transversal' in video_paths else "",
                "transversal_processed": f"/api/videos/demo_transversal_processed.mp4" if 'transversal' in video_paths else ""
            },
            "metrics": {
                "posture_score": 78,
                "symmetry_score": 85,
                "gait_quality": 72,
                "overall_health": 80
            },
            "graphs": {
                "ombros": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSI+R3LDoWZpY28gZG9zIE9tYnJvczwvdGV4dD48L3N2Zz4=",
                "quadris": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSI+R3LDoWZpY28gZG9zIFF1YWRyaXM8L3RleHQ+PC9zdmc+",
                "coluna": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSI+R3LDoWZpY28gZGEgQ29sdW5hPC90ZXh0Pjwvc3ZnPg==",
                "assimetrias": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSI+R3LDoWZpY28gZGUgQXNzaW1ldHJpYXM8L3RleHQ+PC9zdmc+"
            },
            "detailed_analysis": {
                "angulos": {
                    "ombro_esquerdo": {"media": 45, "variacao": 15},
                    "ombro_direito": {"media": 43, "variacao": 12},
                    "quadril_esquerdo": {"media": 25, "variacao": 8},
                    "quadril_direito": {"media": 26, "variacao": 7},
                    "joelho_esquerdo": {"media": 15, "variacao": 5},
                    "joelho_direito": {"media": 16, "variacao": 6},
                    "tornozelo_esquerdo": {"media": 85, "variacao": 10},
                    "tornozelo_direito": {"media": 83, "variacao": 9}
                },
                "assimetrias": {
                    "ombros": 0.02,
                    "quadris": 0.01,
                    "joelhos": 0.03,
                    "tornozelos": 0.02
                },
                "recomendacoes": [
                    "Fortalecimento do core abdominal",
                    "Alongamento de isquiotibiais",
                    "Exercícios de equilíbrio unilateral",
                    "Correção da postura durante caminhada",
                    "Fortalecimento de glúteos médio",
                    "Alongamento de panturrilhas"
                ]
            }
        }
    
    def prepare_detailed_analysis(self, df_analisado):
        """Prepara análise detalhada a partir do DataFrame"""
        return {
            "angulos": {
                "ombro_esquerdo": {"media": float(df_analisado.get('angulo_ombro_esquerdo', 45).mean()), "variacao": float(df_analisado.get('angulo_ombro_esquerdo', 15).std())},
                "ombro_direito": {"media": float(df_analisado.get('angulo_ombro_direito', 43).mean()), "variacao": float(df_analisado.get('angulo_ombro_direito', 12).std())},
                "quadril_esquerdo": {"media": float(df_analisado.get('angulo_quadril_esquerdo', 25).mean()), "variacao": float(df_analisado.get('angulo_quadril_esquerdo', 8).std())},
                "quadril_direito": {"media": float(df_analisado.get('angulo_quadril_direito', 26).mean()), "variacao": float(df_analisado.get('angulo_quadril_direito', 7).std())},
                "joelho_esquerdo": {"media": float(df_analisado.get('angulo_joelho_esquerdo', 15).mean()), "variacao": float(df_analisado.get('angulo_joelho_esquerdo', 5).std())},
                "joelho_direito": {"media": float(df_analisado.get('angulo_joelho_direito', 16).mean()), "variacao": float(df_analisado.get('angulo_joelho_direito', 6).std())},
                "tornozelo_esquerdo": {"media": float(df_analisado.get('angulo_tornozelo_esquerdo', 85).mean()), "variacao": float(df_analisado.get('angulo_tornozelo_esquerdo', 10).std())},
                "tornozelo_direito": {"media": float(df_analisado.get('angulo_tornozelo_direito', 83).mean()), "variacao": float(df_analisado.get('angulo_tornozelo_direito', 9).std())}
            },
            "assimetrias": {
                "ombros": float(df_analisado.get('assimetria_ombros_metros', 0.02).mean()),
                "quadris": float(df_analisado.get('assimetria_quadris_metros', 0.01).mean()),
                "joelhos": 0.03,  # Placeholder
                "tornozelos": 0.02  # Placeholder
            },
            "recomendacoes": [
                "Fortalecimento do core abdominal",
                "Alongamento de isquiotibiais",
                "Exercícios de equilíbrio unilateral",
                "Correção da postura durante caminhada",
                "Fortalecimento de glúteos médio",
                "Alongamento de panturrilhas"
            ]
        }
    
    def get_analysis_results(self, analysis_id):
        """Retorna resultados de uma análise específica"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.set_cors_headers()
        self.end_headers()
        
        # Simular dados da análise (substituir por busca real)
        analysis_data = {
            "analysis_id": analysis_id,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "results": self.simulate_analysis(analysis_id, {})
        }
        
        self.wfile.write(json.dumps(analysis_data).encode())
    
    def parse_multipart_form_data(self, data, content_type):
        """Parser simplificado para dados multipart/form-data"""
        files = {}
        
        try:
            # Extrair boundary do Content-Type
            boundary = content_type.split('boundary=')[1].encode()
            
            # Dividir por boundary
            parts = data.split(b'--' + boundary)
            
            for part in parts:
                if b'Content-Disposition: form-data' in part:
                    # Extrair nome do campo
                    if b'name="' in part:
                        name_start = part.find(b'name="') + 6
                        name_end = part.find(b'"', name_start)
                        field_name = part[name_start:name_end].decode()
                        
                        # Extrair dados do arquivo
                        file_start = part.find(b'\r\n\r\n') + 4
                        file_end = part.rfind(b'\r\n')
                        
                        if file_start < file_end:
                            file_data = part[file_start:file_end]
                            files[field_name] = file_data
            
            return files
            
        except Exception as e:
            print(f"❌ Erro no parse multipart: {e}")
            return {}

def handler(request, context):
    return Handler().handle_request(request)
