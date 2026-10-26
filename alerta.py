import requests
import time
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'

def extrair_coordenadas(dados):
    x, y = "???", "???"
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if 'Pumpkin Queen' in str(valor):
                if isinstance(valor, dict):
                    x = valor.get('x', valor.get('coord_x', x))
                    y = valor.get('y', valor.get('coord_y', y))
                if x == "???" or y == "???":
                    partes = chave.replace('_', 'x').split('x')
                    if len(partes) == 2 and partes[0].isdigit():
                        x, y = partes[0], partes[1]
                break
    elif isinstance(dados, list):
        for item in dados:
            if isinstance(item, dict) and 'Pumpkin Queen' in str(item):
                x = item.get('x', x)
                y = item.get('y', y)
                break
    return x, y

def verificar_e_notificar():
    timestamp = int(time.time() * 1000)
    
    # URLs para testar (com e sem barra final)
    urls_para_testar = [
        f"https://www.dfprofiler.com/bossmap/json/?_={timestamp}",
        f"https://www.dfprofiler.com/bossmap/json?_={timestamp}"
    ]
    
    # Cabeçalhos completos de um navegador real para evitar bloqueio 404 / 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dfprofiler.com/bossmap',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    resposta = None
    for url in urls_para_testar:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"Testando {url} -> Status {r.status_code}")
            if r.status_code == 200:
                resposta = r
                break
        except Exception as e:
            print(f"Falha na conexão com {url}: {e}")

    if not resposta or resposta.status_code != 200:
        print("❌ Não foi possível carregar os dados do JSON (servidor retornou erro).")
        return

    try:
        dados = resposta.json()
        if 'Pumpkin Queen' in str(dados):
            x, y = extrair_coordenadas(dados)
            print(f"🎃 Pumpkin Queen ENCONTRADA! Localização: x{x}, y{y}")
            enviar_alerta(x, y)
        else:
            print("❌ A Pumpkin Queen NÃO está presente nos dados retornados.")
    except Exception as e:
        print(f"Erro ao processar o JSON: {e}")

def enviar_alerta(x, y):
    map_image_url = f"https://deadfrontier.info/w/map/images/Fairview_{x}x{y}.png"
    payload = {
        "content": f"@everyone A Rainha das Aboborinhas Apareceuuuu! 🎃👑\nhttps://www.dfprofiler.com/bossmap\nÁrea: x{x}, y{y}",
        "embeds": [{
            "title": "Bossmap - Profiler",
            "description": "The Dead Frontier Profiler Bossmap for finding zombie bosses.",
            "color": 16711680,
            "image": {"url": map_image_url}
        }]
    }
    res = requests.post(WEBHOOK_URL, json=payload)
    print(f"Status do envio para o Discord: {res.status_code}")

if __name__ == '__main__':
    verificar_e_notificar()
