const backendBaseUrl = "https://tccanalisepostural-production.up.railway.app";
let currentAnalysisData = null;
let currentAnalysisId = null;

// A função handleVideoError foi exposta no escopo global para ser usada em onerror do HTML
window.handleVideoError = function(videoElement, type) {
    console.error(`[FRONTEND ERRO] Falha ao carregar vídeo ${type}.`);
    
    const parentDiv = videoElement.closest('.video-card');
    if (parentDiv) {
        const mediaBox = parentDiv.querySelector('.media-box');
        if (mediaBox) {
            mediaBox.innerHTML = `
                <div class="media-content rounded-lg flex flex-col items-center justify-center video-placeholder">
                    <i data-lucide="alert-triangle" class="w-6 h-6 text-red-500 mb-2"></i>
                    <p class="text-sm text-red-600 font-semibold">${type} indisponível.</p>
                    <p class="text-xs text-red-400">O servidor falhou ao carregar o recurso.</p>
                </div>`;
            if(typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons(); 
            }
        }
    }
}

function populateVideosUI(analysisId, apiResponse) {
    const videoContainer = document.getElementById("video-container");
    videoContainer.innerHTML = '';
    
    // Verifica se os dados da análise frontal e a imagem B64 do frame foram retornados
    if (apiResponse.data.frontal && apiResponse.data.frontal.image_b64) {
        const frameB64 = apiResponse.data.frontal.image_b64;
        
        // Exibe o frame inicial processado em Base64
        videoContainer.innerHTML += `
            <div class="bg-white p-4 rounded-xl shadow-sm video-card">
                <h3 class="font-bold mb-2">Plano Coronal (Frame Processado)</h3>
                <div class="media-box">
                    <img class="media-content rounded-lg" 
                        src="data:image/png;base64,${frameB64}" 
                        alt="Frame Processado" />
                </div>
            </div>`;
    } else {
        videoContainer.innerHTML = '<div class="bg-white p-4 rounded-xl shadow-sm md:col-span-2"><p class="text-red-500">Falha ao carregar frame da análise. O processamento pode ter falhado.</p></div>';
    }
    document.getElementById('analysisSubtitle').textContent = `Resultados da Análise ID: ${analysisId}`;
}

async function fetchAnalysisData(analysisId) {
    try {
        if (!analysisId) throw new Error("ID da análise não foi encontrado na URL.");
        
        // Rota que o backend original usava para recuperar o resultado
        const apiUrl = `${backendBaseUrl}/api/analysis/${analysisId}`; 
        
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error(`Erro na rede: ${response.status}`);
        
        const apiResponse = await response.json();
        
        if (!apiResponse.analysis_id) {
             throw new Error(`Resposta do servidor incompleta. ID da análise ausente.`);
        }

        return {
            analysis_id: apiResponse.analysis_id,
            // A estrutura de dados deve corresponder ao que o backend retorna (mesmo que simulado)
            data: apiResponse.data 
        };
        
    } catch (error) {
        console.error(`[FRONTEND ERRO CRÍTICO] Falha ao buscar análise: ${error.message}`);
        document.getElementById('loading-indicator').innerHTML = `<h2 class="text-red-500 font-bold">Falha ao carregar dados da análise. (Verifique o console F12 e as rotas do Railway)</h2>`;
        return null;
    }
}
        
function cleanupAnalysis(id) {
    // Função mantida para compatibilidade, mas desativada por padrão (cleanupAnalysis(id))
}

window.addEventListener('load', async () => {
    const loadingIndicator = document.getElementById('loading-indicator');
    const tabContent = document.getElementById('tab-content');
    const params = new URLSearchParams(window.location.search);
    const analysisId = params.get('analysis_id');
    
    if (!analysisId) {
        loadingIndicator.innerHTML = '<h2 class="text-xl font-semibold text-red-500">ID da Análise não encontrado na URL.</h2>';
        return;
    }
    
    currentAnalysisId = analysisId; 

    const apiResponseWrapper = await fetchAnalysisData(analysisId);
    
    // A chave do seu sucesso: verificar se a resposta possui dados
    if (apiResponseWrapper && apiResponseWrapper.data && apiResponseWrapper.data.frontal) {
        const apiResponse = apiResponseWrapper.data;

        // 1. Renderiza o frame e placeholders
        populateVideosUI(analysisId, apiResponseWrapper);
        
        // 2. Tenta plotar os gráficos (se a API não retornou dados temporais, os gráficos falharão sem dados simulados)
        // OBS: Para a versão antiga, o frontend precisa que o JSON retornado contenha:
        // analysis_data: { temporal_data_frontal: [...] }
        
        // Como o app.py original não retorna temporal_data, vamos simular a ausência
        currentAnalysisData = apiResponse.temporal_data_frontal || [{ tempo_segundos: 0, angulo_ombro_esquerdo: 90, angulo_ombro_direito: 90, angulo_quadril_esquerdo: 180, angulo_quadril_direito: 180, angulo_coluna_cervical: 180, angulo_joelho_esquerdo: 180, angulo_joelho_direito: 180, assimetria_ombros_vertical: 0, oscilacao_vertical_quadril: 0.5, posicao_horizontal_quadril: 0.5 }];
        
        loadingIndicator.style.display = 'none';
        tabContent.classList.remove('hidden');
        setupAllCharts(currentAnalysisData);
        
        if(typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    } else {
        // Se a chamada falhar, a mensagem de erro já está definida em fetchAnalysisData
    }
    
    // Configuração das abas e exportação (restante do código que você já tinha)
    document.querySelectorAll('.tab-button').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
            document.getElementById(`${tab.dataset.tab}-content`).classList.remove('hidden');
        });
    });
    
    // Funções auxiliares de Chart/CSV (MANTIDAS para o Chart.js funcionar)
    function createChartCard(id, title, category) {
        const container = document.getElementById(`${category}-content`);
        if (!container) return;
        const cardHTML = `
            <div class="bg-white p-6 rounded-xl shadow-sm">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
                    <h2 class="text-lg font-bold text-gray-800">${title}</h2>
                    <button data-export-target="${id}" class="export-button mt-2 sm:mt-0 text-sm flex items-center gap-2 px-3 py-1.5 rounded-md font-semibold bg-gray-100 text-gray-600 hover:bg-gray-200">
                        <i data-lucide="download" class="w-4 h-4"></i> Exportar CSV
                    </button>
                </div>
                <div class="chart-container"><canvas id="${id}"></canvas></div>
            </div>`;
        container.insertAdjacentHTML('beforeend', cardHTML);
    }
    
    function setupAllCharts(analysisData) {
        ['angulos', 'simetria', 'temporal', 'distribuicoes'].forEach(id => {
            const el = document.getElementById(`${id}-content`); if(el) el.innerHTML = '';
        });

        const timestamps = analysisData.map(d => (d.tempo_segundos || 0).toFixed(1));
        const chartOptions = (yTitle, beginAtZero = false) => ({ 
            responsive: true, 
            maintainAspectRatio: false, 
            scales: { 
                y: { 
                    title: { display: true, text: yTitle }, 
                    beginAtZero: beginAtZero 
                } 
            } 
        });

        // Plota o gráfico de Ombros (usando dados simulados se o temporal falhar)
        createChartCard('chartOmbros', 'Ângulos dos Ombros', 'angulos');
        new Chart('chartOmbros', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Esquerdo', data: analysisData.map(d => d.angulo_ombro_esquerdo), borderColor: '#4F46E5' }, { label: 'Direito', data: analysisData.map(d => d.angulo_ombro_direito), borderColor: '#EF4444' }] }, options: chartOptions('Ângulo (°)') });
        
        // ... (Adicionar o resto dos gráficos com a mesma estrutura)
        createChartCard('chartQuadris', 'Ângulos dos Quadris', 'angulos');
        new Chart('chartQuadris', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Esquerdo', data: analysisData.map(d => d.angulo_quadril_esquerdo), borderColor: '#4F46E5' }, { label: 'Direito', data: analysisData.map(d => d.angulo_quadril_direito), borderColor: '#EF4444' }] }, options: chartOptions('Ângulo (°)') });
        
        // Coluna
        createChartCard('chartColuna', 'Ângulos da Coluna', 'angulos');
        new Chart('chartColuna', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Cervical', data: analysisData.map(d => d.angulo_coluna_cervical), borderColor: '#34D399' }] }, options: chartOptions('Ângulo (°)') });

        // Joelhos
        createChartCard('chartJoelhos', 'Ângulos dos Joelhos', 'angulos');
        new Chart('chartJoelhos', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Esquerdo', data: analysisData.map(d => d.angulo_joelho_esquerdo), borderColor: '#4F46E5' }, { label: 'Direito', data: analysisData.map(d => d.angulo_joelho_direito), borderColor: '#EF4444' }] }, options: chartOptions('Ângulo (°)') });

        // Simetria Corporal
        createChartCard('chartAssimetriaOmbros', 'Assimetria Vertical dos Ombros', 'simetria');
        new Chart('chartAssimetriaOmbros', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Diferença Y', data: analysisData.map(d => d.assimetria_ombros_vertical), borderColor: '#F59E0B' }] }, options: chartOptions('Distância (0-1)') });

        // Oscilação Vertical
        createChartCard('chartOscilacaoVertical', 'Oscilação Vertical do Quadril (Y)', 'temporal');
        new Chart('chartOscilacaoVertical', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Posição Y (Quadril)', data: analysisData.map(d => d.oscilacao_vertical_quadril), borderColor: '#10B981' }] }, options: chartOptions('Posição (0-1)') });

        // Posição Horizontal
        createChartCard('chartPosicaoHorizontal', 'Posição Horizontal do Quadril (X)', 'temporal');
        new Chart('chartPosicaoHorizontal', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Posição X (Quadril)', data: analysisData.map(d => d.posicao_horizontal_quadril), borderColor: '#3B82F6' }] }, options: chartOptions('Posição (0-1)') });
        
        // Distribuições
        createChartCard('chartDistribuicaoQuadris', 'Distribuição Vertical do Quadril (Y)', 'distribuicoes');
        new Chart('chartDistribuicaoQuadris', { type: 'line', data: { labels: timestamps, datasets: [{ label: 'Distribuição Y', data: analysisData.map(d => d.oscilacao_vertical_quadril), showLine: false, pointRadius: 3, borderColor: '#A855F7' }] }, options: chartOptions('Posição (0-1)') });

    }

    // A lógica de exportação (exportToCSV e event listener) deve ser movida aqui também.
});
