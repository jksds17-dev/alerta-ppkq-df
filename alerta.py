import requests
import time
import json
import re

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'

def extrair_coordenadas(dados):
    # Converte os dados num formato de texto bruto para inspeção profunda
    json_str = json.dumps(dados)
    
    # Encontra a posição exata da Pumpkin Queen no texto
    idx = json_str.find('Pumpkin Queen')
    
    # Salva o pedaço de texto em redor (para descobrirmos a estrutura caso falhe)
    debug_texto = json_str[max(0, idx-150):min(len(json_str), idx+150)]
    print(f"\n--- DEBUG JSON ---\n{debug_texto}\n------------------\n")

    # Estratégia 1: O DF Profiler costuma colocar a coordenada como o nome do "bloco" antes do boss (ex: "1050_986": { ... "Pumpkin Queen" })
    texto_antes = json_str[0:idx]
    chaves_coords = re.findall(r'"(\d{3,4})[x_](\d{3,4})"', texto_antes)
    if chaves_coords:
        # Pega a última coordenada encontrada antes do nome do boss (garante ser a dela)
        return chaves_coords[-1][0], chaves_coords[-1][1]
        
    # Estratégia 2: Procura pelo padrão clássico de variáveis ("x": 1050, "y": 986)
    padrao_xy = re.search(r'"x"\s*:\s*"?(\d{3,4})"?,?\s*"y"\s*:\s*"?(\d{3,4})"?', debug_texto)
    if padrao_xy:
        return padrao_xy.group(1), padrao_xy.group(2)

    return "???", "???"

def verificar_e_notificar():
    timestamp = int(time.time() * 1000)
    url = f"https://www.dfprofiler.com/bossmap/json/?_={timestamp}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dfprofiler.com/bossmap',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            if 'Pumpkin Queen' in str(dados):
                x, y = extrair_coordenadas(dados)
                print(f"🎃 Coordenadas extraídas: x{x}, y{y}")
                enviar_alerta(x, y)
            else:
                print("❌ A Pumpkin Queen NÃO está presente nos dados retornados.")
        else:
            print(f"Erro HTTP {resposta.status_code}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

def enviar_alerta(x, y):
    map_image_url = f"https://deadfrontier.info/w/map/images/Fairview_{x}x{y}.png" if x != "???" else ""
    
    embed_obj = {
        "title": "Bossmap - Profiler",
        "description": "The Dead Frontier Profiler Bossmap for finding zombie bosses.",
        "color": 16711680
    }
    
    if map_image_url:
        embed_obj["image"] = {"url": map_image_url}

    payload = {
        "content": f"@everyone A Rainha das Aboborinhas Apareceuuuu! 🎃👑\nhttps://www.dfprofiler.com/bossmap\nÁrea: {x} x {y}",
        "embeds": [embed_obj]
    }
    
    res = requests.post(WEBHOOK_URL, json=payload)
    print(f"Status do envio para o Discord: {res.status_code}")

if __name__ == '__main__':
    verificar_e_notificar()
