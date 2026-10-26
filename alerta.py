import requests
import time
import re

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'

def extrair_coordenadas(dados):
    # 1. Procura ocorrências de 'Pumpkin Queen' na estrutura do dicionário
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if 'Pumpkin Queen' in str(valor) or 'Pumpkin Queen' in str(chave):
                # Tenta extrair coordenadas no formato "1050x986", "1050_986", "1050, 986" da chave
                match_k = re.search(r'(\d{3,4})[x_,\s\-]+(\d{3,4})', str(chave))
                if match_k:
                    return match_k.group(1), match_k.group(2)
                
                # Tenta extrair se o valor for um dicionário com chaves x e y
                if isinstance(valor, dict):
                    x = str(valor.get('x', valor.get('coord_x', valor.get('posX', ''))))
                    y = str(valor.get('y', valor.get('coord_y', valor.get('posY', ''))))
                    if x.isdigit() and y.isdigit():
                        return x, y
                    
                    for sub_v in valor.values():
                        match_sub = re.search(r'(\d{3,4})[x_,\s\-]+(\d{3,4})', str(sub_v))
                        if match_sub:
                            return match_sub.group(1), match_sub.group(2)

                match_v = re.search(r'(\d{3,4})[x_,\s\-]+(\d{3,4})', str(valor))
                if match_v:
                    return match_v.group(1), match_v.group(2)

    # 2. Busca por proximidade no texto bruto do JSON
    json_str = str(dados)
    idx = json_str.find('Pumpkin Queen')
    if idx != -1:
        trecho = json_str[max(0, idx-200): min(len(json_str), idx+200)]
        
        match_xy = re.search(r'"x"\s*:\s*"?(\d{3,4})"?,?\s*"y"\s*:\s*"?(\d{3,4})"?', trecho)
        if match_xy:
            return match_xy.group(1), match_xy.group(2)

        matches = re.findall(r'(\d{3,4})[x_,\s\-]+(\d{3,4})', trecho)
        if matches:
            return matches[0][0], matches[0][1]

    return "???", "???"

def verificar_e_notificar():
    timestamp = int(time.time() * 1000)
    url = f"https://www.dfprofiler.com/bossmap/json/?_={timestamp}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dfprofiler.com/bossmap',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    try:
        resposta = requests.get(url, headers=headers, timeout=10)
        print(f"Status da API: {resposta.status_code}")
        
        if resposta.status_code == 200:
            dados = resposta.json()
            if 'Pumpkin Queen' in str(dados):
                x, y = extrair_coordenadas(dados)
                print(f"🎃 Pumpkin Queen ENCONTRADA! Localização: x{x}, y{y}")
                enviar_alerta(x, y)
            else:
                print("❌ Pumpkin Queen não encontrada no JSON.")
    except Exception as e:
        print(f"Erro na requisição: {e}")

def enviar_alerta(x, y):
    # Se capturar as coordenadas corretamente, adiciona a imagem do quadrante do mapa
    map_image_url = f"https://deadfrontier.info/w/map/images/Fairview_{x}x{y}.png" if x != "???" else ""
    
    embed_obj = {
        "title": "Bossmap - Profiler",
        "description": "The Dead Frontier Profiler Bossmap for finding zombie bosses.",
        "color": 16711680
    }
    
    if map_image_url:
        embed_obj["image"] = {"url": map_image_url}

    payload = {
        "content": f"@everyone A Rainha das Aboborinhas Apareceuuuu! 🎃👑\nhttps://www.dfprofiler.com/bossmap\nÁrea: x{x}, y{y}",
        "embeds": [embed_obj]
    }
    
    res = requests.post(WEBHOOK_URL, json=payload)
    print(f"Status do envio para o Discord: {res.status_code}")

if __name__ == '__main__':
    verificar_e_notificar()
