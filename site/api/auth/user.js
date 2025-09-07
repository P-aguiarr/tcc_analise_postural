const { get } = require('@vercel/blob');

export const config = {
  api: {
    bodyParser: false,
  },
};

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
    
    // Tentar recuperar dados do usuário do Blob Storage
    const blobUrl = `https://zxj7fzj8olieg9ix.public.blob.vercel-storage.com/users/${userId}.json`;
    
    const response = await fetch(blobUrl);
    
    if (response.ok) {
      const userData = await response.json();
      res.status(200).json({ success: true, user: userData });
    } else {
      res.status(404).json({ success: false, error: 'Usuário não encontrado' });
    }
    
  } catch (error) {
    console.error('Erro ao buscar usuário:', error);
    res.status(500).json({ success: false, error: 'Erro interno do servidor' });
  }
};
