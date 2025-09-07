// Script para testar a comunicação com o Blob Storage
const { put, get } = require('@vercel/blob');

async function testBlobStorage() {
  try {
    console.log('🧪 Testando comunicação com Vercel Blob Storage...');
    
    // Teste de escrita
    const testData = {
      id: 'test-user-123',
      email: 'test@example.com',
      name: 'Usuário Teste',
      testTimestamp: new Date().toISOString()
    };
    
    console.log('📝 Escrevendo dados de teste...');
    const blob = await put(
      'test/user-test.json',
      JSON.stringify(testData, null, 2),
      {
        access: 'public',
        contentType: 'application/json',
        addRandomSuffix: false
      }
    );
    
    console.log('✅ Dados escritos com sucesso!');
    console.log('📋 URL do blob:', blob.url);
    
    // Teste de leitura
    console.log('📖 Lendo dados de teste...');
    const response = await fetch(blob.url);
    
    if (response.ok) {
      const retrievedData = await response.json();
      console.log('✅ Dados lidos com sucesso!');
      console.log('📋 Dados recuperados:', retrievedData);
    } else {
      console.error('❌ Erro ao ler dados:', response.status, response.statusText);
    }
    
  } catch (error) {
    console.error('❌ Erro no teste:', error);
  }
}

// Executar teste se chamado diretamente
if (require.main === module) {
  testBlobStorage();
}

module.exports = { testBlobStorage };
