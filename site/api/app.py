# site/api/app.py - VERSÃO CORRIGIDA PARA VERCEL
import json
from datetime import datetime

def handler(request):
    try:
        path = request.path
        method = request.method
        
        print(f"📦 Request: {method} {path}")  # Log no Vercel

        # CORS headers
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        }

        # Handle CORS preflight
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": ""
            }

        # Rota /api/health
        if path == "/api/health":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "✅ API Python funcionando no Vercel!",
                    "environment": "vercel-python"
                })
            }

        # Rota /api/process-analysis
        elif path == "/api/process-analysis" and method == "POST":
            print("🎬 Processando upload...")
            
            # ⚠️ NO VERCEL PYTHON: request.files NÃO EXISTE!
            # Vamos simular o processamento por enquanto
            content_length = int(request.headers.get('content-length', 0))
            
            if content_length == 0:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({
                        "success": False, 
                        "error": "Nenhum arquivo recebido"
                    })
                }

            print(f"📦 Tamanho do upload: {content_length} bytes")
            
            # Simular análise
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            result_data = {
                "analysis_id": analysis_id,
                "uploaded_files": ["frontal"],
                "videos": {
                    "frontal_original": f"/api/videos/{analysis_id}_frontal.mp4",
                    "frontal_processed": f"/api/videos/{analysis_id}_frontal_processed.mp4"
                },
                "metrics": {
                    "posture_score": 78,
                    "symmetry_score": 85,
                    "gait_quality": 0,
                    "overall_health": 80
                },
                "debug": {
                    "content_length": content_length,
                    "environment": "vercel-python",
                    "message": "Upload recebido com sucesso! (processamento simulado)"
                }
            }

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "success": True, 
                    "analysisId": analysis_id, 
                    "data": result_data
                })
            }

        # Rota não encontrada
        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({"error": f"Rota não encontrada: {path}"})
            }

    except Exception as e:
        print(f"💥 ERRO: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Erro interno do servidor",
                "details": str(e)
            })
        }
