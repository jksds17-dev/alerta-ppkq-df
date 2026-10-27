import requests
import time
import json
import re
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
ESTADO_FILE = 'estado_bosses.json'

# Coordenadas Exatas das Bases (Calibradas)
BASES = {
    'SB': (1054, 987),   # Secronom Bunker (S)
    'N':  (1048, 1048),  # Nastya's Holdout (N)
    'D':  (927, 1025),   # Dogg's Stockade (D)
    'P':  (972, 927),    # Precinct 13 (P)
    'F':  (1115, 966),   # Fort Pastor (F)
    'Z':  (1058, 1019)   # Ground Zero / Zone 21 (Z) - Calibrado
}

# Configuração dos Bosses a monitorizar
ALVOS = {
    "Pumpkin Queen": {"base_ref": "SB", "emoji": "🎃", "cor": 16744192, "titulo": "A Rainha das Aboborinhas"},
    "Behemoth": {"base_ref": "Z", "emoji": "🦍", "cor": 8388736, "titulo": "Behemoth"},
    "Devil Hound": {"base_ref": "SB", "emoji": "🐺", "cor": 16711680, "titulo": "Devil Hound"},
    "8 x Bandits": {"base_ref": "SB", "emoji": "🥷", "cor": 0, "titulo": "8 Bandits"},
    "Volatile Leaper": {"base_ref": "P", "emoji": "🐸", "cor": 32768, "titulo": "Volatile Leaper"}
}

def calcular_distancia_base(bx, by, base_sigla):
    if bx == "???" or by == "???":
        return "Localização desconhecida"
    
    x, y = int(bx), int(by)
    base_x, base_y = BASES.get(base_sigla, BASES['SB'])
    
    # Matemática invertida padrão do Dead Frontier (Base - Boss)
    diff_x = base_x - x
    diff_y = base_y - y
    
    dir_x = f"{abs(diff_x)}R" if diff_x > 0 else (f"{abs(diff_x)}L" if diff_x < 0 else "")
    dir_y = f"{abs(diff_y)}D" if diff_y > 0 else (f"{abs(diff_y)}U" if diff_y < 0 else "")
    
    posicao = f"{dir_x}{dir_y}".strip()
    if not posicao:
        posicao = "No mesmo bloco"
        
    return f"{posicao} de {base_sigla}"

def extrair_dados_alvo(dados, nome_alvo):
    json_str = json.dumps(dados)
    idx = json_str.find(nome_alvo)
    
    if idx == -1:
        return "???", "???", False

    trecho = json_str[max(0, idx-200):min(len(json_str), idx+200)]
    
    # Deteta Boss Inativo/Verde
    esta_ativo = True
    if 'green' in trecho.lower() or 'expired' in trecho.lower() or 'active":false' in trecho.replace(" ", ""):
        esta_ativo = False

    texto_antes = json_str[0:idx]
    chaves_coords = re.findall(r'"(\d{3,4})[x_](\d{3,4})"', texto_antes)
    if chaves_coords:
        return chaves_coords[-1][0], chaves_coords[-1][1], esta_ativo

    padrao_xy = re.search(r'"x"\s*:\s*"?(\d{3,4})"?,?\s*"y"\s*:\s*"?(\d{3,4})"?', trecho)
    if padrao_xy:
        return padrao_xy.group(1), padrao_xy.group(2), esta_ativo

    return "???", "???", esta_ativo

def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {alvo: {"alertado_inicio": False, "alertado_1h": False, "tempo_inicio": 0, "ultima_loc": ""} for alvo in ALVOS.keys()}

def salvar_estado(estado):
    with open(ESTADO_FILE, 'w') as f:
        json.dump(estado, f)

def verificar_e_notificar():
    timestamp = int(time.time() * 1000)
    url = f"https://www.dfprofiler.com/bossmap/json/?_={timestamp}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.dfprofiler.com/bossmap',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        if resposta.status_code != 200:
            return
            
        dados = resposta.json()
        estado = carregar_estado()
        agora = time.time()
        estado_modificado = False

        for nome_alvo, config in ALVOS.items():
            if nome_alvo not in estado:
                estado[nome_alvo] = {"alertado_inicio": False, "alertado_1h": False, "tempo_inicio": 0, "ultima_loc": ""}

            if nome_alvo not in str(dados):
                if estado[nome_alvo]["alertado_inicio"]:
                    estado[nome_alvo] = {"alertado_inicio": False, "alertado_1h": False, "tempo_inicio": 0, "ultima_loc": ""}
                    estado_modificado = True
                continue

            x, y, esta_ativo = extrair_dados_alvo(dados, nome_alvo)
            
            if not esta_ativo:
                continue

            distancia_ref = calcular_distancia_base(x, y, config['base_ref'])
            loc_atual = f"{x}x{y}"

            # 1º Alerta: Ao Spawnar
            if not estado[nome_alvo]["alertado_inicio"] or estado[nome_alvo]["ultima_loc"] != loc_atual:
                enviar_alerta(nome_alvo, x, y, distancia_ref, config, tipo="inicio")
                estado[nome_alvo]["alertado_inicio"] = True
                estado[nome_alvo]["alertado_1h"] = False
                estado[nome_alvo]["tempo_inicio"] = agora
                estado[nome_alvo]["ultima_loc"] = loc_atual
                estado_modificado = True

            # 2º Alerta: Após 1 Hora (3600 seg)
            elif estado[nome_alvo]["alertado_inicio"] and not estado[nome_alvo]["alertado_1h"]:
                if (agora - estado[nome_alvo]["tempo_inicio"]) >= 3600:
                    enviar_alerta(nome_alvo, x, y, distancia_ref, config, tipo="1hora")
                    estado[nome_alvo]["alertado_1h"] = True
                    estado_modificado = True

        if estado_modificado:
            salvar_estado(estado)

    except Exception as e:
        print(f"Erro: {e}")

def enviar_alerta(nome_alvo, x, y, distancia_str, config, tipo="inicio"):
    map_image_url = f"https://deadfrontier.info/w/map/images/Fairview_{x}x{y}.png" if x != "???" else ""
    
    acao = "Apareceuuuu!" if tipo == "inicio" else "continua ativo! (1 Hora decorrida)"
    titulo = f"{config['titulo']} {acao}"
    
    payload = {
        "content": f"@everyone {titulo} {config['emoji']}\nhttps://www.dfprofiler.com/bossmap\nÁrea: {x}x{y} ({distancia_str})",
        "embeds": [{
            "title": "Bossmap - Profiler",
            "description": f"Localização relativa: **{distancia_str}**",
            "color": config['cor'] if tipo == "inicio" else 16744192,
            "image": {"url": map_image_url} if map_image_url else {}
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == '__main__':
    verificar_e_notificar()
