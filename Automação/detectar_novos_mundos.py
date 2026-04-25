import requests
import re
import json
import os
from datetime import datetime

# Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "Automação", "config.json")
RESULTADOS_DIR = os.path.join(BASE_DIR, "Resultados")

MESES = {
    "jan.": "01", "fev.": "02", "mar.": "03", "abr.": "04",
    "mai.": "05", "jun.": "06", "jul.": "07", "ago.": "08",
    "set.": "09", "out.": "10", "nov.": "11", "dez.": "12"
}

def normalize_date(tw_date):
    # Formato: 22/abr./2026 (09:30)
    match = re.search(r"(\d{1,2})/(\w{3}\.)/(\d{4})", tw_date)
    if match:
        dia, mes_pt, ano = match.groups()
        mes = MESES.get(mes_pt.lower(), "01")
        return f"{ano}-{mes}-{dia.zfill(2)}"
    return None

def get_world_start_date(world_id):
    url = f"https://{world_id}.tribalwars.com.br/page/settings"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            pattern = r"<td>Início</td>\s*<td>(.*?)</td>"
            match = re.search(pattern, resp.text)
            if match:
                return normalize_date(match.group(1))
    except:
        pass
    return None

def check_new_worlds():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    br_worlds = set(config["servers"].get(".BR", []))
    
    # URL que lista mundos ativos (estatísticas)
    url = "https://www.tribalwars.com.br/page/settings"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return
        
        # Procura links como br142.tribalwars.com.br/page/stats
        found_worlds = set(re.findall(r"(br\d+)\.tribalwars\.com\.br", resp.text))
        
        new_worlds = found_worlds - br_worlds
        
        if not new_worlds:
            print("Nenhum mundo novo detectado.")
            return

        for mundo in sorted(list(new_worlds)):
            print(f">>> Novo mundo detectado: {mundo}")
            
            # 1. Pegar data
            start_date = get_world_start_date(mundo)
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
                print(f"      Aviso: Data não encontrada para {mundo}, usando hoje.")
            
            # 2. Atualizar Config
            config["servers"][".BR"].append(mundo)
            config["servers"][".BR"].sort()
            config["server_start_dates"][mundo] = start_date
            
            # 3. Criar Pastas
            pasta_mundo = os.path.join(RESULTADOS_DIR, ".BR", mundo)
            os.makedirs(os.path.join(pasta_mundo, "Players"), exist_ok=True)
            os.makedirs(os.path.join(pasta_mundo, "Tribes"), exist_ok=True)
            print(f"      Pastas criadas em {pasta_mundo}")

        # Salvar config
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("\nConfigurações atualizadas com sucesso!")
        
    except Exception as e:
        print(f"Erro ao verificar novos mundos: {e}")

if __name__ == "__main__":
    check_new_worlds()
