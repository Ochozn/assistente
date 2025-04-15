# AI-Pipeline

## Descrição do Projeto
O AI-Pipeline é um sistema de processamento de documentos e interação via chatbot que utiliza tecnologias de IA para fornecer respostas contextualizadas baseadas em documentos armazenados. O sistema integra o Telegram como interface de usuário, MinIO para armazenamento de documentos, e AnythingLLM como motor de processamento de linguagem natural.

## Funcionalidades Principais
- **Chatbot Telegram**: Interface de usuário acessível via Telegram para interação com o sistema.
- **Armazenamento de Documentos**: Upload e gerenciamento de documentos via MinIO.
- **Processamento de Documentos**: Análise e indexação de documentos para consulta contextual.
- **Workspaces Personalizados**: Cada usuário possui seu próprio workspace isolado.
- **Suporte a Múltiplos Formatos**: Processamento de PDFs, imagens e outros tipos de documentos.

## Arquitetura
O sistema é composto por três componentes principais:
- **Bot Telegram**: Interface de usuário que permite enviar mensagens e documentos.
- **MinIO**: Sistema de armazenamento de objetos para documentos.
- **AnythingLLM**: Motor de IA para processamento de linguagem natural e geração de respostas.

## Stack Tecnológica
- **Backend**: Python 3.x
- **Armazenamento**: MinIO (S3-compatible)
- **IA/LLM**: AnythingLLM Desktop
- **Interface de Usuário**: Bot Telegram
- **Gerenciamento de Configuração**: Arquivos .env e JSON

## Requisitos
- **Python 3.8+**
- **MinIO Server**
- **AnythingLLM Desktop**
- **Token de Bot Telegram**

## Instalação
### Configuração do Ambiente
1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/AI-Pipeline.git
   cd AI-Pipeline
   ```
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente:
   ```bash
   cp .env.example .env
   ```
   Edite o arquivo .env com suas credenciais:
   ```plaintext
   MINIO_ENDPOINT=seu-servidor-minio:9000
   MINIO_ACCESS_KEY=sua-chave-de-acesso
   MINIO_SECRET_KEY=sua-chave-secreta
   MINIO_BUCKET=nome-do-bucket
   TELEGRAM_TOKEN=seu-token-telegram
   ANYTHINGLLM_API=http://localhost:3001/api
   ANYTHINGLLM_API_KEY=sua-chave-api-local
   ```

### Configuração do AnythingLLM Desktop
1. Baixe e instale o AnythingLLM Desktop do repositório oficial
2. Execute o AnythingLLM Desktop
3. Configure sua chave de API nas configurações do aplicativo
4. O servidor estará disponível em http://localhost:3001

## Uso
1. Inicie o bot:
   ```bash
   python bot.py
   ```
2. No Telegram, inicie uma conversa com o bot usando o comando /start
3. Envie mensagens de texto para fazer perguntas ou envie documentos para adicionar ao seu contexto

## Fluxo de Funcionamento
1. O usuário envia uma mensagem ou documento para o bot no Telegram
2. Se for um documento, ele é armazenado no MinIO e indexado pelo AnythingLLM
3. Se for uma mensagem, ela é processada pelo AnythingLLM usando o contexto dos documentos previamente enviados
4. O bot responde com informações relevantes baseadas no contexto

## Estrutura do Projeto
- **bot.py**: Código principal do bot Telegram
- **minio_utils.py**: Utilitários para interação com o MinIO
- **user_map.json**: Mapeamento de usuários e seus workspaces

## Contribuição
Contribuições são bem-vindas! Por favor, siga estes passos:
1. Faça um fork do projeto
2. Crie uma branch para sua feature (git checkout -b feature/nova-feature)
3. Commit suas mudanças (git commit -m 'Adiciona nova feature')
4. Push para a branch (git push origin feature/nova-feature)
5. Abra um Pull Request

## Licença
Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

## Contato
Para questões e sugestões, por favor abra uma issue no GitHub.

Desenvolvido com ❤️ pela equipe Ia-Amarelo