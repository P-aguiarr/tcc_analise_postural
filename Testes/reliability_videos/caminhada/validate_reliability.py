import os
import logging
import pandas as pd
import numpy as np
import tempfile
import pingouin as pg
from collections import defaultdict

# Tenta importar as funções do seu app.py
try:
    from app import (
        analyze_video, 
        BIOMECHANICAL_PRIORITY_MATRIX, 
        CONFIDENCE_THRESHOLD,
        VIDEO_FOURCC,
        VIDEO_EXTENSION
    )
    print("✅ Módulo 'app.py' carregado.")
except ImportError:
    print("❌ ERRO: Não foi possível encontrar 'app.py'.")
    exit()

# --- CONFIGURAÇÃO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, "reliability_videos")
RESULT_DIR = os.path.join(BASE_DIR, "validation_results")
TEMP_VIDEO_DIR = os.path.join(tempfile.gettempdir(), "validation_temp_videos")

# Métricas que vamos extrair de cada série temporal
# Vamos focar nas principais métricas de amplitude e média
METRICS_TO_VALIDATE = [
    'angulo_ombro_esquerdo', 'angulo_ombro_direito',
    'angulo_quadril_esquerdo', 'angulo_quadril_direito',
    'angulo_joelho_esquerdo', 'angulo_joelho_direito',
    'angulo_coluna',
    'assimetria_ombros_vertical',
    'oscilacao_vertical_quadril',
    'oscilacao_horizontal_quadril'
]

# Setup do Logger
if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)
if not os.path.exists(TEMP_VIDEO_DIR): os.makedirs(TEMP_VIDEO_DIR)

log_path = os.path.join(RESULT_DIR, "reliability_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_path, mode='w'),
        logging.StreamHandler()
    ]
)

# --- FUNÇÕES DE ANÁLISE ---

def get_selected_data_for_test(coronal_path, transversal_path, test_name):
    """
    Processa um par de vídeos (coronal, transversal) e aplica a matriz
    de prioridade para retornar um único DataFrame com os dados selecionados.
    """
    logging.info(f"Processando teste: {test_name}")
    analysis_data = {}
    available_sources = {}
    
    # 1. Processa Vídeo Coronal
    try:
        logging.info(f"Processando vídeo coronal: {coronal_path}")
        processed_video_path = os.path.join(TEMP_VIDEO_DIR, f"{test_name}_coronal{VIDEO_EXTENSION}")
        coronal_results = analyze_video(coronal_path, processed_video_path)
        analysis_data['coronal'] = coronal_results
        available_sources['coronal'] = coronal_results.get('confidence_score', 0)
        logging.info(f"Coronal processado. Confiança: {available_sources['coronal']:.3f}")
    except Exception as e:
        logging.error(f"Falha ao processar vídeo coronal: {e}")
        analysis_data['coronal'] = None

    # 2. Processa Vídeo Transversal
    if transversal_path and os.path.exists(transversal_path):
        try:
            logging.info(f"Processando vídeo transversal: {transversal_path}")
            processed_video_path = os.path.join(TEMP_VIDEO_DIR, f"{test_name}_transversal{VIDEO_EXTENSION}")
            transversal_results = analyze_video(transversal_path, processed_video_path)
            analysis_data['transversal'] = transversal_results
            available_sources['transversal'] = transversal_results.get('confidence_score', 0)
            logging.info(f"Transversal processado. Confiança: {available_sources['transversal']:.3f}")
        except Exception as e:
            logging.error(f"Falha ao processar vídeo transversal: {e}")
            analysis_data['transversal'] = None
    else:
        logging.warning(f"Vídeo transversal não fornecido para {test_name}.")
        analysis_data['transversal'] = None

    if not available_sources:
        logging.error("Nenhuma fonte de vídeo pôde ser processada.")
        return None

    # 3. Prepara DataFrames de origem
    df_sources = {}
    if analysis_data['coronal']:
        df_sources['coronal'] = pd.DataFrame(analysis_data['coronal']['temporal_data'])
    if analysis_data['transversal']:
        df_sources['transversal'] = pd.DataFrame(analysis_data['transversal']['temporal_data'])
        
    best_overall_source = max(available_sources, key=available_sources.get)

    # 4. Aplica a Matriz de Decisão
    granular_priority_matrix = {}
    matrix_map = {
        'Angulos_Ombros': ['angulo_ombro_esquerdo', 'angulo_ombro_direito'],
        'Angulos_Quadris': ['angulo_quadril_esquerdo', 'angulo_quadril_direito'],
        'Angulos_Joelhos': ['angulo_joelho_esquerdo', 'angulo_joelho_direito'],
        'Angulo_Coluna': ['angulo_coluna'],
        'Assimetria_Ombros': ['assimetria_ombros_vertical'],
        'Oscilacao_Vertical_Quadril': ['oscilacao_vertical_quadril'],
        'Oscilacao_Horizontal_Quadril': ['oscilacao_horizontal_quadril']
    }
    
    for key_grupo, source_p1 in BIOMECHANICAL_PRIORITY_MATRIX.items():
        for metrica_granular in matrix_map.get(key_grupo, []):
            if metrica_granular in METRICS_TO_VALIDATE:
                granular_priority_matrix[metrica_granular] = source_p1

    df_final_app = pd.DataFrame()
    df_final_app['tempo_segundos'] = df_sources[best_overall_source]['tempo_segundos']
    
    for metric in METRICS_TO_VALIDATE:
        p1_source = granular_priority_matrix.get(metric)
        chosen_source = best_overall_source
        if p1_source in available_sources and available_sources[p1_source] >= CONFIDENCE_THRESHOLD:
            chosen_source = p1_source

        if chosen_source and chosen_source in df_sources and metric in df_sources[chosen_source].columns:
            df_final_app[metric] = df_sources[chosen_source][metric]
        else:
            df_final_app[metric] = 0
            
    return df_final_app

def calculate_summary_statistics(df_data, metric):
    """Calcula estatísticas descritivas (min, max, mean) para uma métrica."""
    # Ignora zeros, que são artefatos de detecção perdida
    valid_data = df_data[metric][df_data[metric] != 0]
    if valid_data.empty:
        return np.nan, np.nan, np.nan
        
    return valid_data.min(), valid_data.max(), valid_data.mean()

def calculate_reliability(df_summary, metric):
    """Calcula Média, Desvio Padrão, CV e ICC para uma métrica."""
    
    # Pega os dados da métrica (ex: 'angulo_joelho_esquerdo_min')
    data = df_summary[metric].dropna()
    
    if len(data) < 2:
        return np.nan, np.nan, np.nan, np.nan, np.nan
        
    # Estatísticas simples
    mean = data.mean()
    std_dev = data.std()
    cv = (std_dev / abs(mean)) * 100 if mean != 0 else np.nan # Coeficiente de Variação (%)
    
    # Preparo para o ICC
    # Precisamos de um DataFrame no formato "longo": (id_teste, metrica, valor)
    df_icc = pd.DataFrame({
        'target': data.values,
        'subject': range(len(data)), # Nossos "sujeitos" são os testes (1, 2, 3)
        'rater': 'system' # O "avaliador" é sempre o sistema
    })
    
    # Calcula o ICC - Tipo ICC2 (Two-way random effects, absolute agreement)
    try:
        # Precisamos de um 'rater' e 'subject' para o ICC, vamos simular
        # O que queremos é a consistência entre os 'subjects' (testes)
        icc_data = df_summary[['test_id', metric]].copy()
        icc_data['rater'] = 'test' # O "avaliador" é o teste
        icc_data = icc_data.rename(columns={'test_id': 'target', metric: 'value'})
        
        # Pingouin precisa de um avaliador "real", vamos usar um truque
        # O que realmente queremos é o ICC1 (One-way random)
        icc = pg.intraclass_corr(data=icc_data, targets='target', raters='rater', ratings='value')
        
        # Vamos usar o ICC1: "Consistência de uma única medida"
        icc_value = icc.set_index('Type').loc['ICC1', 'ICC']
        icc_f = icc.set_index('Type').loc['ICC1', 'F']
        icc_p = icc.set_index('Type').loc['ICC1', 'pval']

    except Exception as e:
        logging.warning(f"Não foi possível calcular o ICC para '{metric}': {e}")
        icc_value, icc_f, icc_p = np.nan, np.nan, np.nan
        
    return mean, std_dev, cv, icc_value


def main():
    logging.info("--- INICIANDO SCRIPT DE VALIDAÇÃO DE CONFIABILIDADE ---")
    
    if not os.path.exists(VIDEO_DIR):
        logging.error(f"Pasta de vídeos não encontrada: {VIDEO_DIR}")
        return

    # 1. Encontra todos os movimentos na pasta (ex: 'agachamento', 'caminhada')
    movements = [d for d in os.listdir(VIDEO_DIR) if os.path.isdir(os.path.join(VIDEO_DIR, d))]
    
    if not movements:
        logging.error(f"Nenhuma pasta de movimento encontrada em {VIDEO_DIR}")
        return
        
    all_summary_data = [] # Lista para todos os dados de sumário
    all_reliability_reports = [] # Lista para todos os relatórios finais
    
    # 2. Itera sobre cada movimento
    for movement in movements:
        logging.info(f"\n--- Processando Movimento: {movement.upper()} ---")
        mov_dir = os.path.join(VIDEO_DIR, movement)
        
        # Encontra os pares de teste (coronal_1/transversal_1, etc.)
        files = os.listdir(mov_dir)
        test_ids = sorted(list(set([f.split('_')[-1].split('.')[0] for f in files if f.endswith('.mp4')])))
        
        if len(test_ids) < 2:
            logging.warning(f"Pelo menos 2 testes são necessários para '{movement}'. Encontrados: {len(test_ids)}. Pulando.")
            continue
            
        logging.info(f"Encontrados {len(test_ids)} testes: {test_ids}")
        
        movement_summary_list = [] # Guarda os sumários de cada teste (1, 2, 3...)
        
        # 3. Itera sobre cada teste (repetição)
        for test_id in test_ids:
            coronal_path = os.path.join(mov_dir, f"coronal_{test_id}.mp4")
            transversal_path = os.path.join(mov_dir, f"transversal_{test_id}.mp4")
            
            if not os.path.exists(coronal_path):
                logging.warning(f"Arquivo coronal não encontrado para {movement} teste {test_id}. Pulando teste.")
                continue
                
            # Processa o par de vídeos
            df_test_data = get_selected_data_for_test(coronal_path, transversal_path, f"{movement}_{test_id}")
            
            if df_test_data is None:
                continue
                
            # 4. Calcula estatísticas descritivas (min, max, mean) para este teste
            summary_row = {'movement': movement, 'test_id': test_id}
            for metric in METRICS_TO_VALIDATE:
                v_min, v_max, v_mean = calculate_summary_statistics(df_test_data, metric)
                summary_row[f"{metric}_min"] = v_min
                summary_row[f"{metric}_max"] = v_max
                summary_row[f"{metric}_mean"] = v_mean
            
            movement_summary_list.append(summary_row)
        
        if not movement_summary_list:
            logging.error(f"Nenhum dado pôde ser processado para o movimento {movement}.")
            continue
            
        all_summary_data.extend(movement_summary_list)
        df_movement_summary = pd.DataFrame(movement_summary_list)
        
        # 5. Agora, calcula a confiabilidade (ICC, Desvio Padrão) entre os testes
        logging.info(f"\n--- RELATÓRIO DE CONFIABILIDADE: {movement.upper()} ---")
        
        reliability_results = []
        # Pega todas as colunas de sumário (ex: 'angulo_joelho_esquerdo_min', 'angulo_coluna_mean')
        summary_metrics = [col for col in df_movement_summary.columns if col not in ['movement', 'test_id']]
        
        for s_metric in summary_metrics:
            mean, std_dev, cv, icc = calculate_reliability(df_movement_summary, s_metric)
            
            # Classificação do ICC
            if pd.isna(icc):
                rating = "N/A"
            elif icc < 0.5:
                rating = "Ruim"
            elif icc < 0.75:
                rating = "Moderada"
            elif icc < 0.90:
                rating = "Boa"
            else:
                rating = "Excelente"
            
            reliability_results.append({
                "Métrica": s_metric,
                "Média": mean,
                "Desvio Padrão (DP)": std_dev,
                "CV (%)": cv,
                "ICC": icc,
                "Confiabilidade": rating
            })
            
        df_reliability_report = pd.DataFrame(reliability_results)
        all_reliability_reports.append(df_reliability_report)
        
        logging.info(f"\n{df_reliability_report.to_string(index=False, float_format='%.3f')}")
        
    # 6. Salva os relatórios finais
    if all_summary_data:
        df_all_data = pd.DataFrame(all_summary_data)
        data_path = os.path.join(RESULT_DIR, "reliability_data.csv")
        df_all_data.to_csv(data_path, index=False, float_format='%.4f')
        logging.info(f"\nDados de sumário de todos os testes salvos em: {data_path}")
        
    if all_reliability_reports:
        report_path = os.path.join(RESULT_DIR, "reliability_report.txt")
        with open(report_path, 'w') as f:
            for i, movement in enumerate(movements):
                if i >= len(all_reliability_reports): break
                f.write(f"--- RELATÓRIO DE CONFIABILIDADE: {movement.upper()} ---\n")
                f.write(all_reliability_reports[i].to_string(index=False, float_format='%.3f'))
                f.write("\n\n")
        logging.info(f"Relatório de confiabilidade completo salvo em: {report_path}")
        
    logging.info("--- VALIDAÇÃO DE CONFIABILIDADE CONCLUÍDA ---")

if __name__ == "__main__":
    main()