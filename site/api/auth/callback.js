const { OAuth2Client } = require('google-auth-library'); 
const { put } = require('@vercel/blob');

// Seu Client ID do Google
const CLIENT_ID = '584796181991-rs0d2u96o5q6e4jcgr84itrks0d7297r.apps.googleusercontent.com';
const client = new OAuth2Client(CLIENT_ID);

// TOKEN DO BLOB - substitua com seu token real
const BLOB_TOKEN = "vercel_blob_rw_ZXJ7FzJ8oliEG9Ix_EMKmWfzml1W0Y0Ni1CbSdR4Em1A8X2";

function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}`;
  console.log(logMessage);
  return logMessage;
}

module.exports = async (req, res) => {
  // CONFIGURAÇÃO CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  // RESPONDER OPÇÕES CORS
  if (req.method === 'OPTIONS') {
    log('✅ Pré-voo CORS atendido');
    return res.status(200).end();
  }
  
  // VERIFICAR MÉTODO HTTP
  if (req.method === 'GET') {
    log('✅ Requisição GET recebida');
    return res.status(200).json({ 
      success: true,
      message: 'API de autenticação do The Posture Lab',
      status: 'active',
      timestamp: new Date().toISOString()
    });
  }
  
  if (req.method !== 'POST') {
    log(`❌ Método não permitido: ${req.method}`);
    return res.status(405).json({ 
      success: false,
      error: 'Método não permitido',
      allowed: ['POST', 'OPTIONS', 'GET']
    });
  }
  
  try {
    let body = '';
    
    // Coletar todos os dados da requisição
    for await (const chunk of req) {
      body += chunk.toString();
    }
    
    // Verificar se o body está vazio
    if (!body.trim()) {
      log('❌ Corpo da requisição vazio');
      return res.status(400).json({ 
        success: false,
        error: 'Corpo da requisição vazio'
      });
    }
    
    const data = JSON.parse(body);
    const { token, test } = data;
    
    // Responder a teste de conexão
    if (test) {
      log('✅ Teste de conexão recebido');
      return res.status(200).json({ 
        success: true, 
        message: 'API conectada com sucesso',
        timestamp: new Date().toISOString(),
        blobTokenConfigured: !!BLOB_TOKEN
      });
    }
    
    if (!token) {
      log('❌ Token não fornecido');
      return res.status(400).json({ 
        success: false,
        error: 'Token não fornecido'
      });
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
    const email_verified = payload['email_verified'];
    
    log(`👤 Usuário autenticado: ${email} (ID: ${userid})`);
    
    // Dados completos do usuário baseados no Google SSO
    const userData = {
      // Dados principais do Google
      id: userid,
      email: email,
      name: name,
      picture: picture,
      email_verified: email_verified,
      
      // Dados de autenticação
      provider: 'google',
      google_id: userid,
      
      // Metadados da aplicação
      loginTimestamp: new Date().toISOString(),
      lastAccess: new Date().toISOString(),
      accessCount: 1,
      firstLogin: new Date().toISOString(),
      
      // Informações adicionais do perfil Google
      given_name: payload['given_name'],
      family_name: payload['family_name'],
      locale: payload['locale'],
      hd: payload['hd'] || null
    };
    
    try {
      // Nome do arquivo no Blob Storage
      const filename = `users/${userid}.json`;
      log(`💾 Salvando usuário em: ${filename}`);
      
      // Salvar/atualizar no Blob Storage
      const blob = await put(
        filename,
        JSON.stringify(userData, null, 2),
        {
          access: 'public',
          contentType: 'application/json',
          addRandomSuffix: false,
          token: BLOB_TOKEN
        }
      );
      
      log(`✅ Dados salvos no Blob Storage: ${blob.url}`);
      
      return res.status(200).json({
        success: true,
        saved: true,
        user: {
          id: userData.id,
          email: userData.email,
          name: userData.name,
          picture: userData.picture,
          firstLogin: userData.firstLogin
        },
        message: 'Usuário salvo com sucesso no storage!',
        blobUrl: blob.url,
        timestamp: new Date().toISOString()
      });
      
    } catch (blobError) {
      log(`❌ Erro ao salvar no Blob Storage: ${blobError.message}`);
      
      return res.status(500).json({
        success: false,
        saved: false,
        error: 'Erro ao salvar usuário no storage',
        details: blobError.message,
        user: {
          id: userData.id,
          email: userData.email,
          name: userData.name
        }
      });
    }
    
  } catch (error) {
    log(`❌ Erro no processamento: ${error.message}`);
    
    return res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      details: error.message
    });
  }
};
