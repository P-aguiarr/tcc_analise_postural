const { get } = require('@vercel/blob');

module.exports = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Origin', 'https://ttc-analise-postural.vercel.app');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método não permitido' });
  }
  
  try {
    const { userId } = req.query;
    
    if (!userId) {
      return res.status(400).json({ error: 'ID do usuário não fornecido' });
    }
    
    // URL do blob no Vercel Storage
    const blobUrl = `https://zxj7fzj8olieg9ix.public.blob.vercel-storage.com/users/${userId}.json`;
    
    console.log('Buscando usuário na URL:', blobUrl);
    
    const response = await fetch(blobUrl, {
      headers: {
        'Authorization': `Bearer ${process.env.BLOB_READ_WRITE_TOKEN}`
      }
    });
    
    if (response.status === 200) {
      const userData = await response.json();
      res.status(200).json({ 
        success: true, 
        user: userData,
        found: true 
      });
    } else if (response.status === 404) {
      res.status(404).json({ 
        success: false, 
        error: 'Usuário não encontrado',
        found: false 
      });
    } else {
      console.error('Erro HTTP:', response.status, response.statusText);
      res.status(500).json({ 
        success: false, 
        error: `Erro ao buscar usuário: ${response.status} ${response.statusText}` 
      });
    }
    
  } catch (error) {
    console.error('Erro ao buscar usuário:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Erro interno do servidor',
      details: error.message 
    });
  }
};
