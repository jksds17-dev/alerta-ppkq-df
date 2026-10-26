import requests
import time
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
DF_API_URL = 'https://www.dfprofiler.com/bossmap/json/'

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
    try:
        # Força o bypass do cache enviando o timestamp atual
        timestamp = int(time.time() * 1000)
        url_com_timestamp = f"{DF_API_URL}?_={timestamp}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        resposta = requests.get(url_com_timestamp, headers=headers)
        print(f"Status HTTP recebido: {resposta.status_code}")
        
        if resposta.status_code != 200:
            print("Não foi possível carregar os dados da API do DF Profiler.")
            return
            
        dados = resposta.json()
        if 'Pumpkin Queen' in str(dados):
            x, y = extrair_coordenadas(dados)
            print(f"🎃 Pumpkin Queen ENCONTRADA! Localização: x{x}, y{y}")
            enviar_alerta(x, y)
        else:
            print("❌ A Pumpkin Queen NÃO está ativa no mapa neste momento.")
    except Exception as e:
        print(f"Erro durante a verificação: {e}")

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
    print(f"Envio para o Discord concluído com status: {res.status_code}")

if __name__ == '__main__':
    verificar_e_notificar()
