# Instala o pacote ffmpeg e as bibliotecas essenciais para OpenCV
apt-get update && \
apt-get install -y ffmpeg libsm6 libxext6 && \
rm -rf /var/lib/apt/lists/*
