// site/api/health.js
export default function handler(request, response) {
  response.status(200).json({
    status: 'ok',
    environment: 'production',
    message: 'API Health Check - Frontend Only Mode'
  });
}
