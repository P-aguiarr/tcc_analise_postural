// api/health.js
export default function handler(req, res) {
  // Configura CORS para permitir requisições do seu domínio
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight request
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method === 'GET') {
    try {
      // Resposta simples de health check
      return res.status(200).json({
        success: true,
        message: 'API está funcionando',
        environment: process.env.NODE_ENV || 'production',
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Health check error:', error);
      return res.status(500).json({
        success: false,
        error: 'Internal server error'
      });
    }
  }

  // Método não permitido
  return res.status(405).json({
    success: false,
    error: 'Method not allowed'
  });
}
