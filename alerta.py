import requests
import time
import json
import re
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
ESTADO_FILE = 'estado_boss.json'

# Coordenadas Exatas das Bases (Calibradas)
BASES = {
    'SB': (1054, 987),  # Secronom Bunker (S) calibrado
    'N':  (1048, 1048), # Nastya's Holdout (N)
    'D':  (927, 1025),  # Dogg's Stockade (D)
    'P':  (972, 927),   # Precinct 13 (P)
    'F':  (1115, 966)   # Fort Pastor (F)
}

def calcular_distancia_base(bx, by, base_sigla='SB'):
    if bx == "???" or by == "???":
        return "Localização desconhecida"
    
    x, y = int(bx), int(by)
    base_x, base_y = BASES.get(base_sigla, BASES['SB'])
    
    # Matemática invertida para bater com o padrão do jogo (Base - Boss)
    diff_x = base_x - x
    diff_y = base_y - y
    
    dir_x = f"{abs(diff_x)}R" if diff_x > 0 else (f"{abs(diff_x)}L" if diff_x < 0 else "")
    dir_y = f"{abs(diff_y)}D" if diff_y > 0 else (f"{abs(diff_y)}U" if diff_y < 0 else "")
    
    # Formata como "2R5D de SB"
    posicao = f"{dir_x}{dir_y}".strip()
    if not posicao:
        posicao = "No mesmo bloco"
        
    return f"{posicao} de {base_sigla}"

def extrair_dados_boss(dados):
    json_str = json.dumps(dados)
    idx = json_str.find('Pumpkin Queen')
    
    if idx == -1:
        return "???", "???", False

    trecho = json_str[max(0, idx-200):min(len(json_str), idx+200)]
    
    # Deteta Boss Inativo/Verde (Tempo Esgotado)
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
    return {"alertado_inicio": False, "alertado_1h": False, "tempo_inicio": 0, "ultima_loc": ""}

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
        if 'Pumpkin Queen' not in str(dados):
            if os.path.exists(ESTADO_FILE):
                os.remove(ESTADO_FILE)
            return

        x, y, esta_ativo = extrair_dados_boss(dados)
        
        if not esta_ativo:
            print("🟢 Pumpkin Queen está visível, mas INATIVA/VERDE no código. Alerta bloqueado.")
            return

        estado = carregar_estado()
        agora = time.time()
        distancia_sb = calcular_distancia_base(x, y, 'SB')
        loc_atual = f"{x}x{y}"

        # 1º Alerta: Ao Spawnar
        if not estado["alertado_inicio"] or estado["ultima_loc"] != loc_atual:
            enviar_alerta(x, y, distancia_sb, tipo="inicio")
            estado["alertado_inicio"] = True
            estado["alertado_1h"] = False
            estado["tempo_inicio"] = agora
            estado["ultima_loc"] = loc_atual
            salvar_estado(estado)

        # 2º Alerta: Após 1 Hora (3600 seg)
        elif estado["alertado_inicio"] and not estado["alertado_1h"]:
            if (agora - estado["tempo_inicio"]) >= 3600:
                enviar_alerta(x, y, distancia_sb, tipo="1hora")
                estado["alertado_1h"] = True
                salvar_estado(estado)

    except Exception as e:
        print(f"Erro: {e}")

def enviar_alerta(x, y, distancia_str, tipo="inicio"):
    map_image_url = f"https://deadfrontier.info/w/map/images/Fairview_{x}x{y}.png" if x != "???" else ""
    titulo = "🎃 A Rainha das Aboborinhas Apareceuuuu!" if tipo == "inicio" else "⏰ A Rainha das Aboborinhas continua ativa! (1 Hora decorrida)"
    
    payload = {
        "content": f"@everyone {titulo} 🎃👑\nhttps://www.dfprofiler.com/bossmap\nÁrea: {x}x{y} ({distancia_str})",
        "embeds": [{
            "title": "Bossmap - Profiler",
            "description": f"Localização relativa: **{distancia_str}**",
            "color": 16711680 if tipo == "inicio" else 16744192,
            "image": {"url": map_image_url} if map_image_url else {}
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == '__main__':
    verificar_e_notificar()
