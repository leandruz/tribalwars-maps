import requests
import re
import json
import os

# Caminho do config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

MESES = {
    "jan.": "01", "fev.": "02", "mar.": "03", "abr.": "04",
    "mai.": "05", "jun.": "06", "jul.": "07", "ago.": "08",
    "set.": "09", "out.": "10", "nov.": "11", "dez.": "12"
}

def normalize_date(tw_date):
    # Formato esperado: 08/jan./2025 (09:30)
    match = re.search(r"(\d{1,2})/(\w{3}\.)/(\d{4})", tw_date)
    if match:
        dia, mes_pt, ano = match.groups()
        mes = MESES.get(mes_pt.lower(), "01")
        # Garantir padding de 2 dígitos no dia
        dia_pad = dia.zfill(2)
        return f"{ano}-{mes}-{dia_pad}"
    return None

def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Erro: {CONFIG_PATH} não encontrado.")
        return

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    worlds = config.get("worlds", [])
    if "server_start_dates" not in config:
        config["server_start_dates"] = {}

    print(f"Iniciando atualização de datas para {len(worlds)} mundos...")

    for mundo in worlds:
        url = f"https://{mundo}.tribalwars.com.br/page/settings"
        print(f"[{mundo}] Acessando configurações...")
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                print(f"[{mundo}] Erro: Status {resp.status_code}")
                continue
            
            # Procura pela linha que contém "Início" e pega a célula seguinte
            # Estrutura típica: <td>Início</td><td>08/jan./2025 (09:30)</td>
            pattern = r"<td>Início</td>\s*<td>(.*?)</td>"
            match = re.search(pattern, resp.text)
            
            if match:
                raw_date = match.group(1)
                normalized = normalize_date(raw_date)
                if normalized:
                    config["server_start_dates"][mundo] = normalized
                    print(f"[{mundo}] Data: {normalized}")
                else:
                    print(f"[{mundo}] Falha ao normalizar data: {raw_date}")
            else:
                print(f"[{mundo}] Campo 'Início' não encontrado.")
        except Exception as e:
            print(f"[{mundo}] Erro de conexão: {e}")

    # Salva de volta no config.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    
    print("\nAtualização concluída com sucesso!")

if __name__ == "__main__":
    main()
