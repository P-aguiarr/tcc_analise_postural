# site/api/app.py - TESTE MÍNIMO
def handler(request):
    print("✅ Python handler executando!")
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": '{"status": "success", "message": "Python funcionando!"}'
    }
