const RAILWAY_API_BASE_URL = 'https://tccanalisepostural-production.up.railway.app';
const VERCEL_BLOB_API_URL = '/api/blob-register-user'; 

// ==========================================================
// FUNÇÕES DE UI (Show/Hide messages)
// ==========================================================
function showLoading() {
  document.getElementById('loadingSpinner').style.display = 'block';
  document.getElementById('errorDetails').style.display = 'none';
  document.getElementById('successMessage').style.display = 'none';
}

function hideLoading() {
  document.getElementById('loadingSpinner').style.display = 'none';
}

function showError(message) {
  const errorElement = document.getElementById('errorDetails');
  errorElement.innerText = '❌ Erro: ' + message;
  errorElement.style.display = 'block';
  hideLoading();
}

function showSuccess(message) {
  const successElement = document.getElementById('successMessage');
  successElement.innerText = message;
  successElement.style.display = 'block';
  hideLoading();
}

// ==========================================================
// REGISTRO NO VERCEL BLOB (Chama a API Serverless Segura)
// ==========================================================
async function registerUserInVercelBlob(user) {
    try {
        // Envia os dados do usuário para a API Vercel, que lida com o token seguro (no lado do servidor)
        const response = await fetch(VERCEL_BLOB_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // Passa os dados do usuário para a API Serverless
            body: JSON.stringify({
                name: user.name,
                email: user.email,
                picture: user.picture,
                lastLogin: new Date().toISOString()
            }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            console.log('✅ Usuário registrado/atualizado no Vercel Blob com sucesso!');
        } else {
            // Não bloqueia o login se o registro no Blob falhar, apenas loga o erro
            console.error('❌ Falha ao registrar usuário no Vercel Blob:', data.error);
        }
    } catch (error) {
        console.error('❌ Erro de rede ao chamar Vercel Blob API:', error);
    }
}

// ==========================================================
// LÓGICA DE CLIQUE CUSTOMIZADO (USANDO API GSI)
// ==========================================================
function triggerGoogleSignIn() {
    showLoading();
    
    // Verifica se o objeto google.accounts.id está carregado
    if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
        google.accounts.id.prompt((notification) => {
            if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                showError('Falha ao abrir o pop-up de login. Desative bloqueadores de pop-up.');
            }
        });
    } else {
        showError('Serviço de login do Google não carregou. Tente recarregar a página.');
    }
}

// ==========================================================
// REDIRECIONAMENTO DE PRÉ-LOGIN
// ==========================================================
function checkUserAndRedirect() {
  const userJSON = localStorage.getItem('user');
  const loginTime = localStorage.getItem('loginTime');

  if (userJSON && loginTime) {
    try {
      const userData = JSON.parse(userJSON);
      const currentTime = new Date().getTime();
      const EXPIRATION_TIME_MS = 86400000; // 24 horas

      if (currentTime - parseInt(loginTime) < EXPIRATION_TIME_MS) {
        showSuccess(`Bem-vindo de volta, ${userData.name.split(' ')[0]}! Redirecionando...`);
        setTimeout(() => {
          window.location.href = '/poslogin';
        }, 1000); 
        return true;
      } else {
        localStorage.removeItem('user');
        localStorage.removeItem('loginTime');
      }
    } catch (e) {
      localStorage.removeItem('user');
      localStorage.removeItem('loginTime');
    }
  }
  return false;
}

// ==========================================================
// FUNÇÃO PRINCIPAL DE RESPOSTA DO GOOGLE
// ==========================================================
async function handleCredentialResponse(response) {
  if (!response.credential) {
    showError('Falha ao receber a credencial do Google.');
    return;
  }
  
  showLoading();

  try {
    // PASSO 1: CHAMA O BACKEND RAILWAY PARA VALIDAÇÃO DO TOKEN
    // *** CORREÇÃO: /api/callback trocado por /auth/callback ***
    const apiResponse = await fetch(`${RAILWAY_API_BASE_URL}/auth/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: response.credential })
    });

    const data = await apiResponse.json();

    if (apiResponse.ok && data.success) {
      const user = data.user;

      // Salva dados no localStorage (Frontend)
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('loginTime', new Date().getTime().toString());
      
      // PASSO 2: CHAMA A API VERCEL PARA REGISTRAR NO BLOB (SEGURO)
      await registerUserInVercelBlob(user);
      
      showSuccess(`Login bem-sucedido! Bem-vindo(a), ${user.name.split(' ')[0]}. Redirecionando...`);
      
      setTimeout(() => {
        window.location.href = '/poslogin';
      }, 1500); 

    } else {
      const errorMessage = data.error || 'Erro desconhecido ao processar o login.';
      showError(errorMessage);
    }

  } catch (error) {
    console.error('❌ Erro de comunicação com o servidor:', error);
    showError('Não foi possível se conectar com o servidor para finalizar o login.');
  } finally {
    hideLoading();
  }
}

// Expor funções globais para o HTML e para o script de inicialização
window.handleCredentialResponse = handleCredentialResponse;
window.checkUserAndRedirect = checkUserAndRedirect;
window.triggerGoogleSignIn = triggerGoogleSignIn;
