const { OAuth2Client } = require('google-auth-library');
const { put } = require('@vercel/blob');

// Seu Client ID do Google
const CLIENT_ID = '584796181991-rs0d2u96o5q6e4jcgr84itrks0d7297r.apps.googleusercontent.com';
const client = new OAuth2Client(CLIENT_ID);

// TOKEN DO BLOB - COLOCA DIRETO NO CÓDIGO! 🔥
const BLOB_TOKEN = "vercel_blob_rw_ZXJ7FzJ8oliEG9Ix_EMKmWfzml1W0Y0Ni1CbSdR4Em1A8X2";

// Função de log melhorada
function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}`;
  console.log(logMessage);
  return logMessage;
}

module.exports = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Origin', 'https://ttc-analise-postural.vercel.app');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Responder à solicitação de pré-voo (preflight) do CORS
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  // Se for GET, retornar informação sobre a API
  if (req.method === 'GET') {
    return res.status(200).json({ 
      message: 'API de autenticação do The Posture Lab',
      status: 'active',
      method: 'Use POST para autenticar'
    });
  }
  
  // Aceitar apenas requisições POST para autenticação
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método não permitido' });
  }
  
  try {
    // Ler o corpo da requisição manualmente
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    
    req.on('end', async () => {
      try {
        const data = JSON.parse(body);
        const { token, test } = data;
        
        // Responder a teste de conexão
        if (test) {
          log('✅ Teste de conexão recebido');
          return res.status(200).json({ 
            success: true, 
            message: 'API conectada com sucesso' 
          });
        }
        
        if (!token) {
          log('❌ Token não fornecido');
          return res.status(400).json({ error: 'Token não fornecido' });
        }
        
        log('🔍 Verificando token do Google...');
        
        // Verificar o token do Google
        const ticket = await client.verifyIdToken({
          idToken: token,
          audience: CLIENT_ID,
        });
        
        const payload = ticket.getPayload();
        const userid = payload['sub'];
        const email = payload['email'];
        const name = payload['name'];
        const picture = payload['picture'];
        
        log(`👤 Usuário autenticado: ${email} (ID: ${userid})`);
        
        // Dados do usuário
        const userData = {
          id: userid,
          email: email,
          name: name,
          picture: picture,
          loginTimestamp: new Date().toISOString(),
          lastAccess: new Date().toISOString(),
          accessCount: 1
        };
        
        try {
          // 🔥 CORREÇÃO: Consulta com autenticação
          const existingUserUrl = `https://zxj7fzj8olieg9ix.public.blob.vercel-storage.com/users/${userid}.json`;
          log(`🔍 Verificando usuário existente: ${existingUserUrl}`);
          
          const existingResponse = await fetch(existingUserUrl, {
            headers: {
              'Authorization': `Bearer ${BLOB_TOKEN}`
            }
          });
          
          if (existingResponse.ok) {
            const existingData = await existingResponse.json();
            log('✅ Usuário existente encontrado, atualizando...');
            userData.accessCount = (existingData.accessCount || 0) + 1;
            userData.firstLogin = existingData.firstLogin || userData.loginTimestamp;
          } else {
            log('🆕 Novo usuário, criando registro...');
            userData.firstLogin = userData.loginTimestamp;
          }
          
          // 🔥 CORREÇÃO: Salvar no Blob Storage
          log('💾 Salvando no Blob Storage...');
          const blob = await put(
            `users/${userid}.json`,
            JSON.stringify(userData, null, 2),
            {
              access: 'public',
              contentType: 'application/json',
              addRandomSuffix: false,
              token: BLOB_TOKEN
            }
          );
          
          log(`✅ Dados salvos no Blob Storage: ${blob.url}`);
          
          // Retornar resposta de sucesso
          res.status(200).json({
            success: true,
            user: userData,
            message: 'Login realizado e dados salvos com sucesso!',
            blobUrl: blob.url,
            saved: true
          });
          
        } catch (blobError) {
          log(`❌ Erro ao salvar no Blob Storage: ${blobError.message}`);
          
          // Retornar info mesmo com erro no blob
          res.status(200).json({
            success: true,
            user: userData,
            message: 'Login realizado (erro ao salvar histórico)',
            warning: 'Dados não foram salvos no storage',
            saved: false,
            error: blobError.message
          });
        }
        
      } catch (error) {
        log(`❌ Erro no processamento: ${error.message}`);
        res.status(500).json({
          success: false,
          error: 'Erro interno do servidor: ' + error.message
        });
      }
    });
    
  } catch (error) {
    log(`❌ Erro na verificação do token: ${error.message}`);
    res.status(401).json({
      success: false,
      error: 'Token inválido: ' + error.message
    });
  }
};
