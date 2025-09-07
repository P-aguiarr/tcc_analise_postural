const fs = require('fs');
const { put } = require('@vercel/blob');

async function testBlobStorage() {
  const log = [];
  const addLog = (message) => {
    console.log(message);
    log.push(`${new Date().toISOString()} - ${message}`);
  };

  try {
    addLog('🧪 Testando comunicação com Vercel Blob Storage...');
    
    const testData = {
      id: 'test-user-123',
      email: 'test@example.com',
      name: 'Usuário Teste',
      testTimestamp: new Date().toISOString()
    };
    
    addLog('📝 Escrevendo dados de teste...');
    const blob = await put(
      'test/user-test.json',
      JSON.stringify(testData, null, 2),
      {
        access: 'public',
        contentType: 'application/json',
        addRandomSuffix: false
      }
    );
    
    addLog('✅ Dados escritos com sucesso!');
    addLog(`📋 URL do blob: ${blob.url}`);
    
    // Teste de leitura
    addLog('📖 Lendo dados de teste...');
    const response = await fetch(blob.url);
    
    if (response.ok) {
      const retrievedData = await response.json();
      addLog('✅ Dados lidos com sucesso!');
      addLog(`📋 Dados recuperados: ${JSON.stringify(retrievedData, null, 2)}`);
    } else {
      addLog(`❌ Erro ao ler dados: ${response.status} ${response.statusText}`);
    }
    
    // Salvar log em arquivo
    fs.writeFileSync('blob-test.log', log.join('\n'));
    addLog('📄 Log salvo em blob-test.log');
    
  } catch (error) {
    addLog(`❌ Erro no teste: ${error.message}`);
    fs.writeFileSync('blob-test.log', log.join('\n'));
  }
}

if (require.main === module) {
  testBlobStorage();
}

module.exports = { testBlobStorage };
