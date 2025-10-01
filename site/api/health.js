// site/api/health.js
export default function handler(req, res) {
  // Configura CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  // Handle preflight request
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method === 'GET') {
    try {
      return res.status(200).json({
        success: true,
        message: 'API está funcionando corretamente',
        environment: process.env.NODE_ENV || 'production',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
      });
    } catch (error) {
      console.error('Health check error:', error);
      return res.status(500).json({
        success: false,
        error: 'Internal server error in health check'
      });
    }
  }
  
  // Método não permitido
  return res.status(405).json({
    success: false,
    error: 'Method not allowed. Use GET or OPTIONS.'
  });
}
