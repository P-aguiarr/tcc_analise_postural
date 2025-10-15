// site/upload.js (Conteúdo completo)

const files = new Map();
const fileInputs = {
    frontal: document.getElementById('frontalFileInput'),
    transversal: document.getElementById('transversalFileInput')
};
const validationError = document.getElementById('validationError');
const processingOverlay = document.getElementById('processingOverlay');
const processingTitle = processingOverlay.querySelector('h2');
const processingSubtitle = processingOverlay.querySelector('p');

const MAX_RETRIES = 3; // Total de tentativas (1 original + 2 repetições)
const RETRY_DELAY_MS = 1500; // 1.5 segundos de espera antes de tentar novamente

// Mapeamento de progresso para melhor UX (baseado em tempo)
const PROGRESS_STEPS = [
    { time: 0, message: "Iniciando o upload..." },
    { time: 1000, message: "Upload concluído. Servidor aquecendo (Cold Start)..." },
    { time: 3000, message: "Analisando quadros-chave (1/3)..." },
    { time: 6000, message: "Calculando ângulos articulares (2/3)..." },
    { time: 9000, message: "Gerando análise e recomendações (3/3)..." },
];

function updateProgress(stepIndex) {
    if (stepIndex >= PROGRESS_STEPS.length) return;
    const step = PROGRESS_STEPS[stepIndex];
    processingTitle.textContent = "Processando Análise...";
    processingSubtitle.textContent = step.message;
    
    // Configura a próxima atualização de progresso
    if (stepIndex < PROGRESS_STEPS.length - 1) {
        const nextStepTime = PROGRESS_STEPS[stepIndex + 1].time;
        const delay = nextStepTime - step.time;
        setTimeout(() => updateProgress(stepIndex + 1), delay);
    } else {
        processingSubtitle.textContent = "Análise concluída. Aguardando a resposta final do servidor...";
    }
}

// Funções de utilidade (handleFile, removeFile, updateFileListUI) mantidas aqui...

document.getElementById('frontalUploadArea').addEventListener('click', () => fileInputs.frontal.click());
document.getElementById('transversalUploadArea').addEventListener('click', () => fileInputs.transversal.click());

fileInputs.frontal.addEventListener('change', () => handleFile(fileInputs.frontal.files[0], 'frontal'));
fileInputs.transversal.addEventListener('change', () => handleFile(fileInputs.transversal.files[0], 'transversal'));

function handleFile(file, type) {
    if (file) files.set(type, file);
    updateFileListUI();
}

function removeFile(type) {
    files.delete(type);
    fileInputs[type].value = '';
    updateFileListUI();
}

function updateFileListUI() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    if (files.size === 0) {
        fileList.innerHTML = '<div class="file-item empty">Nenhum vídeo selecionado</div>';
        return;
    }
    files.forEach((file, type) => {
        const typeLabel = type === 'frontal' ? 'Plano Coronal' : 'Plano Transversal';
        fileList.innerHTML += `<div class="file-item"><span>${file.name} (${typeLabel})</span><div class="file-remove" onclick="removeFile('${type}')">✕</div></div>`;
    });
}


async function attemptAnalysis(formData) {
    const endpoint = "https://tccanalisepostural-production.up.railway.app/api/process-analysis";
    
    const response = await fetch(endpoint, { method: 'POST', body: formData });

    const resultText = await response.text();
    if (!response.ok) {
         // Se o servidor retornar um erro não-JSON (como um 502 de proxy/gateway),
         // é um forte indicador de falha de Cold Start/Rede.
         try {
             JSON.parse(resultText); 
         } catch (e) {
             throw new Error("Erro de rede/servidor (Pode ser Cold Start/CORS inicial).");
         }
         // Se for JSON, é um erro de API
         const errorJson = JSON.parse(resultText);
         throw new Error(errorJson.error || `Erro de rede ${response.status}.`);
    }
    
    const result = JSON.parse(resultText);
    if (result.success && result.analysis_id) {
        return result;
    } else {
        throw new Error(`A análise falhou: ${result.error || 'ID da análise não foi recebido.'}`);
    }
}


async function processAnalysis() {
    if (!files.has('frontal')) {
        validationError.style.display = 'block';
        return;
    }
    validationError.style.display = 'none';
    processingOverlay.style.display = 'flex';
    
    const formData = new FormData();
    if (files.has('frontal')) formData.append('frontalImage', files.get('frontal'));
    if (files.has('transversal')) formData.append('transversalImage', files.get('transversal'));
    
    // Inicia a simulação de progresso
    updateProgress(0);

    for (let i = 0; i < MAX_RETRIES; i++) {
        try {
            // Tenta a análise
            const result = await attemptAnalysis(formData);

            // Sucesso na resposta: interrompe o progresso cronometrado e redireciona
            processingTitle.textContent = "Sucesso!";
            processingSubtitle.textContent = "Análise concluída. Redirecionando...";
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            window.location.href = `/consulta.html?analysis_id=${result.analysis_id}`;
            return;

        } catch (error) {
            console.error(`[Tentativa ${i + 1}/${MAX_RETRIES}] Falha na análise:`, error.message);
            
            // Se for a última tentativa, exibe o erro final e para
            if (i === MAX_RETRIES - 1) {
                processingOverlay.style.display = 'none';
                alert(`Falha crítica na análise após ${MAX_RETRIES} tentativas: ${error.message}`);
                break;
            }
            
            // Caso contrário, exibe mensagem de tentativa de repetição
            processingTitle.textContent = "Erro de Conexão";
            processingSubtitle.textContent = `Falha de rede/servidor (CORS/Cold Start). Tentativa ${i + 2} em ${RETRY_DELAY_MS / 1000}s...`;
            
            // Espera antes de tentar novamente
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS));
        }
    }
    
    // Se o loop falhar todas as vezes, fecha o overlay.
    processingOverlay.style.display = 'none';
}

// Expõe a função para ser chamada pelo onclick no HTML
window.processAnalysis = processAnalysis;
