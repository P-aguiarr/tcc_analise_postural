// Script para testar a comunicação com o Blob Storage
const { put } = require('@vercel/blob');

async function testBlobStorage() {
  try {
    console.log('🧪 Testando comunicação com Vercel Blob Storage...');
    
    // TOKEN DIRETO NO CÓDIGO (SUPER PRÁTICO!) 🔥
    const BLOB_TOKEN = "vercel_blob_rw_ZXJ7FzJ8oliEG9Ix_EMKmWfzml1W0Y0Ni1CbSdR4Em1A8X2";
    
    // Teste de escrita
    const testData = {
      id: 'test-user-123',
      email: 'test@example.com',
      name: 'Usuário Teste',
      testTimestamp: new Date().toISOString(),
      message: "Funcionou! 🎉"
    };
    
    console.log('📝 Escrevendo dados de teste...');
    const blob = await put(
      'test/user-test.json',
      JSON.stringify(testData, null, 2),
      {
        access: 'public',
        contentType: 'application/json',
        addRandomSuffix: false,
        token: BLOB_TOKEN // Token direto aqui!
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
      console.log('📋 Dados recuperados:', JSON.stringify(retrievedData, null, 2));
      
      // Teste extra: verificar se podemos acessar pela URL
      console.log('\n🌐 Testando acesso pela URL no browser...');
      console.log(`🔗 Cole isso no seu navegador: ${blob.url}`);
      
    } else {
      console.error('❌ Erro ao ler dados:', response.status, response.statusText);
    }
    
  } catch (error) {
    console.error('❌ Erro no teste:', error.message);
    
    // Dica de troubleshooting
    if (error.message.includes('token')) {
      console.log('\n💡 Dica: Verifique se o token está correto!');
      console.log('📋 Token usado:', "vercel_blob_rw_ZXJ7FzJ8oliEG9Ix_EMKmWfzml1W0Y0Ni1CbSdR4Em1A8X2".length, 'caracteres');
    }
  }
}

// Executar teste se chamado diretamente
if (require.main === module) {
  testBlobStorage();
}

module.exports = { testBlobStorage };
