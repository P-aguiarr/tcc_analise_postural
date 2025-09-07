const { OAuth2Client } = require('google-auth-library');

// Seu Client ID do Google
const CLIENT_ID = '584796181991-rs0d2u96o5q6e4jcgr84itrks0d7297r.apps.googleusercontent.com';
const client = new OAuth2Client(CLIENT_ID);

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
          return res.status(200).json({ 
            success: true, 
            message: 'API conectada com sucesso' 
          });
        }
        
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
        
        // Dados do usuário
        const userData = {
          id: userid,
          email: email,
          name: name,
          picture: picture,
          loginTimestamp: new Date().toISOString(),
          lastAccess: new Date().toISOString()
        };
        
        // Retornar resposta de sucesso
        res.status(200).json({
          success: true,
          user: userData,
          message: 'Login realizado com sucesso!'
        });
        
      } catch (error) {
        console.error('Erro no processamento:', error);
        res.status(500).json({
          success: false,
          error: 'Erro interno do servidor'
        });
      }
    });
    
  } catch (error) {
    console.error('Erro na verificação do token:', error);
    res.status(401).json({
      success: false,
      error: 'Token inválido'
    });
  }
};
