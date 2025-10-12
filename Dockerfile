# Use uma imagem Python completa para incluir as ferramentas de build necessárias
FROM python:3.9

# Defina o diretório de trabalho
WORKDIR /app

# Instale dependências de sistema (como aquelas que o FFmpeg e o OpenCV frequentemente precisam)
# Isso garante que bibliotecas como o OpenCV sejam instaladas corretamente no build
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copie o arquivo de dependências para aproveitar o cache do Docker
COPY requirements.txt .

# Instale as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da sua aplicação
COPY . .

# CRÍTICO: CORREÇÃO AQUI - Esta sintaxe força o shell a substituir a variável ${PORT}
# Isso corrige o erro 'Error: '$PORT' is not a valid port number.'
CMD ["/bin/sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} site.api.app:app"]
