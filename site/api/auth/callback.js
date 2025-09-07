
const express = require('express');
const { OAuth2Client } = require('google-auth-library');
const router = express.Router();

const CLIENT_ID = '584796181991-rs0d2u96o5q6e4jcgr84itrks0d7297r.apps.googleusercontent.com';
const client = new OAuth2Client(CLIENT_ID);

// Rota de callback do Google
router.post('/site/auth/google/callback', async (req, res) => {
try {
const { token } = req.body;

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

// Aqui você pode:
// 1. Verificar se o usuário já existe no seu banco de dados
// 2. Criar um novo usuário se não existir
// 3. Criar uma sessão para o usuário
// 4. Redirecionar para a página principal

// Exemplo: criar sessão e redirecionar
req.session.user = {
id: userid,
email: email,
name: name,
picture: picture
};

res.json({ 
success: true, 
message: 'Login realizado com sucesso!',
user: { id: userid, email, name, picture }
});

} catch (error) {
console.error('Erro no callback do Google:', error);
res.status(401).json({ 
success: false, 
message: 'Falha na autenticação' 
});
}
});

module.exports = router;
