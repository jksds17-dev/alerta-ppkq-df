import requests
import json
import os

WEBHOOK_URL = 'https://discord.com/api/webhooks/1564227542754263131/Z0tmoKFVN7JHaidxn0SJLv09q3fTPiNbcbC8VRQHga1ul2mhLgPEJfZmAyl_592wDn8T'
DF_API_URL = 'https://www.dfprofiler.com/bossmap/json/'
ESTADO_FILE = 'ultimo_alerta.json'

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

def ja_notificado():
    return os.path.exists(ESTADO_FILE)

def registar_notificacao():
    with open(ESTADO_FILE, 'w') as f:
        f.write('notificado')

def verificar_e_notificar():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resposta = requests.get(DF_API_URL, headers=headers)
        if resposta.status_code != 200:
            print(f"Erro HTTP {resposta.status_code}")
            return
            
        dados = resposta.json()
        if 'Pumpkin Queen' in str(dados):
            if ja_notificado():
                print("Pumpkin Queen ativa, mas já foi notificada anteriormente.")
                return

            x, y = extrair_coordenadas(dados)
            print(f"🎃 Boss encontrado na localização: x{x}, y{y}")
            enviar_alerta(x, y)
            registar_notificacao()
        else:
            print("Pumpkin Queen não encontrada no mapa.")
            if os.path.exists(ESTADO_FILE):
                os.remove(ESTADO_FILE) # Reseta o estado quando o boss desaparecer
    except Exception as e:
        print(f"Erro na verificação: {e}")

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
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == '__main__':
    verificar_e_notificar()
