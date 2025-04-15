import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import logging
import json

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

API_BASE = None
API_KEY = None

def setup_api(base_url, api_key):
    global API_BASE, API_KEY
    API_BASE = base_url.rstrip('/')
    API_KEY = api_key
    logger.info(f"API configurada com base URL: {API_BASE}")

def get_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

def check_api_status():
    try:
        url = f"{API_BASE}/v1/system"
        response = requests.get(url, headers=get_headers(), timeout=10, verify=False)
        response.raise_for_status()
        logger.debug("API do AnythingLLM está disponível.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"API do AnythingLLM não disponível: {str(e)}")
        return False

def list_workspaces():
    try:
        url = f"{API_BASE}/v1/workspaces"
        response = requests.get(url, headers=get_headers(), timeout=10, verify=False)
        response.raise_for_status()
        return response.json().get("workspaces", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao listar workspaces: {str(e)}")
        return []

def create_workspace(user_id):
    try:
        url = f"{API_BASE}/v1/workspace/new"
        workspace_name = f"telegram-user-{user_id}"
        
        # Incluir todas as configurações diretamente no payload de criação
        payload = {
            "name": workspace_name,
            "similarityThreshold": 0.50,
            "openAiTemp": 0.5,
            "openAiHistory": 20,
            "openAiPrompt": (
                "Você é a IA-amarela, a assistente executiva virtual da Amarelo, uma empresa de delivery de comida. "
                "Seu objetivo é ser a melhor parceira dos gestores, fornecendo análises detalhadas, relatórios completos e "
                "insights estratégicos para otimizar o negócio. "
                "Você tem acesso total a todos os dados da empresa embedded neste workspace, incluindo planilhas, PDFs, relatórios, e-mails, registros de clientes, operações, "
                "faturamento, custos, lucros, churn, campanhas de marketing e mais. Além disso, você pode usar ferramentas de pesquisa na internet para complementar suas respostas "
                "e possui capacidade de gerar gráficos e visualizações baseados nos dados disponíveis.\n\n"
                "Instruções:\n"
                "1. Baseie-se nos Dados Embedded: Sempre priorize os dados embedded no workspace como fonte principal. Cruze informações de diferentes documentos "
                "(ex.: faturamento com custos para calcular margens) e gere relatórios completos quando solicitado.\n"
                "2. Análise Avançada: Realize cálculos precisos (ex.: churn, faturamento entre datas, margem de lucro) e apresente os resultados com explicações claras, "
                "incluindo a origem dos dados e os passos do cálculo.\n"
                "3. Relatórios Sob Demanda: Se eu pedir um relatório (ex.: 'Relatório de faturamento de 2025'), organize os dados em um formato estruturado, com números, "
                "comparações e insights úteis.\n"
                "4. Estratégias e Sugestões: Quando solicitado (ex.: 'Sugira uma estratégia de marketing'), analise os dados embedded, identifique padrões "
                "(ex.: campanhas mais eficazes) e proponha ideias práticas, inovadoras e fundamentadas, detalhando os benefícios esperados.\n"
                "5. Pesquisa na Internet: Se os dados embedded não forem suficientes, use ferramentas de pesquisa na internet para buscar informações relevantes "
                "(ex.: tendências de mercado no setor de delivery) e integre isso às suas respostas, citando fontes quando aplicável.\n"
                "6. Geração de Gráficos: Se eu pedir gráficos ou visualizações (ex.: 'Mostre um gráfico de faturamento mensal'), descreva os dados em texto como se estivesse "
                "gerando um gráfico (ex.: 'Gráfico de barras: Janeiro R$ 150 mil, Fevereiro R$ 170 mil...') com base nos dados embedded.\n"
                "7. Proatividade: Sempre que possível, vá além da pergunta inicial, oferecendo insights adicionais ou alertas "
                "(ex.: 'Notei que o churn aumentou 5% em março; sugiro investigar a satisfação do cliente nesse período').\n"
                "8. Limitações: Se os dados necessários não estiverem no workspace e a pesquisa na internet não for suficiente, diga: "
                "'Não tenho dados suficientes no workspace ou na internet para responder completamente. Posso ajudar com outra coisa?'\n"
                "9. Tom e Estilo: Adote um tom profissional, confiante e colaborativo, como uma assistente executiva experiente que está sempre pronta para apoiar os gestores da Amarelo."
            ),
            "queryRefusalResponse": "Não tenho dados suficientes no workspace ou na internet para responder completamente. Posso ajudar com outra coisa?",
            "chatMode": "chat",
            "topN": 5,
            "searchPreference": "accuracy_optimized",
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        response = requests.post(url, json=payload, headers=get_headers(), timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()
        workspace_slug = data.get("slug")
        if workspace_slug:
            logger.info(f"Workspace criado com sucesso para user_id {user_id}: {workspace_slug}")
            return workspace_slug
        else:
            logger.error("Slug do workspace não encontrado na resposta.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao criar workspace para user_id {user_id}: {str(e)}")
        return None



def get_or_create_workspace(user_id):
    workspaces = list_workspaces()
    workspace_name = f"telegram-user-{user_id}"
    for ws in workspaces:
        if ws.get("name") == workspace_name:
            return ws.get("slug")
    return create_workspace(user_id)

def list_workspace_documents(workspace_slug):
    try:
        url = f"{API_BASE}/v1/workspace/{workspace_slug}/documents"
        response = requests.get(url, headers=get_headers(), timeout=10, verify=False)
        response.raise_for_status()
        return response.json().get("documents", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao listar documentos do workspace {workspace_slug}: {str(e)}")
        return []

async def upload_file_to_anythingllm(file_path, file_name):
    try:
        url = f"{API_BASE}/v1/document/upload"
        files = {'file': (file_name, open(file_path, 'rb'), 'application/octet-stream')}
        headers = get_headers()
        headers.pop("Content-Type")  # Remover para multipart/form-data
        response = requests.post(url, files=files, headers=headers, timeout=60, verify=False)
        response.raise_for_status()
        data = response.json()
        location = data.get("documents", [{}])[0].get("location")
        logger.info(f"Arquivo {file_name} enviado ao AnythingLLM com localização: {location}")
        return True, location
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar arquivo {file_name} ao AnythingLLM: {str(e)}")
        return False, None

async def update_workspace_embeddings(workspace_slug, adds=None, removes=None):
    try:
        url = f"{API_BASE}/v1/workspace/{workspace_slug}/update-embeddings"
        payload = {}
        if adds:
            payload["adds"] = adds
        if removes:
            payload["removes"] = removes
        response = requests.post(url, json=payload, headers=get_headers(), timeout=600, verify=False)
        response.raise_for_status()
        logger.info(f"Embeddings atualizados no workspace {workspace_slug}: {json.dumps(payload)}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao atualizar embeddings no workspace {workspace_slug}: {str(e)}")
        return False

def list_all_custom_documents():
    try:
        url = f"{API_BASE}/v1/documents"
        response = requests.get(url, headers=get_headers(), timeout=10, verify=False)
        response.raise_for_status()
        documents = response.json().get("documents", {})
        return list(documents.keys())
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao listar todos os documentos customizados: {str(e)}")
        return []

def get_documents_to_embed(workspace_slug):
    """Retorna uma lista de documentos que estão disponíveis mas não embedados no workspace."""
    try:
        # Obter todos os documentos disponíveis no AnythingLLM
        all_documents = list_all_custom_documents()
        if not all_documents:
            logger.info("Nenhum documento disponível para embedding.")
            return []
        
        # Obter documentos já embedados no workspace
        workspace_docs = list_workspace_documents(workspace_slug)
        embedded_locations = {doc.get("docpath") for doc in workspace_docs if doc.get("docpath")}
        
        # Filtrar documentos que não estão embedados
        files_to_embed = [loc for loc in all_documents if loc not in embedded_locations]
        
        logger.info(f"Encontrados {len(files_to_embed)} documentos para embedding no workspace {workspace_slug}")
        return files_to_embed
    except Exception as e:
        logger.error(f"Erro ao verificar documentos para embedding: {str(e)}")
        return []