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

def calcular_inclinacao_horizontal(a, b):
    """Calcula a inclinação horizontal entre dois pontos (em graus)."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.degrees(math.atan2(dy, dx))

# ======================================
# 3. CÁLCULOS DE ÂNGULOS PRINCIPAIS
# ======================================
angulos = {
    'ombro_esquerdo': [],
    'ombro_direito': [],
    'quadril_esquerdo': [],
    'quadril_direito': [],
    'coluna_cervical': [],
    'coluna_toracica': [],
    # Novos ângulos solicitados
    'tornozelo_esquerdo': [],
    'tornozelo_direito': [],
    'joelho_esquerdo': [],
    'joelho_direito': [],
    'quadril_frontal_esquerdo': [],
    'quadril_frontal_direito': [],
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
    
    # Ângulos quadris (visão lateral)
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
    
    # NOVOS ÂNGULOS SOLICITADOS
    
    # Ângulos do tornozelo (visão lateral - dorsiflexão)
    # Ponto de referência para o pé: entre calcanhar e ponta do pé
    ponto_pe_esquerdo = ((row['LEFT_HEEL_x'] + row['LEFT_FOOT_INDEX_x'])/2, 
                         (row['LEFT_HEEL_y'] + row['LEFT_FOOT_INDEX_y'])/2)
    ponto_pe_direito = ((row['RIGHT_HEEL_x'] + row['RIGHT_FOOT_INDEX_x'])/2, 
                        (row['RIGHT_HEEL_y'] + row['RIGHT_FOOT_INDEX_y'])/2)
    
    angulos['tornozelo_esquerdo'].append(calcular_angulo(
        (row['LEFT_KNEE_x'], row['LEFT_KNEE_y']),
        (row['LEFT_ANKLE_x'], row['LEFT_ANKLE_y']),
        ponto_pe_esquerdo
    ))
    
    angulos['tornozelo_direito'].append(calcular_angulo(
        (row['RIGHT_KNEE_x'], row['RIGHT_KNEE_y']),
        (row['RIGHT_ANKLE_x'], row['RIGHT_ANKLE_y']),
        ponto_pe_direito
    ))
    
    # Ângulos do joelho (visão lateral - flexão/extensão)
    angulos['joelho_esquerdo'].append(calcular_angulo(
        (row['LEFT_HIP_x'], row['LEFT_HIP_y']),
        (row['LEFT_KNEE_x'], row['LEFT_KNEE_y']),
        (row['LEFT_ANKLE_x'], row['LEFT_ANKLE_y'])
    ))
    
    angulos['joelho_direito'].append(calcular_angulo(
        (row['RIGHT_HIP_x'], row['RIGHT_HIP_y']),
        (row['RIGHT_KNEE_x'], row['RIGHT_KNEE_y']),
        (row['RIGHT_ANKLE_x'], row['RIGHT_ANKLE_y'])
    ))
    
    # Ângulos do quadril (visão frontal - adução/abdução)
    # Usando a linha dos ombros como referência horizontal
    angulos['quadril_frontal_esquerdo'].append(calcular_inclinacao_horizontal(
        (row['LEFT_HIP_x'], row['LEFT_HIP_y']),
        (row['LEFT_KNEE_x'], row['LEFT_KNEE_y'])
    ))
    
    angulos['quadril_frontal_direito'].append(calcular_inclinacao_horizontal(
        (row['RIGHT_HIP_x'], row['RIGHT_HIP_y']),
        (row['RIGHT_KNEE_x'], row['RIGHT_KNEE_y'])
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
print("=" * 50)

# Estatísticas para ângulos principais
for col in ['angulo_ombro_esquerdo', 'angulo_ombro_direito', 
            'angulo_quadril_esquerdo', 'angulo_quadril_direito',
            'angulo_coluna_cervical', 'angulo_coluna_toracica']:
    print(f"{col}: média={df[col].mean():.1f}°, std={df[col].std():.1f}°, variação={df[col].max()-df[col].min():.1f}°")

# Estatísticas para os novos ângulos
print("\nÂNGULOS SOLICITADOS ESPECIFICAMENTE:")
print("=" * 50)
for col in ['angulo_tornozelo_esquerdo', 'angulo_tornozelo_direito',
            'angulo_joelho_esquerdo', 'angulo_joelho_direito',
            'angulo_quadril_frontal_esquerdo', 'angulo_quadril_frontal_direito']:
    print(f"{col}: média={df[col].mean():.1f}°, std={df[col].std():.1f}°, variação={df[col].max()-df[col].min():.1f}°")

print(f"\nAssimetria Ombros: {df['assimetria_ombros'].mean():.3f} unidades")
print(f"Assimetria Quadris: {df['assimetria_quadris'].mean():.3f} unidades")

# ======================================
# 7. VISUALIZAÇÃO GRÁFICA PRINCIPAL
# ======================================
fig, axes = plt.subplots(3, 2, figsize=(15, 12))
fig.suptitle('Análise Postural Completa (MediaPipe - 33 Landmarks)', fontsize=16, fontweight='bold')

# Ombros
axes[0, 0].plot(df['frame'], df['angulo_ombro_esquerdo_suavizado'], 'b-', linewidth=2, label="Ombro Esquerdo")
axes[0, 0].plot(df['frame'], df['angulo_ombro_direito_suavizado'], 'r-', linewidth=2, label="Ombro Direito")
axes[0, 0].set_title("Ângulos dos Ombros\n(Pontos: Ombro-Cotovelo-Pulso)", fontweight='bold')
axes[0, 0].set_ylabel("Ângulo (graus)")
axes[0, 0].set_xlabel("Número do Frame")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Quadris (visão lateral)
axes[0, 1].plot(df['frame'], df['angulo_quadril_esquerdo_suavizado'], 'b-', linewidth=2, label="Quadril Esquerdo")
axes[0, 1].plot(df['frame'], df['angulo_quadril_direito_suavizado'], 'r-', linewidth=2, label="Quadril Direito")
axes[0, 1].set_title("Ângulos do Quadril (Visão Lateral)\n(Pontos: Quadril-Joelho-Tornozelo)", fontweight='bold')
axes[0, 1].set_ylabel("Ângulo (graus)")
axes[0, 1].set_xlabel("Número do Frame")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Coluna
axes[1, 0].plot(df['frame'], df['angulo_coluna_cervical_suavizado'], 'g-', linewidth=2, label="Coluna Cervical")
axes[1, 0].plot(df['frame'], df['angulo_coluna_toracica_suavizado'], 'm-', linewidth=2, label="Coluna Torácica")
axes[1, 0].set_title("Ângulos da Coluna Vertebral\n(Pontos: Orelha-Ombro-Quadril / Ombro-Quadril-Joelho)", fontweight='bold')
axes[1, 0].set_ylabel("Ângulo (graus)")
axes[1, 0].set_xlabel("Número do Frame")
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# Assimetrias
axes[1, 1].plot(df['frame'], df['assimetria_ombros'], 'c-', label="Assimetria Ombros", linewidth=2)
axes[1, 1].plot(df['frame'], df['assimetria_quadris'], 'y-', label="Assimetria Quadris", linewidth=2)
axes[1, 1].set_title("Assimetrias Corporais\n(Diferença entre lados esquerdo e direito)", fontweight='bold')
axes[1, 1].set_ylabel("Diferença (unidades normalizadas)")
axes[1, 1].set_xlabel("Número do Frame")
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

# Histograma coluna
axes[2, 0].hist(df['angulo_coluna_cervical_suavizado'], bins=30, alpha=0.7, color='green', label="Coluna Cervical")
axes[2, 0].hist(df['angulo_coluna_toracica_suavizado'], bins=30, alpha=0.7, color='magenta', label="Coluna Torácica")
axes[2, 0].set_title("Distribuição dos Ângulos da Coluna", fontweight='bold')
axes[2, 0].set_xlabel("Ângulo (graus)")
axes[2, 0].set_ylabel("Frequência")
axes[2, 0].legend()
axes[2, 0].grid(True, alpha=0.3)

# Boxplot assimetrias
axes[2, 1].boxplot([df['assimetria_ombros'], df['assimetria_quadris']], 
                  labels=['Ombros', 'Quadris'])
axes[2, 1].set_title("Distribuição das Assimetrias", fontweight='bold')
axes[2, 1].set_ylabel("Diferença (unidades normalizadas)")
axes[2, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("analise_postural_completa.png", dpi=300, bbox_inches='tight')

# ======================================
# 8. GRÁFICOS ESPECIALIZADOS SOLICITADOS
# ======================================
print("\n📈 Gerando gráficos especializados...")

# Configurar estilo para os gráficos especializados
plt.style.use('default')
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('Análise Específica de Articulações (MediaPipe - 33 Landmarks)', fontsize=16, fontweight='bold')

# 1. TORNOZELO (visão lateral - movimento dorsiflexão)
axes[0, 0].plot(df['frame'], df['angulo_tornozelo_esquerdo_suavizado'], 'b-', linewidth=2, label="Tornozelo Esquerdo")
axes[0, 0].plot(df['frame'], df['angulo_tornozelo_direito_suavizado'], 'r-', linewidth=2, label="Tornozelo Direito")
axes[0, 0].set_title("Ângulo do Tornozelo (Visão Lateral - Dorsiflexão)\n(Pontos: Joelho-Tornozelo-Pé)", fontweight='bold')
axes[0, 0].set_ylabel("Ângulo (graus)")
axes[0, 0].set_xlabel("Número do Frame")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].axhline(y=90, color='k', linestyle='--', alpha=0.5, label='Ângulo Neutro (90°)')

# 2. JOELHO (visão lateral - extensão e flexão)
axes[0, 1].plot(df['frame'], df['angulo_joelho_esquerdo_suavizado'], 'b-', linewidth=2, label="Joelho Esquerdo")
axes[0, 1].plot(df['frame'], df['angulo_joelho_direito_suavizado'], 'r-', linewidth=2, label="Joelho Direito")
axes[0, 1].set_title("Ângulo do Joelho (Visão Lateral - Flexão/Extensão)\n(Pontos: Quadril-Joelho-Tornozelo)", fontweight='bold')
axes[0, 1].set_ylabel("Ângulo (graus)")
axes[0, 1].set_xlabel("Número do Frame")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# 3. QUADRIL (visão frontal - adução/abdução)
axes[1, 0].plot(df['frame'], df['angulo_quadril_frontal_esquerdo_suavizado'], 'b-', linewidth=2, label="Quadril Esquerdo")
axes[1, 0].plot(df['frame'], df['angulo_quadril_frontal_direito_suavizado'], 'r-', linewidth=2, label="Quadril Direito")
axes[1, 0].set_title("Inclinação do Quadril (Visão Frontal - Adução/Abdução)\n(Pontos: Quadril-Joelho)", fontweight='bold')
axes[1, 0].set_ylabel("Ângulo de Inclinação (graus)")
axes[1, 0].set_xlabel("Número do Frame")
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].axhline(y=0, color='k', linestyle='--', alpha=0.5, label='Linha de Referência (0°)')

# 4. COMPARAÇÃO ENTRE LADOS
lado_direito = [df['angulo_tornozelo_direito_suavizado'].mean(), 
                df['angulo_joelho_direito_suavizado'].mean(), 
                df['angulo_quadril_frontal_direito_suavizado'].mean()]

lado_esquerdo = [df['angulo_tornozelo_esquerdo_suavizado'].mean(), 
                 df['angulo_joelho_esquerdo_suavizado'].mean(), 
                 df['angulo_quadril_frontal_esquerdo_suavizado'].mean()]

x = np.arange(3)
width = 0.35

axes[1, 1].bar(x - width/2, lado_esquerdo, width, label='Lado Esquerdo', color='blue', alpha=0.7)
axes[1, 1].bar(x + width/2, lado_direito, width, label='Lado Direito', color='red', alpha=0.7)
axes[1, 1].set_title('Média dos Ângulos por Articulação e Lado', fontweight='bold')
axes[1, 1].set_ylabel('Ângulo Médio (graus)')
axes[1, 1].set_xlabel('Articulação')
axes[1, 1].set_xticks(x)
axes[1, 1].set_xticklabels(['Tornozelo', 'Joelho', 'Quadril Frontal'])
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("analise_articulacoes_especificas.png", dpi=300, bbox_inches='tight')

# ======================================
# 9. GRÁFICOS ADICIONAIS PARA ANÁLISE DE MARCHA
# ======================================
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('Análise de Marcha e Simetria (MediaPipe - 33 Landmarks)', fontsize=16, fontweight='bold')

# 1. Diferença entre lados para cada articulação
dif_tornozelo = np.abs(df['angulo_tornozelo_esquerdo_suavizado'] - df['angulo_tornozelo_direito_suavizado'])
dif_joelho = np.abs(df['angulo_joelho_esquerdo_suavizado'] - df['angulo_joelho_direito_suavizado'])
dif_quadril = np.abs(df['angulo_quadril_frontal_esquerdo_suavizado'] - df['angulo_quadril_frontal_direito_suavizado'])

axes[0, 0].plot(df['frame'], dif_tornozelo, 'b-', linewidth=2, label="Diferença Tornozelo")
axes[0, 0].plot(df['frame'], dif_joelho, 'r-', linewidth=2, label="Diferença Joelho")
axes[0, 0].plot(df['frame'], dif_quadril, 'g-', linewidth=2, label="Diferença Quadril")
axes[0, 0].set_title("Diferença entre Lados por Articulação", fontweight='bold')
axes[0, 0].set_ylabel("Diferença de Ângulo (graus)")
axes[0, 0].set_xlabel("Número do Frame")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# 2. Histograma das diferenças
axes[0, 1].hist(dif_tornozelo, bins=30, alpha=0.7, color='blue', label="Tornozelo")
axes[0, 1].hist(dif_joelho, bins=30, alpha=0.7, color='red', label="Joelho")
axes[0, 1].hist(dif_quadril, bins=30, alpha=0.7, color='green', label="Quadril")
axes[0, 1].set_title("Distribuição das Diferenças entre Lados", fontweight='bold')
axes[0, 1].set_xlabel("Diferença de Ângulo (graus)")
axes[0, 1].set_ylabel("Frequência")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# 3. Evolução temporal dos ângulos normalizados
# Normalizar para facilitar comparação
def normalizar(dados):
    return (dados - np.min(dados)) / (np.max(dados) - np.min(dados))

axes[1, 0].plot(df['frame'], normalizar(df['angulo_tornozelo_esquerdo_suavizado']), 'b-', linewidth=2, label="Tornozelo Esq. (normalizado)")
axes[1, 0].plot(df['frame'], normalizar(df['angulo_joelho_esquerdo_suavizado']), 'r-', linewidth=2, label="Joelho Esq. (normalizado)")
axes[1, 0].plot(df['frame'], normalizar(df['angulo_quadril_esquerdo_suavizado']), 'g-', linewidth=2, label="Quadril Esq. (normalizado)")
axes[1, 0].set_title("Evolução Temporal Normalizada (Lado Esquerdo)", fontweight='bold')
axes[1, 0].set_ylabel("Valor Normalizado (0-1)")
axes[1, 0].set_xlabel("Número do Frame")
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# 4. Correlação entre articulações
from scipy.stats import pearsonr

corr_tj, _ = pearsonr(df['angulo_tornozelo_esquerdo_suavizado'], df['angulo_joelho_esquerdo_suavizado'])
corr_tq, _ = pearsonr(df['angulo_tornozelo_esquerdo_suavizado'], df['angulo_quadril_esquerdo_suavizado'])
corr_jq, _ = pearsonr(df['angulo_joelho_esquerdo_suavizado'], df['angulo_quadril_esquerdo_suavizado'])

correlacoes = [corr_tj, corr_tq, corr_jq]
nomes = ['Tornozelo-Joelho', 'Tornozelo-Quadril', 'Joelho-Quadril']

axes[1, 1].bar(nomes, correlacoes, color=['blue', 'red', 'green'], alpha=0.7)
axes[1, 1].set_title("Correlação entre Articulações (Lado Esquerdo)", fontweight='bold')
axes[1, 1].set_ylabel("Coeficiente de Correlação de Pearson")
axes[1, 1].set_ylim(-1, 1)
axes[1, 1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1, 1].grid(True, alpha=0.3)

# Adicionar valores nas barras
for i, v in enumerate(correlacoes):
    axes[1, 1].text(i, v/2, f'{v:.2f}', ha='center', va='center', fontweight='bold', color='white')

plt.tight_layout()
plt.savefig("analise_marcha_simetria.png", dpi=300, bbox_inches='tight')

# ======================================
# 10. EXPORTAR RESULTADOS
# ======================================
df.to_csv("analise_postural_completa.csv", index=False)
print("\n🎉 Arquivos gerados:")
print("- analise_postural_completa.png (gráficos principais)")
print("- analise_articulacoes_especificas.png (gráficos especializados)")
print("- analise_marcha_simetria.png (análise de marcha e simetria)")
print("- analise_postural_completa.csv (dados completos)")

# Mostrar todos os gráficos
plt.show()