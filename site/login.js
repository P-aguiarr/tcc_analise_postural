const RAILWAY_API_BASE_URL = 'https://tccanalisepostural-production.up.railway.app';
    
function showLoading() {
  document.getElementById('loadingSpinner').style.display = 'block';
  hideError();
  hideSuccess();
}

function hideLoading() {
  document.getElementById('loadingSpinner').style.display = 'none';
}

function showError(message) {
  const errorElement = document.getElementById('errorDetails');
  errorElement.innerText = '❌ Erro: ' + message;
  errorElement.style.display = 'block';
  hideLoading();
  document.getElementById('successMessage').style.display = 'none';
}

function hideError() {
  document.getElementById('errorDetails').style.display = 'none';
}

function showSuccess(message) {
  const successElement = document.getElementById('successMessage');
  successElement.innerText = message;
  successElement.style.display = 'block';
  hideLoading();
  document.getElementById('errorDetails').style.display = 'none';
}

function hideSuccess() {
  document.getElementById('successMessage').style.display = 'none';
}

function triggerGoogleSignIn() {
    showLoading();
    
    if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
        console.log('✅ GSI Client pronto. Disparando prompt de login...');
        
        google.accounts.id.prompt((notification) => {
            if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                console.error('❌ Falha ao mostrar pop-up do Google. Verifique bloqueadores.');
                showError('Falha ao abrir o pop-up de login. Desative bloqueadores de pop-up.');
            }
        });
        
    } else {
        console.log('⏳ GSI Client ainda não carregado. Aguardando...');
        showError('Serviço de login do Google não carregou. Tente recarregar a página.');
    }
}

function checkUserAndRedirect() {
  const userJSON = localStorage.getItem('user');
  const loginTime = localStorage.getItem('loginTime');

  if (userJSON && loginTime) {
    try {
      const userData = JSON.parse(userJSON);
      const currentTime = new Date().getTime();
      const EXPIRATION_TIME_MS = 86400000; // 24 horas

      if (currentTime - parseInt(loginTime) < EXPIRATION_TIME_MS) {
        console.log('Usuário válido encontrado. Redirecionando...');
        showSuccess(`Bem-vindo de volta, ${userData.name.split(' ')[0]}! Redirecionando...`);
        setTimeout(() => {
          window.location.href = '/poslogin';
        }, 1000); 
        return true;
      } else {
        console.log('Login expirado. Favor logar novamente.');
        localStorage.removeItem('user');
        localStorage.removeItem('loginTime');
      }
    } catch (e) {
      console.error('Erro ao parsear dados de usuário do localStorage:', e);
      localStorage.removeItem('user');
      localStorage.removeItem('loginTime');
    }
  }
  return false;
}

async function handleCredentialResponse(response) {
  if (!response.credential) {
    showError('Falha ao receber a credencial do Google.');
    return;
  }
  
  showLoading();

  try {
    const apiResponse = await fetch(`${RAILWAY_API_BASE_URL}/api/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ id_token: response.credential })
    });

    const data = await apiResponse.json();

    if (apiResponse.ok && data.success) {
      localStorage.setItem('user', JSON.stringify(data.user));
      localStorage.setItem('loginTime', new Date().getTime().toString());
      
      console.log('✅ Login completo. Dados salvos:', data.user);
      showSuccess(`Login bem-sucedido! Bem-vindo(a), ${data.user.name.split(' ')[0]}. Redirecionando...`);
      
      setTimeout(() => {
        window.location.href = '/poslogin';
      }, 1500); 

    } else {
      const errorMessage = data.error || 'Erro desconhecido ao processar o login.';
      console.error('❌ Erro na API de Callback:', data.error, data.details);
      showError(errorMessage);
    }

  } catch (error) {
    console.error('❌ Erro ao comunicar com o servidor de callback:', error);
    showError('Não foi possível se conectar com o servidor para finalizar o login.');
  } finally {
    hideLoading();
  }
}

// Expor funções para o HTML
window.handleCredentialResponse = handleCredentialResponse;
window.checkUserAndRedirect = checkUserAndRedirect;
window.triggerGoogleSignIn = triggerGoogleSignIn;

document.addEventListener('DOMContentLoaded', () => {
    // Aplica a centralização e o espaçamento para páginas curtas
    document.body.style.display = 'flex';
    document.body.style.flexDirection = 'column';
    document.body.style.minHeight = '100vh';
});
