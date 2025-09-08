const { list } = require('@vercel/blob');

module.exports = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Origin', 'https://ttc-analise-postural.vercel.app');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método não permitido' });
  }
  
  try {
    const { email } = req.body;
    
    if (!email) {
      return res.status(400).json({ error: 'E-mail do paciente não fornecido' });
    }
    
    console.log('Buscando paciente com email:', email);
    
    // Buscar todos os arquivos de usuários
    const { blobs } = await list({ 
      token: process.env.BLOB_READ_WRITE_TOKEN 
    });
    
    // Filtrar apenas arquivos de usuários
    const userBlobs = blobs.filter(blob => 
      blob.pathname.startsWith('users/') && 
      blob.pathname.endsWith('.json')
    );
    
    console.log(`Encontrados ${userBlobs.length} arquivos de usuário`);
    
    // Procurar usuário pelo email
    let userData = null;
    
    for (const blob of userBlobs) {
      try {
        const response = await fetch(blob.url, {
          headers: {
            'Authorization': `Bearer ${process.env.BLOB_READ_WRITE_TOKEN}`
          }
        });
        
        if (response.status === 200) {
          const data = await response.json();
          
          // Verificar se é o usuário procurado
          if (data.email && data.email.toLowerCase() === email.toLowerCase()) {
            userData = data;
            console.log('Usuário encontrado:', data.email);
            break;
          }
        }
      } catch (error) {
        console.error(`Erro ao ler arquivo ${blob.pathname}:`, error);
      }
    }
    
    if (userData) {
      res.status(200).json({ 
        success: true, 
        found: true,
        user: {
          email: userData.email,
          name: userData.name,
          id: userData.id
        },
        history: userData.history || []
      });
    } else {
      res.status(404).json({ 
        success: false, 
        found: false,
        error: 'E-mail não encontrado na base de dados'
      });
    }
    
  } catch (error) {
    console.error('Erro ao buscar histórico:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Erro interno do servidor',
      details: error.message 
    });
  }
};
