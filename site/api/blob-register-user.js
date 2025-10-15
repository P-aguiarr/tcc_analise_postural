import { put, list } from '@vercel/blob';

// Nome do arquivo onde a lista de usuários será salva no Blob Storage
const USERS_BLOB_FILENAME = 'users.json';

/**
 * Lê, atualiza e escreve de volta a lista de usuários no Vercel Blob Storage.
 * @param {object} newUser - Dados do usuário autenticado (name, email, picture, lastLogin).
 * @returns {Promise<void>}
 */
async function updateUsersList(newUser) {
    // 1. O TOKEN É LIDO AQUI NO SERVIDOR (FORA DO ALCANCE DO NAVEGADOR)
    if (!process.env.BLOB_READ_WRITE_TOKEN) {
        throw new Error('BLOB_READ_WRITE_TOKEN não configurado no ambiente Vercel.');
    }

    let users = [];

    try {
        // 2. Tentar Ler a Lista Atual
        const listResult = await list({ prefix: USERS_BLOB_FILENAME });
        const existingBlob = listResult.blobs.find(b => b.pathname === USERS_BLOB_FILENAME);
        
        if (existingBlob) {
            const response = await fetch(existingBlob.url);
            if (!response.ok) throw new Error(`Falha ao buscar Blob: ${response.statusText}`);
            
            const jsonText = await response.text();
            try {
                users = JSON.parse(jsonText);
            } catch (e) {
                console.warn(`Arquivo ${USERS_BLOB_FILENAME} corrompido, recriando lista.`);
                users = [];
            }
        }
    } catch (error) {
        console.error('Erro ao ler ou baixar Blob inicial:', error);
        users = [];
    }

    // 3. Atualizar/Adicionar o Usuário
    const existingIndex = users.findIndex(user => user.email === newUser.email);

    if (existingIndex !== -1) {
        // Atualiza usuário existente (ex: data de último login)
        users[existingIndex] = { ...users[existingIndex], ...newUser };
    } else {
        // Adiciona novo usuário
        users.push(newUser);
    }
    
    // 4. Enviar de Volta para o Blob (put sobrescreve o arquivo)
    const updatedUsersJson = JSON.stringify(users, null, 2);
    
    await put(USERS_BLOB_FILENAME, updatedUsersJson, {
        access: 'public' // Altere para 'private' se não quiser acesso direto à URL
    });
}


// Função principal do Serverless Function
export default async (req, res) => {
    if (req.method !== 'POST') {
        res.setHeader('Allow', ['POST']);
        return res.status(405).json({ success: false, error: 'Método não permitido.' });
    }

    try {
        const { name, email, picture, lastLogin } = JSON.parse(req.body);

        if (!email || !name) {
            return res.status(400).json({ success: false, error: 'Dados de usuário incompletos.' });
        }

        const newUser = { name, email, picture, lastLogin };
        await updateUsersList(newUser);

        return res.status(200).json({ 
            success: true, 
            message: 'Usuário registrado com sucesso no Vercel Blob.'
        });

    } catch (error) {
        console.error('Erro no Serverless Function:', error);
        return res.status(500).json({ 
            success: false, 
            error: `Erro interno do servidor: ${error.message}` 
        });
    }
};
