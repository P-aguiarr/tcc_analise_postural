import pandas as pd
import math
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------
# 1. CARREGAR SEUS DADOS (400+ FRAMES)
# --------------------------------------
df = pd.read_csv("dados_posturais.csv")
print(f"✅ Dados carregados! Total de frames: {len(df)}")

# --------------------------------------
# 2. ESTIMAR POSIÇÕES DO QUADRIL E JOELHO
# (Baseado em proporções anatômicas médias)
# --------------------------------------
# Quadril: ~15% abaixo do ombro no eixo Y
df['quadril_esquerdo_x'] = df['ombro_esquerdo_x'] * 0.98  # Pequeno ajuste horizontal
df['quadril_esquerdo_y'] = df['ombro_esquerdo_y'] + 0.15

# Joelho: ~30% abaixo do quadril no eixo Y
df['joelho_esquerdo_x'] = df['quadril_esquerdo_x'] * 1.02
df['joelho_esquerdo_y'] = df['quadril_esquerdo_y'] + 0.30

# --------------------------------------
# 3. FUNÇÃO PARA CÁLCULO DE ÂNGULOS
# --------------------------------------
def calcular_angulo(a, b, c):
    """Calcula ângulo entre 3 pontos (em graus)"""
    ba_x, ba_y = a[0]-b[0], a[1]-b[1]
    bc_x, bc_y = c[0]-b[0], c[1]-b[1]
    produto_escalar = ba_x*bc_x + ba_y*bc_y
    mag_ba = math.sqrt(ba_x**2 + ba_y**2)
    mag_bc = math.sqrt(bc_x**2 + bc_y**2)
    angulo = math.degrees(math.acos(produto_escalar / (mag_ba * mag_bc)))
    return angulo

# Calcula ângulo ombro-quadril-joelho
df['angulo'] = df.apply(lambda row: calcular_angulo(
    (row['ombro_esquerdo_x'], row['ombro_esquerdo_y']),
    (row['quadril_esquerdo_x'], row['quadril_esquerdo_y']),
    (row['joelho_esquerdo_x'], row['joelho_esquerdo_y'])
), axis=1)

# --------------------------------------
# 4. ANÁLISE E VISUALIZAÇÃO
# --------------------------------------
# Suavização para reduzir ruído
df['angulo_suavizado'] = df['angulo'].rolling(window=5, center=True).mean()

# Estatísticas básicas
print("\n📊 Estatísticas do Ângulo Postural:")
print(f"- Média: {df['angulo'].mean():.1f}°")
print(f"- Variação: {df['angulo'].max()-df['angulo'].min():.1f}°")

# Gráfico
plt.figure(figsize=(12, 6))
plt.plot(df['frame'], df['angulo'], 'b-', alpha=0.3, label="Ângulo Bruto")
plt.plot(df['frame'], df['angulo_suavizado'], 'r-', linewidth=2, label="Ângulo Suavizado")
plt.xlabel("Frame do Vídeo")
plt.ylabel("Ângulo (graus)")
plt.title("Ângulo Postural Estimado (Ombro-Quadril-Joelho)")
plt.legend()
plt.grid()
plt.savefig("angulo_postural.png", dpi=300)
plt.show()

# --------------------------------------
# 5. EXPORTAR RESULTADOS
# --------------------------------------
df.to_csv("dados_com_angulos_estimados.csv", index=False)
print("\n🎉 Arquivos gerados:")
print("- angulo_postural.png (gráfico)")
print("- dados_com_angulos_estimados.csv (dados completos)")