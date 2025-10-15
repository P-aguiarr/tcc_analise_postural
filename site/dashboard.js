const backendBaseUrl = "https://tccanalisepostural-production.up.railway.app";
let currentAnalysisData = null;
let currentAnalysisId = null;

/**
 * Lida com o erro de carregamento de vídeo.
 */
function handleVideoError(videoElement, type) {
    if (type === 'Original') {
        console.error(`[FRONTEND ERRO CRÍTICO] Falha ao carregar o vídeo Original. URL: ${videoElement.src}`);
    } else {
        console.error(`[FRONTEND ERRO] Falha ao carregar o vídeo Landmarks. URL: ${videoElement.src}`);
    }
    
    const parentDiv = videoElement.closest('.video-card');
    if (parentDiv) {
        const mediaBox = parentDiv.querySelector('.media-box');
        if (mediaBox) {
            // Usa Lucide Icons para exibir o placeholder
            mediaBox.innerHTML = `
                <div class="media-content rounded-lg flex flex-col items-center justify-center video-placeholder">
                    <i data-lucide="alert-triangle" class="w-6 h-6 text-red-500 mb-2"></i>
                    <p class="text-sm text-red-600 font-semibold">${type} indisponível.</p>
                    <p class="text-xs text-red-400">O servidor falhou ao codificar o vídeo (WebM).</p>
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
    
    if (apiResponse.data.frontal && apiResponse.data.frontal.image_b64) {
        // Assume que a análise retorna o base64 para a imagem do frame inicial
        const frameB64 = apiResponse.data.frontal.image_b64;
        
        videoContainer.innerHTML += `
            <div class="bg-white p-4 rounded-xl shadow-sm video-card">
                <h3 class="font-bold mb-2">Plano Coronal (Frame Processado)</h3>
                <div class="media-box">
                    <img class="media-content rounded-lg" 
                        src="data:image/png;base64,${frameB64}" 
                        alt="Frame Processado" />
                </div>
            </div>`;

        // Aqui você pode adicionar o placeholder do vídeo de Landmarks
         videoContainer.innerHTML += `
            <div class="bg-white p-4 rounded-xl shadow-sm video-card">
                <h3 class="font-bold mb-2">Vídeo de Landmarks (Indisponível na versão estática)</h3>
                <div class="media-box">
                    <div class="media-content rounded-lg flex flex-col items-center justify-center video-placeholder">
                        <i data-lucide="video-off" class="w-6 h-6 text-red-500 mb-2"></i>
                        <p class="text-sm text-red-600 font-semibold">Vídeo Indisponível</p>
                        <p class="text-xs text-red-400">O servidor não salvou o vídeo processado para esta versão.</p>
                    </div>
                </div>
            </div>`;
    } else {
         videoContainer.innerHTML = '<div class="bg-white p-4 rounded-xl shadow-sm md:col-span-2"><p class="text-red-500">Falha ao carregar frame da análise.</p></div>';
    }
    document.getElementById('analysisSubtitle').textContent = `Resultados da Análise ID: ${analysisId}`;
}


async function fetchAnalysisData(analysisId) {
    try {
        if (!analysisId) throw new Error("ID da análise não foi encontrado na URL.");
        
        // CORREÇÃO CRÍTICA: A rota de análise deve ser a do seu backend Railway
        const apiUrl = `${backendBaseUrl}/api/analysis/${analysisId}`; 
        
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error(`Erro na rede: ${response.status}`);
        
        const apiResponse = await response.json();
        
        // IMPORTANTE: O endpoint atual /analyze retorna os dados, mas o /analysis/<id> é simulado.
        // Se a chamada for bem-sucedida, o código continua.
        if (!apiResponse.analysis_id) throw new Error(`Erro no backend: ID da análise ausente.`);

        // Se o backend antigo não tiver a rota /analysis/<id>, isso aqui vai falhar. 
        // Para fins de teste e correção do frontend, vamos assumir que o backend 
        // que retornou o ID na página anterior é a fonte dos dados simulados.
        // OBS: Na sua implementação real, a rota /analysis/<id> deve retornar 
        // o JSON salvo pelo /process-analysis.

        return {
            analysis_id: apiResponse.analysis_id,
            data: {
                // Simulando a estrutura esperada do JSON de análise:
                frontal: apiResponse.data.frontal, 
                lateral: apiResponse.data.lateral,
                recommendations: apiResponse.data.recomendacoes
                // Como a função de análise no backend_app.py não retorna dados temporais (para gráficos), 
                // o frontend terá que simular ou tratar a ausência deles. 
                // Vamos simular dados vazios para evitar falha no Chart.js.
            }
        };
        
    } catch (error) {
        console.error(`[FRONTEND ERRO CRÍTICO] Falha ao buscar análise: ${error.message}`);
        document.getElementById('loading-indicator').innerHTML = `<h2 class="text-red-500 font-bold">Falha ao carregar dados da análise. (Consulte o console F12)</h2>`;
        return null;
    }
}
        
function cleanupAnalysis(id) {
    if (!id) return;
    // Assume que a rota de limpeza é /api/delete-analysis/<id>
    const deleteUrl = `${backendBaseUrl}/api/delete-analysis/${id}`;
    const data = new Blob([''], {type : 'application/json'});
    navigator.sendBeacon(deleteUrl, data);
    console.log(`Cleanup request sent for analysis ID: ${id}`);
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

    // Chama a API de análise (Aqui está o problema CORS/Dados)
    const apiResponse = await fetchAnalysisData(analysisId);
    
    if (apiResponse && apiResponse.data) {
        // Preenche a seção de vídeos (usando o frame B64 para o frame inicial)
        populateVideosUI(analysisId, apiResponse);
        
        // --- SIMULAÇÃO DE DADOS PARA GRÁFICOS (POIS A API NÃO RETORNA TEMPORAIS) ---
        // Cria dados simulados mínimos para Chart.js não quebrar
        const simulatedData = [{ tempo_segundos: 0, angulo_ombro_esquerdo: 90, angulo_ombro_direito: 90 }];
        currentAnalysisData = simulatedData; 
        // --------------------------------------------------------------------------

        loadingIndicator.style.display = 'none';
        tabContent.classList.remove('hidden');
        setupAllCharts(currentAnalysisData);
        if(typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    } else {
        // Se a chamada falhar (CORS/Cold Start), a mensagem de erro já está definida em fetchAnalysisData
    }
    
    // Configuração das abas
    document.querySelectorAll('.tab-button').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
            document.getElementById(`${tab.dataset.tab}-content`).classList.remove('hidden');
        });
    });
    
    // Limpeza ao fechar a aba
    window.addEventListener('beforeunload', () => {
        if (currentAnalysisId) {
            // cleanupAnalysis(currentAnalysisId); // Descomente para ativar a limpeza
        }
    });

    // --- FUNÇÕES DE GRÁFICOS (MANTIDAS) ---
    
    function exportToCSV(data, filename) {
        if (!data || data.length === 0) { console.error("Não há dados para exportar."); return; }
        const headers = Object.keys(data[0]);
        const csvRows = [headers.join(',')];
        for (const row of data) {
            const values = headers.map(header => `"${String(row[header] ?? '').replace(/"/g, '""')}"`);
            csvRows.push(values.join(','));
        }
        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    document.getElementById('tab-content').addEventListener('click', function(event) {
        const exportButton = event.target.closest('.export-button');
        if (!exportButton || !currentAnalysisData) return;
        // Lógica de exportação... (A ser implementada com Chart.js)
    });
    
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

        // Simulação de timestamps para Charts
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

        // Ângulos Articulares (Usando dados mockados para não quebrar)
        createChartCard('chartOmbros', 'Ângulos dos Ombros', 'angulos');
        new Chart('chartOmbros', { 
            type: 'line', 
            data: { 
                labels: ['0.0'], 
                datasets: [
                    { label: 'Esquerdo', data: [90], borderColor: '#4F46E5' }, 
                    { label: 'Direito', data: [90], borderColor: '#EF4444' }
                ] 
            }, 
            options: chartOptions('Ângulo (°)') 
        });
        
        // ... (Outros gráficos seriam adicionados aqui)
    }
    // window.handleVideoError = handleVideoError;
});
