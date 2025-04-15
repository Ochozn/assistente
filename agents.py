# agents.py
from crewai import Agent
from api_utils import (
    list_workspace_documents, list_all_custom_documents, get_headers
)
import requests
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente para os agentes
load_dotenv()
ANYTHINGLLM_API = os.getenv("ANYTHINGLLM_API")
ANYTHINGLLM_API_KEY = os.getenv("ANYTHINGLLM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não encontrado no .env. É necessário para o CrewAI.")

# Configurar o CrewAI para usar OpenAI
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Função para consultar o chat do AnythingLLM
def fetch_anythingllm_chat(query, workspace_slug, session_id):
    url = f"{ANYTHINGLLM_API}/v1/workspace/{workspace_slug}/chat"
    payload = {
        "message": query,
        "mode": "chat",
        "sessionId": session_id,
        "attachments": []
    }
    headers = get_headers()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=600, verify=False)
        response.raise_for_status()
        data = response.json()
        return data.get("textResponse", "")
    except Exception as e:
        return f"Erro ao buscar dados via chat: {str(e)}"

# Funções ajustadas para o Bibliotecário
def fetch_workspace_documents(workspace_slug):
    try:
        docs = list_workspace_documents(workspace_slug)
        return [doc.get("docpath", "Sem nome") for doc in docs]
    except Exception as e:
        return f"Erro ao listar documentos do workspace: {str(e)}"

def fetch_all_custom_documents():
    try:
        docs = list_all_custom_documents()
        return docs
    except Exception as e:
        return f"Erro ao listar todos os documentos: {str(e)}"

# Definição dos Agentes
coordenador = Agent(
    role="Coordenador",
    goal="Receber solicitações do gestor, delegar tarefas aos agentes apropriados e consolidar respostas",
    backstory="Você é o núcleo da IA Amarela, coordenando agentes especializados para ajudar gestores da Amarelo, uma empresa de delivery de comida.",
    verbose=True,
    allow_delegation=True
)

bibliotecario = Agent(
    role="Bibliotecário",
    goal="Buscar e fornecer dados embedados no banco vetorizado do AnythingLLM",
    backstory="Você é o guardião dos dados da Amarelo, especializado em encontrar informações precisas no banco vetorizado usando todas as APIs disponíveis.",
    tools=[
        fetch_anythingllm_chat,       # Consulta via chat
        fetch_workspace_documents,    # Lista documentos embedados no workspace
        fetch_all_custom_documents    # Lista todos os documentos no AnythingLLM
    ],
    verbose=True,
    allow_delegation=False
)

financeiro = Agent(
    role="Analista Financeiro",
    goal="Realizar cálculos financeiros e fornecer insights baseados em dados",
    backstory="Você é um especialista financeiro da Amarelo, analisando faturamento, custos e margens para os gestores.",
    verbose=True,
    allow_delegation=False
)