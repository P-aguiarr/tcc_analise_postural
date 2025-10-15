const files = new Map();
const fileInputs = {
    frontal: document.getElementById('frontalFileInput'),
    transversal: document.getElementById('transversalFileInput')
};
const validationError = document.getElementById('validationError');
const processingOverlay = document.getElementById('processingOverlay');

// Adiciona event listeners de clique (agora em JS, não inline)
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

async function processAnalysis() {
    if (!files.has('frontal')) {
        validationError.style.display = 'block';
        return;
    }
    validationError.style.display = 'none';
    processingOverlay.style.display = 'flex';

    try {
        const formData = new FormData();
        if (files.has('frontal')) formData.append('frontalImage', files.get('frontal'));
        if (files.has('transversal')) formData.append('transversalImage', files.get('transversal'));
        
        // Endpoint do seu backend Railway
        const endpoint = "https://tccanalisepostural-production.up.railway.app/api/process-analysis";
        const response = await fetch(endpoint, { method: 'POST', body: formData });

        const resultText = await response.text();
        if (!response.ok) {
             throw new Error(`Erro de rede ${response.status}: ${resultText}`);
        }
        
        const result = JSON.parse(resultText);
        if (result.success && result.analysis_id) {
            // Redireciona para a página de consulta com o ID da análise
            window.location.href = `/consulta.html?analysis_id=${result.analysis_id}`;
        } else {
            throw new Error(`A análise falhou: ${result.error || 'ID da análise não foi recebido.'}`);
        }
    } catch (error) {
        console.error("Falha na análise:", error);
        alert("Falha na análise: " + error.message);
        processingOverlay.style.display = 'none';
    }
}
