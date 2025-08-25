import pandas as pd
import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter

# ======================================
# 1. CARREGAR DADOS
# ======================================
df = pd.read_csv("dados_posturais_completos.csv")
print(f"✅ Dados carregados! Total de frames: {len(df)}")
print(f"Colunas disponíveis: {df.columns.tolist()[:10]} ...")

# ======================================
# 2. FUNÇÕES DE ANÁLISE POSTURAL
# ======================================
def calcular_angulo(a, b, c):
    """Calcula ângulo entre 3 pontos (em graus)."""
    ba_x, ba_y = a[0]-b[0], a[1]-b[1]
    bc_x, bc_y = c[0]-b[0], c[1]-b[1]
    produto_escalar = ba_x*bc_x + ba_y*bc_y
    mag_ba = math.sqrt(ba_x**2 + ba_y**2)
    mag_bc = math.sqrt(bc_x**2 + bc_y**2)
    if mag_ba * mag_bc == 0:
        return 0
    cos_angle = produto_escalar / (mag_ba * mag_bc)
    cos_angle = max(min(cos_angle, 1), -1)
    return math.degrees(math.acos(cos_angle))

def calcular_simetria(a_esq, a_dir, ponto_central):
    """Diferença de distâncias entre lados esquerdo/direito em relação ao centro."""
    dist_esq = math.dist(a_esq, ponto_central)
    dist_dir = math.dist(a_dir, ponto_central)
    return abs(dist_esq - dist_dir)

# ======================================
# 3. CÁLCULOS DE ÂNGULOS
# ======================================
angulos = {
    'ombro_esquerdo': [],
    'ombro_direito': [],
    'quadril_esquerdo': [],
    'quadril_direito': [],
    'coluna_cervical': [],
    'coluna_toracica': [],
}

for _, row in df.iterrows():
    # Pontos médios
    ombros = ((row['LEFT_SHOULDER_x'] + row['RIGHT_SHOULDER_x'])/2,
              (row['LEFT_SHOULDER_y'] + row['RIGHT_SHOULDER_y'])/2)
    quadris = ((row['LEFT_HIP_x'] + row['RIGHT_HIP_x'])/2,
               (row['LEFT_HIP_y'] + row['RIGHT_HIP_y'])/2)
    
    # Ângulos ombros
    angulos['ombro_esquerdo'].append(calcular_angulo(
        (row['LEFT_SHOULDER_x'], row['LEFT_SHOULDER_y']),
        (row['LEFT_ELBOW_x'], row['LEFT_ELBOW_y']),
        (row['LEFT_WRIST_x'], row['LEFT_WRIST_y'])
    ))
    angulos['ombro_direito'].append(calcular_angulo(
        (row['RIGHT_SHOULDER_x'], row['RIGHT_SHOULDER_y']),
        (row['RIGHT_ELBOW_x'], row['RIGHT_ELBOW_y']),
        (row['RIGHT_WRIST_x'], row['RIGHT_WRIST_y'])
    ))
    
    # Ângulos quadris
    angulos['quadril_esquerdo'].append(calcular_angulo(
        (row['LEFT_HIP_x'], row['LEFT_HIP_y']),
        (row['LEFT_KNEE_x'], row['LEFT_KNEE_y']),
        (row['LEFT_ANKLE_x'], row['LEFT_ANKLE_y'])
    ))
    angulos['quadril_direito'].append(calcular_angulo(
        (row['RIGHT_HIP_x'], row['RIGHT_HIP_y']),
        (row['RIGHT_KNEE_x'], row['RIGHT_KNEE_y']),
        (row['RIGHT_ANKLE_x'], row['RIGHT_ANKLE_y'])
    ))
    
    # Ângulos coluna
    angulos['coluna_cervical'].append(calcular_angulo(
        (row['LEFT_EAR_x'], row['LEFT_EAR_y']),
        ombros, quadris
    ))
    angulos['coluna_toracica'].append(calcular_angulo(
        ombros, quadris,
        (row['LEFT_KNEE_x'], row['LEFT_KNEE_y'])
    ))

# Adicionar ao DataFrame
for k, v in angulos.items():
    df[f'angulo_{k}'] = v

# ======================================
# 4. ASSIMETRIA
# ======================================
df['assimetria_ombros'] = df.apply(lambda r: calcular_simetria(
    (r['LEFT_SHOULDER_x'], r['LEFT_SHOULDER_y']),
    (r['RIGHT_SHOULDER_x'], r['RIGHT_SHOULDER_y']),
    ((r['LEFT_SHOULDER_x']+r['RIGHT_SHOULDER_x'])/2, (r['LEFT_SHOULDER_y']+r['RIGHT_SHOULDER_y'])/2)
), axis=1)

df['assimetria_quadris'] = df.apply(lambda r: calcular_simetria(
    (r['LEFT_HIP_x'], r['LEFT_HIP_y']),
    (r['RIGHT_HIP_x'], r['RIGHT_HIP_y']),
    ((r['LEFT_HIP_x']+r['RIGHT_HIP_x'])/2, (r['LEFT_HIP_y']+r['RIGHT_HIP_y'])/2)
), axis=1)

# ======================================
# 5. SUAVIZAÇÃO
# ======================================
for col in df.columns:
    if 'angulo_' in col:
        df[f'{col}_suavizado'] = savgol_filter(df[col], window_length=11, polyorder=2)

# ======================================
# 6. ESTATÍSTICAS
# ======================================
print("\n📊 ESTATÍSTICAS:")
for col in df.columns:
    if 'angulo_' in col and '_suavizado' not in col:
        print(f"{col}: média={df[col].mean():.1f}°, std={df[col].std():.1f}°")

print(f"Ombros: {df['assimetria_ombros'].mean():.3f}")
print(f"Quadris: {df['assimetria_quadris'].mean():.3f}")

# ======================================
# 7. VISUALIZAÇÃO GRÁFICA
# ======================================
fig, axes = plt.subplots(3, 2, figsize=(15, 12))
fig.suptitle('Análise Postural (MediaPipe - 33 Landmarks)', fontsize=16)

# Ombros
axes[0, 0].plot(df['frame'], df['angulo_ombro_esquerdo'], 'b-', alpha=0.3, label="Ombro Esq. Bruto")
axes[0, 0].plot(df['frame'], df['angulo_ombro_esquerdo_suavizado'], 'b-', linewidth=2, label="Ombro Esq. Suavizado")
axes[0, 0].plot(df['frame'], df['angulo_ombro_direito'], 'r-', alpha=0.3, label="Ombro Dir. Bruto")
axes[0, 0].plot(df['frame'], df['angulo_ombro_direito_suavizado'], 'r-', linewidth=2, label="Ombro Dir. Suavizado")
axes[0, 0].set_title("Ângulos dos Ombros")
axes[0, 0].set_ylabel("Ângulo (graus)")
axes[0, 0].legend()
axes[0, 0].grid()

# Quadris
axes[0, 1].plot(df['frame'], df['angulo_quadril_esquerdo'], 'b-', alpha=0.3, label="Quadril Esq. Bruto")
axes[0, 1].plot(df['frame'], df['angulo_quadril_esquerdo_suavizado'], 'b-', linewidth=2, label="Quadril Esq. Suavizado")
axes[0, 1].plot(df['frame'], df['angulo_quadril_direito'], 'r-', alpha=0.3, label="Quadril Dir. Bruto")
axes[0, 1].plot(df['frame'], df['angulo_quadril_direito_suavizado'], 'r-', linewidth=2, label="Quadril Dir. Suavizado")
axes[0, 1].set_title("Ângulos dos Quadris")
axes[0, 1].set_ylabel("Ângulo (graus)")
axes[0, 1].legend()
axes[0, 1].grid()

# Coluna
axes[1, 0].plot(df['frame'], df['angulo_coluna_cervical'], 'g-', alpha=0.3, label="Coluna Cervical Bruto")
axes[1, 0].plot(df['frame'], df['angulo_coluna_cervical_suavizado'], 'g-', linewidth=2, label="Coluna Cervical Suavizado")
axes[1, 0].plot(df['frame'], df['angulo_coluna_toracica'], 'm-', alpha=0.3, label="Coluna Torácica Bruto")
axes[1, 0].plot(df['frame'], df['angulo_coluna_toracica_suavizado'], 'm-', linewidth=2, label="Coluna Torácica Suavizado")
axes[1, 0].set_title("Ângulos da Coluna")
axes[1, 0].legend()
axes[1, 0].grid()

# Assimetrias
axes[1, 1].plot(df['frame'], df['assimetria_ombros'], 'c-', label="Assimetria Ombros")
axes[1, 1].plot(df['frame'], df['assimetria_quadris'], 'y-', label="Assimetria Quadris")
axes[1, 1].set_title("Assimetrias")
axes[1, 1].legend()
axes[1, 1].grid()

# Histograma
axes[2, 0].hist(df['angulo_coluna_cervical_suavizado'], bins=30, alpha=0.7, color='green', label="Cervical")
axes[2, 0].hist(df['angulo_coluna_toracica_suavizado'], bins=30, alpha=0.7, color='magenta', label="Torácica")
axes[2, 0].set_title("Distribuição dos Ângulos da Coluna")
axes[2, 0].legend()
axes[2, 0].grid()

# Boxplot assimetrias
axes[2, 1].boxplot([df['assimetria_ombros'], df['assimetria_quadris']], labels=['Ombros', 'Quadris'])
axes[2, 1].set_title("Boxplot Assimetrias")
axes[2, 1].grid()

plt.tight_layout()
plt.savefig("analise_postural_completa.png", dpi=300)
plt.show()

# ======================================
# 8. EXPORTAR RESULTADOS
# ======================================
df.to_csv("analise_postural_completa.csv", index=False)
print("\n🎉 Arquivos gerados:")
print("- analise_postural_completa.png (gráficos)")
print("- analise_postural_completa.csv (dados completos)")
