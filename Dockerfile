# Use uma imagem Python completa para incluir as ferramentas de build necessárias
FROM python:3.9

# Defina o diretório de trabalho
WORKDIR /app

# Instale dependências de sistema (como aquelas que o FFmpeg e o OpenCV frequentemente precisam)
# Isso resolve o erro de 'setup' que você viu no log do Nixpacks
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copie o arquivo de dependências para aproveitar o cache do Docker
COPY requirements.txt .

# Instale as dependências Python
# O comando --no-cache-dir economiza espaço
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da sua aplicação
COPY . .

# Comando de inicialização, baseado no seu log (gunicorn)
CMD gunicorn --bind 0.0.0.0:$PORT site.api.app:app
