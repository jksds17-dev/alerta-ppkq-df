import requests
import time
import datetime
import json
import re
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
ESTADO_FILE = 'estado_dashboard.json'

BASES = {
    'SB': (1054, 987),
    'N':  (1048, 1048),
    'D':  (927, 1025),
    'P':  (972, 927),
    'F':  (1115, 966),
    'Z':  (1058, 1019)
}

# Organização por categorias para o Dashboard
CATEGORIAS = {
    "Daily Specials": [
        {"nome": "Volatile Leaper", "base": "P"},
        {"nome": "Behemoth", "base": "Z"},
        {"nome": "Devil Hound", "base": "SB"},
        {"nome": "8 x Bandits", "base": "SB"}
    ],
    "Event Bosses": [
        {"nome": "Pumpkin Queen", "base": "SB"}
    ]
}

def calcular_distancia_base(bx, by, base_sigla):
    if bx == "???" or by == "???":
        return ""
    x, y = int(bx), int(by)
    base_x, base_y = BASES.get(base_sigla, BASES['SB'])
    
    diff_x = x - base_x
    diff_y = y - base_y
    
    dir_x = f"{abs(diff_x)}R" if diff_x > 0 else (f"{abs(diff_x)}L" if diff_x < 0 else "")
    dir_y = f"{abs(diff_y)}D" if diff_y > 0 else (f"{abs(diff_y)}U" if diff_y < 0 else "")
    
    posicao = f"{dir_x}{dir_y}".strip()
    return f"{posicao} de {base_sigla}" if posicao else "No mesmo bloco"

def extrair_dados_alvo(dados, nome_alvo):
    # Função de alta precisão baseada em árvore (gavetas independentes)
    encontrado_x, encontrado_y, esta_ativo = "???", "???", False
    
    def iterar_nos(no, chave_pai=None):
        nonlocal encontrado_x, encontrado_y, esta_ativo
        if isinstance(no, dict):
            texto_no = json.dumps(no)
            if nome_alvo in texto_no:
                ativo = not ('green' in texto_no.lower() or 'expired' in texto_no.lower() or '"active": false' in texto_no.lower() or '"active":false' in texto_no.lower())
                
                if 'x' in no and 'y' in no:
                    encontrado_x, encontrado_y, esta_ativo = str(no['x']), str(no['y']), ativo
                    return True
                if chave_pai and re.match(r'^\d{3,4}[x_]\d{3,4}$', str(chave_pai)):
                    partes = str(chave_pai).replace('_', 'x').split('x')
                    encontrado_x, encontrado_y, esta_ativo = partes[0], partes[1], ativo
                    return True
                for k, v in no.items():
                    if nome_alvo in str(v) and re.match(r'^\d{3,4}[x_]\d{3,4}$', str(k)):
                        partes = str(k).replace('_', 'x').split('x')
                        encontrado_x, encontrado_y, esta_ativo = partes[0], partes[1], ativo
                        return True
            for k, v in no.items():
                if iterar_nos(v, k): return True
        elif isinstance(no, list):
            for item in no:
                if iterar_nos(item, chave_pai): return True
        return False

    iterar_nos(dados)
    return encontrado_x, encontrado_y, esta_ativo

def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, 'r') as f:
                estado = json.load(f)
                if "message_id" in estado:
                    return estado
        except:
            pass
    return {"message_id": None}

def salvar_estado(estado):
    with open(ESTADO_FILE, 'w') as f:
        json.dump(estado, f)

def formatar_linha(boss_info, dados_api):
    nome = boss_info["nome"]
    base = boss_info["base"]
    
    # Se o nome não existir de todo no JSON
    if nome not in str(dados_api):
        return f"❌ **{nome}**"
        
    x, y, esta_ativo = extrair_dados_alvo(dados_api, nome)
    
    if not esta_ativo or x == "???":
        return f"❌ **{nome}**"
        
    distancia = calcular_distancia_base(x, y, base)
    if distancia:
        return f"✅ **{nome}** — spotted: {x}x{y} ({distancia})"
    else:
        return f"✅ **{nome}** — spotted: {x}x{y}"

def atualizar_dashboard():
    timestamp = int(time.time() * 1000)
    url_api = f"https://www.dfprofiler.com/bossmap/json/?_={timestamp}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.dfprofiler.com/bossmap',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        resposta = requests.get(url_api, headers=headers, timeout=10)
        if resposta.status_code != 200:
            print("Erro ao aceder à API do DF Profiler.")
            return
            
        dados = resposta.json()
        estado = carregar_estado()
        
        # Calcular a hora atual no fuso horário do Brasil (UTC-3)
        agora_utc = datetime.datetime.utcnow()
        agora_br = agora_utc - datetime.timedelta(hours=3)
        hora_formatada = agora_br.strftime('%d/%m/%Y às %H:%M:%S')

        # Construir o texto das secções
        texto_specials = "\n".join([formatar_linha(b, dados) for b in CATEGORIAS["Daily Specials"]])
        texto_events = "\n".join([formatar_linha(b, dados) for b in CATEGORIAS["Event Bosses"]])

        descricao = (
            f"⏱️ **Last Checked:** {hora_formatada}\n\n"
            f"**Today's Daily Specials**\n{texto_specials}\n\n"
            f"**Today's Event Bosses**\n{texto_events}"
