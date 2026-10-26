import requests
import time
import json
import re
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
ESTADO_FILE = 'estado_boss.json'

# Coordenadas das Bases (Outposts)
BASES = {
    'SB': (1050, 980),  # Secronom Bunker (S)
    'N':  (1000, 1000), # Nastya's Holdout (N)
    'D':  (900, 1000),  # Dogg's Stockade (D)
    'P':  (1000, 900),  # Precinct 13 (P)
    'F':  (1100, 1000)  # Fort Pastor (F)
}

def calcular_distancia_base(bx, by, base_sigla='SB'):
    """Calcula a posição relativa em blocos (ex: 1U5L from SB)"""
    if bx == "???" or by == "???":
        return "Localização desconhecida"
    
    x, y = int(bx), int(by)
    base_x, base_y = BASES.get(base_sigla, BASES['SB'])
    
    diff_x = x - base_x
    diff_y = y - base_y
    
    # Direção X (R = Right/Direita, L = Left/Esquerda)
    dir_x = f"{abs(diff_x)}R" if diff_x > 0 else (f"{abs(diff_x)}L" if diff_x < 0 else "")
    # Direção Y (U = Up/Cima, D = Down/Baixo)
    dir_y = f"{abs(diff_y)}U" if diff_y < 0 else (f"{abs(diff_y)}D" if diff_y > 0 else "")
    
    posicao = f"{dir_y}{dir_x}".strip()
    if not posicao:
        posicao = "No mesmo bloco"
        
    return f"{posicao} de {base_sigla}"

def extrair_dados_boss(dados):
    """Extrai x, y e se o boss está ativo/vivo"""
    json_str = json.dumps(dados)
    idx = json_str.find('Pumpkin Queen')
    
    if idx == -1:
        return "???", "???", False

    trecho = json_str[max(0, idx-150):min(len(json_str), idx+150)]

    # Checa se está inativo/expirado (ex: cor verde no site, status inactive/dead)
    esta_ativo = True
    if '"active":false' in trecho.replace(" ", "") or '"status":"expired"' in trecho or '"color":"green"' in trecho:
        esta_ativo = False

    # Extrai coordenadas por Regex
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.dfprofiler.com/bossmap',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        if resposta.status_code != 200:
            print(f"Erro HTTP {resposta.status_code}")
            return
            
        dados = resposta.json()
        if 'Pumpkin Queen' not in str(dados):
            print("❌ Pumpkin Queen não está no mapa. Resetando estado.")
            if os.path.exists(ESTADO_FILE):
                os.remove(ESTADO_FILE)
            return

        x, y, esta_ativo = extrair_dados_boss(dados)
        
        # Se apareceu no site mas na cor verde (já não está disponível/expirou)
        if not esta_ativo:
            print("🟢 Pumpkin Queen está visível no mapa, mas EXPIRADA (Verde). Nenhum alerta enviado.")
            return

        estado = carregar_estado()
        agora = time.time()
        distancia_sb = calcular_distancia_base(x, y, 'SB')

        loc_atual = f"{x}x{y}"

        # 1. Primeiro Alerta: Ao aparecer
        if not estado["alertado_inicio"] or estado["ultima_loc"] != loc_atual:
            print(f"🎃 NOVA Pumpkin Queen Ativa! Localização: x{x}, y{y} ({distancia_sb})")
            enviar_alerta(x, y, distancia_sb, tipo="inicio")
            
            estado["alertado_inicio"] = True
            estado["alertado_1h"] = False
            estado["tempo_inicio"] = agora
            estado["ultima_loc"] = loc_atual
            salvar_estado(estado)

        # 2. Segundo Alerta: Após 1 hora (3600 segundos) de spawn ativo
        elif estado["alertado_inicio"] and not estado["alertado_1h"]:
            tempo_decorrido = agora - estado["tempo_inicio"]
            if tempo_decorrido >= 3600:
                print(f"⏰ Pumpkin Queen completa 1 hora no mapa! Reenviando alerta...")
                enviar_alerta(x, y, distancia_sb, tipo="1hora")
                
                estado["alertado_1h"] = True
                salvar_estado(estado)
            else:
                minutos_restantes = int((3600 - tempo_decorrido) / 60)
                print(f"⏳ Boss ativo. Faltam ~{minutos_restantes} min para o alerta de 1 hora.")

    except Exception as e:
        print(f"Erro ao verificar: {e}")

def enviar_alerta(x, y, distancia_str, tipo="inicio"):
    map_image_url = f"https://deadfrontier.info/w/map/images/Fairview_{x}x{y}.png" if x != "???" else ""
    
    titulo_status = "🎃 A Rainha das Aboborinhas Apareceuuuu!" if tipo == "inicio" else "⏰ A Rainha das Aboborinhas continua ativa! (1 Hora decorrida)"
    
    payload = {
        "content": f"@everyone {titulo_status} 🎃👑\nhttps://www.dfprofiler.com/bossmap\nÁrea: {x}x{y} ({distancia_str})",
        "embeds": [{
            "title": "Bossmap - Profiler",
            "description": f"Localização relativa: **{distancia_str}**\nClique no link acima para ver o mapa interativo.",
            "color": 16711680 if tipo == "inicio" else 16744192, # Vermelho no início, Laranja após 1h
            "image": {"url": map_image_url} if map_image_url else {}
        }]
    }
    
    res = requests.post(WEBHOOK_URL, json=payload)
    print(f"Status do envio para o Discord: {res.status_code}")

if __name__ == '__main__':
    verificar_e_notificar()
