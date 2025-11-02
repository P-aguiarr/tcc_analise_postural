# Desenvolvimento de um Sistema Integrado para Análise Postural: otimização de seções via aprendizado de máquina e visualização de dados em um dashboard web (TCC)

Este repositório contém o código-fonte e os resultados da validação do meu Trabalho de Conclusão de Curso (TCC), intitulado: **"Desenvolvimento de um Sistema Integrado para Análise Postural: otimização de seções via aprendizado de máquina e visualização de dados em um dashboard web"**.

O projeto consiste em uma plataforma web completa que utiliza Visão Computacional e Aprendizado de Máquina para realizar análises biomecânicas quantitativas a partir de vídeos, visando democratizar o acesso a essa tecnologia para profissionais de saúde e do esporte.

## 1\. Resumo (Abstract)

Este trabalho desenvolveu um sistema integrado para análise postural, utilizando tecnologias de visão computacional. A proposta surgiu diante da crescente demanda por soluções acessíveis e **confiáveis** na área da saúde e do esporte, visando automatizar a detecção de desvios posturais. O sistema desenvolvido realiza a captação de imagens por dispositivos móveis, detecta automaticamente pontos corporais (*landmarks*) e calcula ângulos articulares, oferecendo praticidade e baixo custo. A metodologia contemplou a utilização do modelo pré-treinado **MediaPipe Pose** para extração de pontos-chave do corpo, além do tratamento e análise dos dados gerados. Os resultados foram apresentados em um **dashboard web interativo**, o que permitiu otimizar as sessões de avaliação postural com visualizações claras e objetivas. Ao final, validou-se a **excelente confiabilidade (ICC ≈ 1.000)** do modelo e padronizou-se o processo de captura, oferecendo uma ferramenta funcional para profissionais da saúde.

## 2\. Funcionalidades Principais

  * **Upload de Múltiplos Planos:** Permite o upload de vídeos nos planos **Coronal** (frontal) e **Transversal** (lateral/sagital) para uma análise mais completa.
  * **API de Processamento em Lote:** Um backend robusto em **Flask (Python)** que recebe os vídeos e os processa em segundo plano.
  * **Extração de *Landmarks*:** Utiliza o Google **MediaPipe Pose** para extrair 33 pontos-chave do corpo em cada quadro do vídeo.
  * **Cálculo Biomecânico:** Calcula automaticamente métricas angulares (joelhos, quadris, coluna, ombros) e de simetria (assimetria de ombros, oscilação pélvica).
  * **Dashboard Interativo:** Uma interface web que exibe os resultados da análise, os vídeos processados com o esqueleto sobreposto e gráficos de séries temporais.

## 3\. Arquitetura da Solução

O sistema foi construído em uma arquitetura de microsserviços desacoplada, ideal para a web:

  * **Frontend:** Uma aplicação web estática (HTML, CSS, JavaScript) responsável pela interface do usuário, login, upload de vídeos e visualização do dashboard.
  * **Backend (API):** Uma API RESTful em **Python** e **Flask**, que serve como o "cérebro" do sistema. Ela gerencia o upload, executa a análise de visão computacional e serve os dados JSON para o frontend.
  * **Módulo de IA:** O núcleo da API, que utiliza **OpenCV** para processamento de vídeo e **MediaPipe Pose** para a inferência dos *landmarks*.
  * **Deployment:** O projeto está configurado para deploy em plataformas de nuvem (como Vercel e Railway), utilizando `Dockerfile`, `gunicorn` e `requirements.txt` para garantir a portabilidade.

## 4\. O "Cérebro": A Lógica da Análise (`app.py`)

O coração do projeto está no arquivo `site/api/app.py`. O fluxo de análise é o seguinte:

1.  **Recebimento dos Vídeos:** A rota `/api/process-analysis` recebe os vídeos `video_coronal` e (opcionalmente) `video_transversal`.
2.  **Análise Quadro-a-Quadro:** A função `analyze_video` itera sobre cada quadro de cada vídeo:
      * Extrai os 33 *landmarks* 3D do MediaPipe Pose.
      * Calcula os ângulos 2D necessários (ex: `calculate_angle`) usando `numpy` para a geometria vetorial.
      * Calcula métricas de oscilação e assimetria usando as coordenadas normalizadas dos *landmarks*.
      * Armazena todos os dados em uma série temporal (quadro a quadro).
3.  **A Matriz de Decisão Biomecânica:** Esta é a principal inovação do projeto. Eu criei a `BIOMECHANICAL_PRIORITY_MATRIX`.
      * **O Problema:** Um ângulo de joelho (flexão/extensão) é mal medido em um vídeo frontal. Uma assimetria de ombros é mal medida em um vídeo lateral.
      * **A Solução:** A matriz define qual plano (Coronal ou Transversal) é o "Plano Otimizado (P1)" para cada métrica (ex: `Angulos_Joelhos` usa Transversal, `Assimetria_Ombros` usa Coronal).
      * O sistema então verifica a confiança (`CONFIDENCE_THRESHOLD`) da detecção e escolhe a fonte de dados mais confiável (o Plano P1, ou o melhor plano disponível) para construir os gráficos finais. Isso garante que o relatório utilize sempre a melhor fonte de dados possível.
4.  **Entrega dos Resultados:** A API salva um `.json` com todos os dados, que é então consumido pelo frontend para gerar o dashboard.

## 5\. Validação (A Prova do TCC)

A validação de um sistema de medição é crucial. Como o acesso a um laboratório "padrão-ouro" (como o Vicon) não estava disponível para medir a **acurácia** (erro em cm/graus), meu foco foi provar a **confiabilidade** do sistema.

**Metodologia:** Foi realizada uma **análise de confiabilidade teste-reteste**. Eu gravei o mesmo movimento (caminhada) duas vezes (`teste 1` e `teste 2`) e processei ambos pelo sistema. Os resultados foram então comparados estatisticamente.

**Resultados:** A consistência foi medida usando o **Coeficiente de Correlação Intraclasse (ICC)**, a métrica padrão-ouro para confiabilidade na área da saúde. Os resultados foram **excelentes**, conforme as tabelas abaixo.

A interpretação do ICC (baseada em Koo & Li, 2016) é:

  * **\> 0.90:** Excelente
  * **0.75 – 0.90:** Boa
  * **0.50 – 0.75:** Moderada
  * **\< 0.50:** Ruim

-----

### Tabela 1: Confiabilidade (ICC) para Amplitude de Movimento (ADM)

| Métrica | Média (Graus) | Desvio Padrão (DP) | ICC | Confiabilidade |
| :--- | :--- | :--- | :--- | :--- |
| ADM Mínima - Ombro Esquerdo | 148.918 | 0.004 | 1.000 | Excelente |
| ADM Mínima - Ombro Direito | 144.975 | 0.015 | 1.000 | Excelente |
| ADM Mínima - Quadril Esquerdo | 159.200 | 0.090 | 1.000 | Excelente |
| ADM Mínima - Quadril Direito | 160.039 | 0.089 | 1.000 | Excelente |
| ADM Mínima - Joelho Esquerdo | 148.259 | 0.111 | 1.000 | Excelente |
| ADM Mínima - Joelho Direito | 149.030 | 0.071 | 1.000 | Excelente |
| ADM Mínima - Coluna | 170.198 | 0.024 | 1.000 | Excelente |
| ADM Máxima - Ombro Esquerdo | 178.618 | 0.016 | 1.000 | Excelente |
| ADM Máxima - Ombro Direito | 178.508 | 0.032 | 1.000 | Excelente |
| ADM Máxima - Quadril Esquerdo | 179.317 | 0.021 | 1.000 | Excelente |
| ADM Máxima - Quadril Direito | 179.167 | 0.015 | 1.000 | Excelente |
| ADM Máxima - Joelho Esquerdo | 179.324 | 0.011 | 1.000 | Excelente |
| ADM Máxima - Joelho Direito | 179.317 | 0.043 | 1.000 | Excelente |
| ADM Máxima - Coluna | 179.792 | 0.011 | 1.000 | Excelente |

### Tabela 2: Confiabilidade (ICC) para Posição Angular Média

| Métrica | Média (Graus) | Desvio Padrão (DP) | ICC | Confiabilidade |
| :--- | :--- | :--- | :--- | :--- |
| Ângulo Médio - Ombro Esquerdo | 163.791 | 0.050 | 1.000 | Excelente |
| Ângulo Médio - Ombro Direito | 160.598 | 0.021 | 1.000 | Excelente |
| Ângulo Médio - Quadril Esquerdo | 170.812 | 0.046 | 1.000 | Excelente |
| Ângulo Médio - Quadril Direito | 171.218 | 0.051 | 1.000 | Excelente |
| Ângulo Médio - Joelho Esquerdo | 165.811 | 0.038 | 1.000 | Excelente |
| Ângulo Médio - Joelho Direito | 166.082 | 0.046 | 1.000 | Excelente |
| Ângulo Médio - Coluna | 175.050 | 0.007 | 1.000 | Excelente |

### Tabela 3: Confiabilidade (ICC) para Simetria e Oscilação Pélvica

| Métrica | Média (Val. Norm.) | Desvio Padrão (DP) | ICC | Confiabilidade |
| :--- | :--- | :--- | :--- | :--- |
| Assimetria Vertical dos Ombros | 0.005 | 0.000 | 1.000 | Excelente |
| Oscilação Vertical do Quadril | 0.814 | 0.000 | 1.000 | Excelente |
| Oscilação Horizontal do Quadril | 0.498 | 0.000 | 1.000 | Excelente |

**Conclusão da Validação:** O sistema provou ser **excepcionalmente confiável** (ICC ≈ 1.000, DP ≈ 0.0). Isso significa que a ferramenta é estável e consistente, tornando-a ideal para o acompanhamento longitudinal de pacientes (rastrear a *progressão* ao longo do tempo).

## 6\. Limitações e Trabalhos Futuros

Este TCC atingiu seus objetivos, mas possui limitações claras que abrem caminho para trabalhos futuros:

1.  **2D vs. 3D:** O sistema é primariamente 2D. Ele não captura rotações axiais (ex: rotação do tronco).
2.  **Sem Calibração Métrica:** As métricas de distância (assimetria, oscilação) são em **Valores Normalizados (Val. Norm.)**, não em centímetros. Isso ocorre porque o código não implementa uma rotina de calibração baseada em um objeto de referência.
3.  **Sem Suavização Temporal:** O sistema atualmente não aplica filtros de suavização (como Savitzky-Golay) para reduzir o "ruído" natural da detecção quadro-a-quadro.

**Trabalhos Futuros:**

  * Implementar uma rotina de calibração métrica.
  * Adicionar filtros de suavização temporal (Savgol).
  * Realizar um estudo de **Acurácia** (RMSE/MAE) contra um sistema "padrão-ouro" 3D.

## 7\. Como Executar o Projeto Localmente

### Pré-requisitos

  * **Python 3.11** (recomendado, pois foi o ambiente de desenvolvimento e teste).
  * `pip` (gerenciador de pacotes Python).

### Instalação

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/p-aguiarr/tcc_analise_postural.git
    cd tcc_analise_postural
    ```

2.  **Crie e ative um Ambiente Virtual (Venv):**
    *É crucial usar um ambiente virtual\!*

    ```bash
    # Crie o venv (usando Python 3.11)
    py -3.11 -m venv venv

    # Ative o venv
    # No Windows (CMD):
    .\venv\Scripts\activate.bat
    # No Windows (PowerShell):
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    .\venv\Scripts\activate.ps1
    # No Mac/Linux:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    Com o `(venv)` ativo, instale todas as bibliotecas necessárias.

    ```bash
    pip install -r requirements.txt
    ```

### Executando a API Backend

O backend é o coração do sistema e deve ser executado primeiro. Estou utilizando o Railway para a funcionalidade. 

```bash
# Navegue até a pasta da API e execute o app.py
cd site/api
python app.py
```

O servidor Flask estará rodando (provavelmente em `http://127.0.0.1:8080`).

### Executando o Frontend

O frontend é composto por arquivos HTML estáticos. Estou utilizando o vercel para essa funiconalidade.

1.  Abra a pasta `site` no seu explorador de arquivos.
2.  Dê um duplo clique em `index.html` (para a landing page) ou `login.html` (para ir direto ao login) para abri-los no seu navegador.

A aplicação frontend irá (por padrão) tentar se comunicar com a API backend que você acabou de iniciar.

8. Estrutura do Repositório
O projeto é organizado em duas pastas principais: site/ (toda a aplicação web e API) e Testes/ (todos os scripts e resultados de validação).

.
├── Testes/
│   ├── reliability_data.csv        # Dados brutos (min/max/mean) de cada teste de validação.
│   ├── reliability_log.txt         # Log de execução do script de validação.
│   ├── reliability_report.txt      # O relatório final de confiabilidade (ICC, DP) - SUAS TABELAS.
│   ├── validate_reliability.py     # Script Python para rodar a análise teste-reteste (ICC).
│   └── reliability_videos/
│       └── caminhada/              # Pasta com os vídeos de teste (coronal_1, coronal_2, etc.)
│
├── site/
│   ├── api/                      # O backend (API) em Python/Flask.
│   │   ├── __init__.py
│   │   ├── app.py                # O "CÉREBRO" - Script principal da API com toda a lógica MediaPipe.
│   │   ├── auth/                 # Pastas relacionadas à autenticação (SSO, Vercel).
│   │   ├── blob-register-user.js # Scripts JS para funções serverless (Vercel).
│   │   ├── check-patient-history.js
│   │   └── health.js
│   │
│   ├── img/                      # Todas as imagens e ícones usados no frontend.
│   │
│   ├── configuracoes.html
│   ├── consulta.html             # Página do dashboard de resultados.
│   ├── dashboard.css             # CSS específico do dashboard.
│   ├── dashboard.js              # JavaScript que busca dados da API e desenha os gráficos (Chart.js).
│   ├── global.css
│   ├── historico.html
│   ├── index.html                # A landing page estática do projeto.
│   ├── login.html                # Página de login.
│   ├── login.js                  # JavaScript para autenticação.
│   ├── nova_analise.html         # Página de upload dos vídeos (coronal/transversal).
│   ├── poslogin.html
│   ├── style.css                 # Folha de estilo principal.
│   ├── styleguide.css
│   ├── upload.css                # CSS da página de upload.
│   └── upload.js                 # JavaScript que controla o formulário de upload e chama a API.
│
├── .gitignore
├── Dockerfile                  # Define a imagem de contêiner para deploy (ex: Railway).
├── Procfile                    # Define o comando para iniciar o servidor web (ex: Gunicorn).
├── README.md                   # Este arquivo.
├── analise_completa.py         # (Script de teste ou versão antiga do app.py).
├── backend_app.py              # (Script de teste ou versão antiga do app.py).
├── build.sh                    # Script de build para deploy (ex: Vercel).
├── nixpacks.toml               # Arquivo de configuração para o build (ex: Railway).
├── railway.json                # Configuração de deploy específica da plataforma Railway.
├── requirements.txt            # Lista de todas as dependências Python (pip).
├── runtime.txt                 # Especifica a versão do Python para o deploy.
└── vercel.json                 # Configuração de deploy/rotas específica da plataforma Vercel.
