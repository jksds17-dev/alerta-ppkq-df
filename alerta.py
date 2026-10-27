import requests
import time
import json
import re
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
ESTADO_FILE = 'estado_bosses.json'

BASES = {
    'SB': (1054, 987),
    'N':  (1048, 1048),
    'D':  (927, 1025),
    'P':  (972, 927),
    'F':  (1115, 966),
    'Z':  (1058, 1019)
}

ALVOS = {
    "Pumpkin Queen": {"base_ref": "SB", "emoji": "🎃", "cor": 16744192, "titulo": "A Rainha das Aboborinhas", "mostrar_distancia": True},
    "Behemoth": {"base_ref": "Z", "emoji": "🦍", "cor": 8388736, "titulo": "Behemoth", "mostrar_distancia": True},
    "Devil Hound": {"base_ref": "SB", "emoji": "🐺", "cor": 16711680, "titulo": "Devil Hound", "mostrar_distancia": True},
    "8 x Bandits": {"base_ref": "SB", "emoji": "🥷", "cor": 0, "titulo": "8 Bandits", "mostrar_distancia": True},
    "Volatile Leaper": {"base_ref": "P", "emoji": "🐸", "cor": 32768, "titulo": "Volatile Leaper", "mostrar_distancia": False}
}

def calcular_distancia_base(bx, by, base_sigla):
    if bx == "???" or by == "???":
        return "Localização desconhecida"
    
    x, y = int(bx), int(by)
    base_x, base_y = BASES.get(base_sigla, BASES['SB'])
    
    # Matemática Correta: Boss - Base
    diff_x = x - base_x
    diff_y = y - base_y
    
    # Eixo X: Positivo é Direita (R), Negativo é Esquerda (L)
    dir_x = f"{abs(diff_x)}R" if diff_x > 0 else (f"{abs(diff_x)}L" if diff_x < 0 else "")
    # Eixo Y: Positivo é Baixo (D), Negativo é Cima (U)
    dir_y = f"{abs(diff_y)}D" if diff_y > 0 else (f"{abs(diff_y)}U" if diff_y < 0 else "")
    
    posicao = f"{dir_x}{dir_y}".strip()
    return f"{posicao} de {base_sigla}" if posicao else "No mesmo bloco"

def extrair_dados_alvo(dados, nome_alvo):
    # 1. Busca Estruturada (Garante que a coordenada pertence EXATAMENTE a este boss)
    if isinstance(dados, dict):
        for k, v in dados.items():
            # Verifica se a chave é uma coordenada (ex: "1054_995")
            if re.match(r'^\d{3,4}[x_]\d{3,4}$', str(k)):
                if nome_alvo in str(v):
                    partes = str(k).replace('_', 'x').split('x')
                    trecho = str(v).lower()
                    esta_ativo = not ('green' in trecho or 'expired' in trecho or '"active":false' in trecho.replace(" ", ""))
                    return partes[0], partes[1], esta_ativo
                    
        # Se os blocos estiverem dentro de um sub-dicionário
        for k, v in dados.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if re.match(r'^\d{3,4}[x_]\d{3,4}$', str(sub_k)):
                        if nome_alvo in str(sub_v):
                            partes = str(sub_k).replace('_', 'x').split('x')
                            trecho = str(sub_v).lower()
                            esta_ativo = not ('green' in trecho or 'expired' in trecho or '"active":false' in trecho.replace(" ", ""))
                            return partes[0], partes[1], esta_ativo

    # 2. Fallback (Caso de emergência se a estrutura do site mudar)
    json_str = json.dumps(dados)
    idx = json_str.find(nome_alvo)
    if idx != -1:
        trecho_total = json_str[max(0, idx-150):min(len(json_str), idx+150)]
        esta_ativo = not ('green' in trecho_total.lower() or 'expired' in trecho_total.lower() or '"active":false' in trecho_total.replace(" ", ""))
        
        texto_antes = json_str[:idx]
        chaves_coords = re.findall(r'"(\d{3,4})[x_](\d{3,4})"', texto_antes)
        if chaves_coords:
            return chaves_coords[-1][0], chaves_coords[-1][1], esta_ativo

    return "???", "???", False

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
            
            if not esta_ativo or x == "???":
                continue

            distancia_ref = calcular_distancia_base(x, y, config['base_ref'])
            loc_atual = f"{x}x{y}"

            if not estado[nome_alvo]["alertado_inicio"] or estado[nome_alvo]["ultima_loc"] != loc_atual:
                enviar_alerta(nome_alvo, x, y, distancia_ref, config, tipo="inicio")
                estado[nome_alvo]["alertado_inicio"] = True
                estado[nome_alvo]["alertado_1h"] = False
                estado[nome_alvo]["tempo_inicio"] = agora
                estado[nome_alvo]["ultima_loc"] = loc_atual
                estado_modificado = True

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
    acao = "Apareceuuuu!" if tipo == "inicio" else "continua ativo! (1 Hora decorrida)"
    titulo = f"{config['titulo']} {acao}"
    
    if config['mostrar_distancia']:
        texto_area = f"Área: {x}x{y} ({distancia_str})"
        desc_alerta = f"Localização relativa: **{distancia_str}**\nClique no link acima para abrir o mapa interativo."
    else:
        texto_area = f"Área: {x}x{y}"
        desc_alerta = "Clique no link acima para abrir o mapa interativo."
    
    payload = {
        "content": f"@everyone {titulo} {config['emoji']}\nhttps://www.dfprofiler.com/bossmap\n{texto_area}",
        "embeds": [{
            "title": "Bossmap - Profiler",
            "description": desc_alerta,
            "color": config['cor'] if tipo == "inicio" else 16744192
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == '__main__':
    verificar_e_notificar()
