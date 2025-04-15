# Assistente Executivo IA

## Descrição do Projeto
O Assistente Executivo IA é um sistema inteligente de automação e apoio à gestão, que utiliza um bot Telegram integrado ao AnythingLLM para executar tarefas, responder perguntas, gerar relatórios, gráficos e resumos, tudo via Telegram. O AnythingLLM é utilizado exclusivamente como fonte de contexto e busca vetorizada de documentos. Todo o fluxo de automação, decisões e interações é feito pelo bot Python, sem Crew AI.

## Funcionalidades Principais
- **Chatbot Telegram**: Interface principal para interação com o sistema.
- **Busca Contextual (AnythingLLM)**: Consulta e recuperação de informações em documentos via banco vetorizado do AnythingLLM.
- **Processamento de Documentos**: Upload, indexação e consulta de PDFs, imagens e textos.
- **Geração de Gráficos**: Criação automática de gráficos (QuickChart) a partir de comandos ou contexto de conversa.
- **Resumos Executivos**: Geração de resumos automáticos de documentos e conversas.
- **Ações Automatizadas**: Execução de comandos e automações personalizadas via chat.
- **Histórico de Interações**: Registro e consulta de interações anteriores.
- **Gestão de Despesas**: Registro e atualização de despesas manuais pelo Telegram, com sincronização automática no contexto.

## Arquitetura
O sistema é composto por dois componentes principais:
- **Bot Telegram (bot.py)**: Interface de usuário para envio de mensagens, comandos e arquivos, além de toda a lógica de automação e integração.
- **AnythingLLM**: Utilizado apenas para busca vetorizada e contexto de documentos, não para armazenamento principal.

## Stack Tecnológica
- **Backend**: Python 3.x
- **Busca Contextual**: AnythingLLM Desktop (apenas contexto)
- **Interface de Usuário**: Bot Telegram
- **Gerenciamento de Configuração**: Arquivos .env e JSON

## Requisitos
- **Python 3.8+**
- **AnythingLLM Desktop** (apenas para contexto)
- **Token de Bot Telegram**
- **Chave de API AnythingLLM**

## Instalação
### Configuração do Ambiente
1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/AssistenteExecutivo-ia.git
   cd AssistenteExecutivo-ia
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
3. Envie mensagens de texto para perguntas, comandos ou envie documentos para adicionar ao contexto
4. Exemplos de comandos:
   - Envie arquivos PDF, imagens ou textos para análise automática
   - Use frases como "Gastei R$ 20 com almoço hoje" para registrar despesas
   - Use comandos como /novo_chat, /historico_chat, /reset, /documentos, /sync
   - Solicite gráficos ou relatórios diretamente na conversa

## Segurança e Privacidade
- Nunca compartilhe seu arquivo .env ou credenciais sensíveis.
- O arquivo .gitignore já está configurado para proteger arquivos de ambiente e segredos.
- Recomenda-se revisar periodicamente os arquivos ignorados e garantir que nenhum segredo seja versionado.

## Fluxo de Funcionamento
1. O usuário envia uma mensagem ou documento para o bot no Telegram
2. O bot identifica o tipo de solicitação e aciona as funções apropriadas
3. O bot consulta o AnythingLLM para buscar informações contextuais em documentos
4. O bot responde ao usuário consolidando as informações e resultados

## Estrutura do Projeto
- **bot.py**: Código principal do bot Telegram e orquestração de automações
- **api_utils.py**: Utilitários para comunicação com AnythingLLM
- **user_map.json**: Mapeamento de usuários e workspaces
- **file_map.json**: Mapeamento de arquivos enviados e suas localizações

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