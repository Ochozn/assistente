import os
import logging
import signal
import sys
import time
import asyncio
from queue import Queue
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import urllib.parse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from api_utils import (
    setup_api, get_headers, check_api_status, list_workspaces, create_workspace, get_or_create_workspace,
    list_workspace_documents, upload_file_to_anythingllm, update_workspace_embeddings, list_all_custom_documents
)

# Desativar avisos de SSL inseguro
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANYTHINGLLM_API = os.getenv("ANYTHINGLLM_API")
ANYTHINGLLM_API_KEY = os.getenv("ANYTHINGLLM_API_KEY")

if not all([TELEGRAM_TOKEN, ANYTHINGLLM_API, ANYTHINGLLM_API_KEY]):
    logger.error("Uma ou mais variáveis de ambiente estão ausentes. Verifique o arquivo .env.")
    exit(1)

# Configurar api_utils
setup_api(ANYTHINGLLM_API, ANYTHINGLLM_API_KEY)

# Arquivos de configuração locais
FILE_MAP_FILE = "file_map.json"
USER_MAP_FILE = "user_map.json"
CHART_URL_LOG = "chart_urls.txt"
EXPENSES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lançamentos")
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documentos")
GRAPHICS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gráficos")
os.makedirs(EXPENSES_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(GRAPHICS_DIR, exist_ok=True)

def load_file_map():
    if os.path.exists(FILE_MAP_FILE):
        with open(FILE_MAP_FILE, "r") as f:
            return json.load(f)
    return {}

def save_file_map(file_map):
    with open(FILE_MAP_FILE, "w") as f:
        json.dump(file_map, f, indent=2)

def load_user_map():
    if os.path.exists(USER_MAP_FILE):
        with open(USER_MAP_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_map(user_map):
    with open(USER_MAP_FILE, "w") as f:
        json.dump(user_map, f, indent=2)

def save_chart_urls(original_url, fixed_url):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}]\nOriginal (falha): {original_url}\nCorrigida: {fixed_url}\n\n"
    with open(CHART_URL_LOG, "a") as f:
        f.write(log_entry)
    logger.debug(f"URLs salvas em {CHART_URL_LOG}")

def fix_chart_url(chart_url):
    try:
        if "quickchart.io/chart?c=" not in chart_url:
            logger.warning(f"URL do gráfico não contém 'quickchart.io/chart?c=': {chart_url}")
            return chart_url
        
        chart_config_str = chart_url.split("quickchart.io/chart?c=")[1]
        try:
            chart_config = json.loads(chart_config_str)
        except json.JSONDecodeError:
            chart_config_str = chart_config_str.replace("'", '"')
            chart_config = json.loads(chart_config_str)
        
        def replace_special_chars(obj):
            if isinstance(obj, str):
                replacements = {
                    "R$": "Real",
                    "%20": " ",
                    "$": "USD",
                    "€": "EUR",
                    "£": "GBP",
                    "%": "pct",
                    "&": "and"
                }
                result = obj
                for old, new in replacements.items():
                    result = result.replace(old, new)
                return result
            elif isinstance(obj, dict):
                return {k: replace_special_chars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_special_chars(item) for item in obj]
            return obj
        
        fixed_config = replace_special_chars(chart_config)
        fixed_config_str = json.dumps(fixed_config)
        encoded_config = urllib.parse.quote(fixed_config_str)
        
        fixed_url = f"https://quickchart.io/chart?c={encoded_config}&format=png"
        logger.debug(f"URL do gráfico corrigido: {fixed_url}")
        return fixed_url
    except Exception as e:
        logger.error(f"Erro ao corrigir o chart_url: {str(e)}")
        return chart_url

def download_chart_image(chart_url):
    try:
        if not chart_url or "quickchart.io/chart" not in chart_url:
            logger.error(f"URL inválida ou não é do QuickChart: {chart_url}")
            return None
        
        logger.debug(f"Baixando imagem do URL: {chart_url}")
        response = requests.get(chart_url, timeout=30, verify=False)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "")
        logger.debug(f"Content-Type da resposta: {content_type}")
        
        if "image/png" not in content_type:
            logger.error(f"Resposta não é uma imagem PNG: {content_type}")
            return None
        
        timestamp = int(time.time())
        final_filename = f"gráfico_{timestamp}.png"
        final_path = os.path.join(GRAPHICS_DIR, final_filename)
        
        with open(final_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Imagem baixada e salva como PNG em: {final_path}")
        
        return final_path
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar a imagem do URL {chart_url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar a imagem: {str(e)}")
        return None

async def delete_document_from_anythingllm(docpath):
    """Deleta completamente um documento do AnythingLLM pelo docpath."""
    url = f"{ANYTHINGLLM_API}/v1/document/delete"
    payload = {"location": docpath}
    headers = get_headers()
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        logger.info(f"Documento {docpath} deletado completamente do AnythingLLM.")
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar documento {docpath}: {str(e)}")
        return False

async def remove_document_from_workspace(workspace_slug, docpath):
    """Remove um documento do contexto do workspace."""
    url = f"{ANYTHINGLLM_API}/v1/workspace/{workspace_slug}/update-embeddings"
    payload = {"removes": [docpath]}
    headers = get_headers()
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        logger.info(f"Documento {docpath} removido do contexto do workspace {workspace_slug}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao remover documento do contexto {docpath}: {str(e)}")
        return False

async def reset_chat(workspace_slug, session_id):
    """Reseta o histórico do chat atual no AnythingLLM."""
    url = f"{ANYTHINGLLM_API}/v1/workspace/{workspace_slug}/chat/reset"
    payload = {"sessionId": session_id}
    headers = get_headers()
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        logger.info(f"Chat {session_id} resetado no workspace {workspace_slug}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao resetar chat {session_id}: {str(e)}")
        return False

async def process_manual_expense(message, user_id, username, workspace_slug, context):
    """Processa despesas manuais, atualiza o arquivo JSON, deleta o antigo e reinsere no AnythingLLM."""
    try:
        import re
        pattern = r"(?:Gastei\s+)?(?:R\$|Real)?\s*(\d+(?:\.\d{2})?)\s*(?:com)?\s*([\w\s]+?)(?:\s+(hoje|ontem|\d{2}/\d{2}/\d{4}))?$"
        match = re.match(pattern, message, re.IGNORECASE)
        if not match:
            await context.bot.send_message(chat_id=context._chat_id, text="Formato inválido. Use: 'Gastei R$ 20 com produto x hoje'.")
            return

        value, description, date_str = match.groups()
        value = float(value)

        # Determinar a data
        if not date_str or date_str.lower() == "hoje":
            date = datetime.now().strftime("%Y-%m-%d")
        elif date_str.lower() == "ontem":
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            date = datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")

        # Criar entrada de despesa
        expense = {
            "date": date,
            "value": value,
            "description": description.strip(),
            "timestamp": int(time.time())
        }

        # Nome do arquivo único por usuário na pasta lançamentos
        file_name = f"{username}/expenses_{user_id}.json"
        local_path = os.path.join(EXPENSES_DIR, file_name)

        # Carregar despesas existentes ou criar nova lista
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                expenses = json.load(f)
        else:
            expenses = []

        # Adicionar nova despesa
        expenses.append(expense)

        # Salvar o arquivo atualizado localmente
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(expenses, f, ensure_ascii=False, indent=2)

        # Verificar se o arquivo já está embedado e deletá-lo completamente
        old_docpath = FILE_MAP.get(file_name)
        if old_docpath:
            await remove_document_from_workspace(workspace_slug, old_docpath)
            if await delete_document_from_anythingllm(old_docpath):
                del FILE_MAP[file_name]
                save_file_map(FILE_MAP)
            else:
                await context.bot.send_message(chat_id=context._chat_id, text="Erro ao deletar o arquivo antigo do AnythingLLM.")
                return

        # Enviar o arquivo atualizado ao AnythingLLM
        upload_success, location = await upload_file_to_anythingllm(local_path, file_name)
        if not upload_success or not location:
            await context.bot.send_message(chat_id=context._chat_id, text="Erro ao enviar despesa ao AnythingLLM.")
            return

        # Adicionar o novo arquivo ao contexto
        embedding_success = await update_workspace_embeddings(workspace_slug, adds=[location])
        if embedding_success:
            FILE_MAP[file_name] = location
            save_file_map(FILE_MAP)
            await context.bot.send_message(
                chat_id=context._chat_id,
                text=f"Despesa registrada: R$ {value:.2f} em '{description}' em {date}. Contexto atualizado!"
            )
        else:
            await context.bot.send_message(chat_id=context._chat_id, text="Erro ao atualizar o contexto.")

    except Exception as e:
        logger.error(f"Erro ao processar despesa: {str(e)}")
        await context.bot.send_message(chat_id=context._chat_id, text=f"Erro: {str(e)}")

async def chat_with_anythingllm(message, workspace_slug, session_id, update, context):
    logger.info(f"Enviando mensagem para AnythingLLM no workspace {workspace_slug} com sessionId {session_id}: '{message}'")
    url = f"{ANYTHINGLLM_API}/v1/workspace/{workspace_slug}/chat"
    
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or f"User{user_id}"

    # Verificar se é uma despesa manual
    if message.lower().startswith("gastei"):
        await process_manual_expense(message, user_id, username, workspace_slug, context)
        return

    enhanced_message = (
        f"{message}. Quando solicitado um gráfico, use a ferramenta `create-chart` e retorne a URL do QuickChart no campo `chart.url` do response body da API, "
        "sem incluir a URL no texto da resposta. Não use placeholders como '[Gráfico]' ou Markdown como '![Gráfico](URL)'. "
        "Exemplo de resposta esperada: {{'textResponse': 'Aqui está o gráfico solicitado', 'chart': {{'url': 'https://quickchart.io/chart?c=...'}}}}."
    ) if "@agent" in message and "gráfico" in message.lower() else message
    
    payload = {
        "message": enhanced_message,
        "mode": "chat",
        "sessionId": session_id,
        "attachments": []
    }
    
    headers = get_headers()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=600, verify=False)
        response.raise_for_status()
        data = response.json()
        
        text_response = data.get("textResponse", "")
        sources = data.get("sources", [])
        chart = data.get("chart", {})
        chart_url = chart.get("url") if chart else None
        
        if not chart_url and "https://quickchart.io/chart?c=" in text_response:
            import re
            url_match = re.search(r'(https://quickchart\.io/chart\?c=[^\s\)]+)', text_response)
            if url_match:
                chart_url = url_match.group(0)
                text_response = re.sub(r'!\[.*?\]\(https://quickchart\.io/chart\?c=[^\s\)]+\)', '', text_response).strip()
        
        if not text_response and not chart_url:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Desculpe, não recebi nenhuma resposta ou gráfico.")
            return
        
        if text_response:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text_response)
        
        if sources:
            sources_text = "\n\nFontes utilizadas:\n" + "\n".join([f"- {s['title']}: {s.get('chunk', 'N/A')}" for s in sources])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=sources_text)
        
        if chart_url:
            processing_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Baixando gráfico...")
            fixed_chart_url = fix_chart_url(chart_url)
            save_chart_urls(chart_url, fixed_chart_url)
            chart_path = download_chart_image(fixed_chart_url)
            if chart_path:
                with open(chart_path, "rb") as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Erro ao baixar o gráfico.")
        
    except Exception as e:
        logger.error(f"Erro ao comunicar com AnythingLLM: {str(e)}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Erro: {str(e)}")

async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user_id = str(update.message.from_user.id)
    
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return
    
    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    all_documents = list_all_custom_documents()
    if not all_documents:
        await update.message.reply_text("Nenhum documento encontrado para sincronizar.")
        return
    
    workspace_docs = list_workspace_documents(workspace_slug)
    embedded_locations = {doc.get("docpath") for doc in workspace_docs if doc.get("docpath")}
    files_to_embed = [loc for loc in all_documents if loc not in embedded_locations]
    
    if not files_to_embed:
        await update.message.reply_text("Todos os documentos já estão sincronizados.")
        return
    
    success = await update_workspace_embeddings(workspace_slug, adds=files_to_embed)
    if success:
        await update.message.reply_text(f"{len(files_to_embed)} documentos sincronizados com sucesso!")
    else:
        await update.message.reply_text("Erro ao sincronizar documentos.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user = update.message.from_user
    user_id = str(user.id)
    username = user.username if user.username else f"User{user_id}"
    
    if not check_api_status():
        await update.message.reply_text("Erro: A API do AnythingLLM não está disponível.")
        return
    
    if user_id not in USER_WORKSPACE_MAP:
        workspace_slug = get_or_create_workspace(user_id)
        if not workspace_slug:
            await update.message.reply_text("Erro ao configurar seu workspace.")
            return
        
        USER_WORKSPACE_MAP[user_id] = {
            "user_id": user.id,
            "username": username,
            "first_name": user.first_name,
            "workspace": workspace_slug,
            "active_thread": f"telegram-{user_id}-thread-{int(time.time())}",
            "threads": {f"telegram-{user_id}-thread-{int(time.time())}": "Chat Inicial"}
        }
        save_user_map(USER_WORKSPACE_MAP)
    
    await update.message.reply_text(f"Olá, {user.first_name}! Seu workspace está pronto. Use /help para mais informações.")

async def novo_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user_id = str(update.message.from_user.id)
    
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return
    
    args = context.args
    thread_name = " ".join(args) if args else f"Thread {int(time.time())}"
    new_session_id = f"telegram-{user_id}-thread-{int(time.time())}"
    
    USER_WORKSPACE_MAP[user_id]["threads"][new_session_id] = thread_name
    USER_WORKSPACE_MAP[user_id]["active_thread"] = new_session_id
    save_user_map(USER_WORKSPACE_MAP)
    
    await update.message.reply_text(f"Nova thread criada: '{thread_name}' ({new_session_id}).")

async def historico_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user_id = str(update.message.from_user.id)
    
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return
    
    threads = USER_WORKSPACE_MAP[user_id]["threads"]
    active_thread = USER_WORKSPACE_MAP[user_id]["active_thread"]
    
    message = "Suas threads de chat:\n"
    for idx, (session_id, name) in enumerate(threads.items(), 1):
        status = " (ativa)" if session_id == active_thread else ""
        message += f"{idx}. {name} ({session_id}){status}\n"
    message += "\nPara alternar, use /historico_chat <número>"
    
    args = context.args
    if args:
        try:
            idx = int(args[0]) - 1
            if 0 <= idx < len(threads):
                new_active_thread = list(threads.keys())[idx]
                USER_WORKSPACE_MAP[user_id]["active_thread"] = new_active_thread
                save_user_map(USER_WORKSPACE_MAP)
                await update.message.reply_text(f"Thread alterada para: '{threads[new_active_thread]}'")
            else:
                await update.message.reply_text("Número inválido.")
        except ValueError:
            await update.message.reply_text("Use um número válido.")
    else:
        await update.message.reply_text(message)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user_id = str(update.message.from_user.id)
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return

    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    session_id = USER_WORKSPACE_MAP[user_id]["active_thread"]

    if await reset_chat(workspace_slug, session_id):
        await update.message.reply_text(f"Chat {session_id} resetado com sucesso!")
    else:
        await update.message.reply_text("Erro ao resetar o chat.")

async def documentos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user_id = str(update.message.from_user.id)
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return

    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    embedded_docs = list_workspace_documents(workspace_slug)

    if not embedded_docs:
        await update.message.reply_text("Nenhum documento embedado no seu contexto atual.")
        return

    doc_list = "\n".join([f"- {doc.get('docpath', 'Sem nome')}" for doc in embedded_docs])
    await update.message.reply_text(f"Documentos embedados no seu contexto:\n{doc_list}")

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP, FILE_MAP
    user_id = str(update.message.from_user.id)
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return

    if not context.args:
        await update.message.reply_text("Use: /remove [nome_do_arquivo] (ex.: /remove user123/expenses_123456789.json)")
        return

    file_name = " ".join(context.args)
    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    docpath = FILE_MAP.get(file_name)

    if not docpath:
        await update.message.reply_text(f"Arquivo '{file_name}' não encontrado no contexto.")
        return

    if await remove_document_from_workspace(workspace_slug, docpath):
        del FILE_MAP[file_name]
        save_file_map(FILE_MAP)
        await update.message.reply_text(f"Arquivo '{file_name}' removido do contexto com sucesso!")
    else:
        await update.message.reply_text(f"Erro ao remover '{file_name}' do contexto.")

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP, FILE_MAP
    user_id = str(update.message.from_user.id)
    if user_id not in USER_WORKSPACE_MAP:
        await update.message.reply_text("Use /start para configurar seu workspace primeiro.")
        return

    if not context.args:
        await update.message.reply_text("Use: /delete [nome_do_arquivo] (ex.: /delete user123/expenses_123456789.json)")
        return

    file_name = " ".join(context.args)
    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    docpath = FILE_MAP.get(file_name)

    if not docpath:
        await update.message.reply_text(f"Arquivo '{file_name}' não encontrado no contexto.")
        return

    if await remove_document_from_workspace(workspace_slug, docpath) and await delete_document_from_anythingllm(docpath):
        del FILE_MAP[file_name]
        save_file_map(FILE_MAP)
        await update.message.reply_text(f"Arquivo '{file_name}' deletado completamente do AnythingLLM!")
    else:
        await update.message.reply_text(f"Erro ao deletar '{file_name}'.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "Comandos disponíveis:\n\n"
        "/start - Configura seu workspace.\n"
        "/novo_chat [nome] - Cria uma nova thread.\n"
        "/historico_chat - Lista suas threads.\n"
        "/reset - Reseta o chat atual.\n"
        "/sync - Sincroniza documentos.\n"
        "/documentos - Lista documentos embedados.\n"
        "/remove [arquivo] - Remove um documento do contexto.\n"
        "/delete [arquivo] - Deleta um documento do AnythingLLM.\n"
        "/help - Mostra esta mensagem.\n\n"
        "Envie 'Gastei R$ 20 com produto x hoje' para registrar despesas.\n"
        "Use '@agent Crie um gráfico...' para gráficos."
    )
    await update.message.reply_text(help_message)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP
    user = update.message.from_user
    user_id = str(user.id)
    
    if not check_api_status():
        await update.message.reply_text("Erro: A API está indisponível.")
        return
    
    if user_id not in USER_WORKSPACE_MAP:
        await start(update, context)
    
    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    session_id = USER_WORKSPACE_MAP[user_id]["active_thread"]
    message = update.message.text
    
    await chat_with_anythingllm(message, workspace_slug, session_id, update, context)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_WORKSPACE_MAP, FILE_MAP
    user = update.message.from_user
    user_id = str(user.id)
    username = user.username if user.username else f"User{user_id}"
    
    if update.message.document:
        file = update.message.document
        file_name_orig = file.file_name
    elif update.message.photo:
        file = update.message.photo[-1]
        file_name_orig = f"photo_{file.file_id}.jpg"
    else:
        await update.message.reply_text("Nenhum arquivo detectado.")
        return

    file_obj = await file.get_file()
    user_dir = os.path.join(DOCUMENTS_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    local_file_path = os.path.join(user_dir, file_name_orig)
    await file_obj.download_to_drive(local_file_path)
    
    file_name = f"{username}/{file_name_orig}"
    
    if user_id not in USER_WORKSPACE_MAP:
        if not check_api_status():
            await update.message.reply_text("API indisponível.")
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            return
        workspace_slug = get_or_create_workspace(user_id)
        if not workspace_slug:
            await update.message.reply_text("Erro ao configurar seu workspace.")
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            return
        USER_WORKSPACE_MAP[user_id] = {
            "user_id": user.id,
            "username": username,
            "first_name": user.first_name,
            "workspace": workspace_slug,
            "active_thread": f"telegram-{user_id}-thread-{int(time.time())}",
            "threads": {f"telegram-{user_id}-thread-{int(time.time())}": "Chat Inicial"}
        }
        save_user_map(USER_WORKSPACE_MAP)
    
    workspace_slug = USER_WORKSPACE_MAP[user_id]["workspace"]
    
    async def process_file():
        try:
            upload_success, location = await upload_file_to_anythingllm(local_file_path, file_name)
            if not upload_success or not location:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Erro ao enviar o arquivo.")
                return

            FILE_MAP[file_name] = location
            save_file_map(FILE_MAP)
            if await update_workspace_embeddings(workspace_slug, adds=[location]):
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Arquivo adicionado ao workspace!")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Erro ao adicionar ao workspace.")
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {str(e)}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Erro ao processar o arquivo.")

    asyncio.create_task(process_file())
    await update.message.reply_text("Arquivo sendo processado em segundo plano.")

def signal_handler(sig, frame):
    logger.info("Encerrando o bot...")
    TASK_QUEUE.put(None)
    sys.exit(0)

USER_WORKSPACE_MAP = {}
FILE_MAP = {}
TASK_QUEUE = Queue()

def main():
    signal.signal(signal.SIGINT, signal_handler)
    if not check_api_status():
        logger.error("API do AnythingLLM não está disponível.")
        sys.exit(1)
    
    global USER_WORKSPACE_MAP, FILE_MAP
    USER_WORKSPACE_MAP = load_user_map()
    FILE_MAP = load_file_map()
    
    logger.info("Bot iniciado.")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("novo_chat", novo_chat))
    app.add_handler(CommandHandler("historico_chat", historico_chat))
    app.add_handler(CommandHandler("sync", sync_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("documentos", documentos_command))
    app.add_handler(CommandHandler("remove", remove_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    
    worker_loop = asyncio.new_event_loop()
    worker_thread = Thread(target=lambda: worker_loop.run_until_complete(background_worker()), daemon=True)
    worker_thread.start()
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário.")
    finally:
        app.stop()
        worker_loop.stop()
        worker_loop.close()

async def background_worker():
    while True:
        try:
            task = TASK_QUEUE.get()
            if task is None:
                break
            await task()
            TASK_QUEUE.task_done()
        except Exception as e:
            logger.error(f"Erro no worker de fundo: {str(e)}")
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    main()