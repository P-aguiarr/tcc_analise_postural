const { OAuth2Client } = require('google-auth-library');
const { put } = require('@vercel/blob');

// Seu Client ID do Google
const CLIENT_ID = '584796181991-rs0d2u96o5q6e4jcgr84itrks0d7297r.apps.googleusercontent.com';
const client = new OAuth2Client(CLIENT_ID);

// Configuração para desativar o bodyParser (necessário para Pages API Routes)
export const config = {
  api: {
    bodyParser: false,
  },
};

module.exports = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Origin', 'https://ttc-analise-postural.vercel.app');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Responder à solicitação de pré-voo (preflight) do CORS
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  // Aceitar apenas requisições POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método não permitido' });
  }
  
  try {
    // Ler o corpo da requisição manualmente (já que bodyParser está desativado)
    let body = '';
    for await (const chunk of req) {
      body += chunk.toString();
    }
    
    const { token } = JSON.parse(body);
    
    if (!token) {
      return res.status(400).json({ error: 'Token não fornecido' });
    }
    
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
    
    // Dados do usuário para armazenar
    const userData = {
      id: userid,
      email: email,
      name: name,
      picture: picture,
      loginTimestamp: new Date().toISOString(),
      lastAccess: new Date().toISOString()
    };
    
    // Salvar dados do usuário no Blob Storage - FORMA CORRETA para Pages API
    try {
      const blob = await put(
        `users/${userid}.json`, 
        JSON.stringify(userData, null, 2), 
        {
          access: 'public',
          contentType: 'application/json',
          addRandomSuffix: false
        }
      );
      
      console.log('Dados do usuário salvos no Blob Storage:', blob.url);
      
    } catch (blobError) {
      console.error('Erro ao salvar no Blob Storage:', blobError);
      // Não falha a autenticação por erro no storage, apenas loga o erro
    }
    
    // Retornar resposta de sucesso
    res.status(200).json({
      success: true,
      user: userData,
      message: 'Login realizado com sucesso!'
    });
    
  } catch (error) {
    console.error('Erro na verificação do token:', error);
    res.status(401).json({
      success: false,
      error: 'Token inválido'
    });
  }
};
