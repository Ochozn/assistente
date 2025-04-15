# Assistente Executivo IA

## Descrição do Projeto
O Assistente Executivo IA é um sistema inteligente de automação e apoio à gestão, que utiliza agentes orquestrados pelo Crew AI para executar tarefas, responder perguntas, gerar relatórios, gráficos e resumos, tudo via Telegram. O AnythingLLM é utilizado exclusivamente como fonte de contexto e busca vetorizada de documentos. Todo o fluxo de agentes, decisões e automações é feito pelo Crew AI, com integração ao Telegram para interação com o usuário.

## Funcionalidades Principais
- **Chatbot Telegram**: Interface principal para interação com o sistema.
- **Orquestração de Agentes (Crew AI)**: Delegação automática de tarefas entre agentes especializados (coordenador, bibliotecário, financeiro, etc).
- **Busca Contextual (AnythingLLM)**: Consulta e recuperação de informações em documentos via banco vetorizado do AnythingLLM.
- **Processamento de Documentos**: Upload, indexação e consulta de PDFs, imagens e textos.
- **Geração de Gráficos**: Criação automática de gráficos (QuickChart) a partir de comandos ou contexto de conversa.
- **Resumos Executivos**: Geração de resumos automáticos de documentos e conversas.
- **Ações Automatizadas**: Execução de comandos e automações personalizadas via chat.
- **Histórico de Interações**: Registro e consulta de interações anteriores.

## Arquitetura
O sistema é composto por três componentes principais:
- **Bot Telegram**: Interface de usuário para envio de mensagens, comandos e arquivos.
- **Crew AI**: Orquestrador de agentes inteligentes, responsável por delegar tarefas e consolidar respostas.
- **AnythingLLM**: Utilizado apenas para busca vetorizada e contexto de documentos, não para armazenamento.

## Stack Tecnológica
- **Backend**: Python 3.x
- **Orquestração de Agentes**: Crew AI
- **Busca Contextual**: AnythingLLM Desktop (apenas contexto)
- **Interface de Usuário**: Bot Telegram
- **Gerenciamento de Configuração**: Arquivos .env e JSON

## Requisitos
- **Python 3.8+**
- **Crew AI**
- **AnythingLLM Desktop** (apenas para contexto)
- **Token de Bot Telegram**
- **Chave de API OpenAI**

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
   OPENAI_API_KEY=sua-chave-openai
   ```

### Configuração do AnythingLLM Desktop
1. Baixe e instale o AnythingLLM Desktop do repositório oficial
2. Execute o AnythingLLM Desktop
3. Configure sua chave de API nas configurações do aplicativo
4. O servidor estará disponível em http://localhost:3001

### Configuração do Crew AI
1. As dependências do Crew AI já estão no requirements.txt
2. Não é necessário configuração adicional além da chave OpenAI

## Uso
1. Inicie o bot:
   ```bash
   python bot.py
   ```
2. No Telegram, inicie uma conversa com o bot usando o comando /start
3. Envie mensagens de texto para perguntas, comandos ou envie documentos para adicionar ao contexto
4. Exemplos de comandos:
   - Envie arquivos PDF, imagens ou textos para análise automática
   - Use `@agent` para acionar agentes específicos (ex: `@agent Crie um gráfico...`)

## Segurança e Privacidade
- Nunca compartilhe seu arquivo .env ou credenciais sensíveis.
- O arquivo .gitignore já está configurado para proteger arquivos de ambiente e segredos.
- Recomenda-se revisar periodicamente os arquivos ignorados e garantir que nenhum segredo seja versionado.

## Fluxo de Funcionamento
1. O usuário envia uma mensagem ou documento para o bot no Telegram
2. O bot identifica o tipo de solicitação e aciona o Crew AI
3. O Crew AI delega tarefas aos agentes apropriados (coordenador, bibliotecário, financeiro, etc)
4. O agente bibliotecário consulta o AnythingLLM para buscar informações contextuais em documentos
5. O bot responde ao usuário consolidando as informações e resultados

## Estrutura do Projeto
- **bot.py**: Código principal do bot Telegram e orquestração do Crew AI
- **agents.py**: Definição dos agentes e integração com AnythingLLM
- **api_utils.py**: Utilitários para comunicação com AnythingLLM
- **user_map.json**: Mapeamento de usuários e workspaces

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