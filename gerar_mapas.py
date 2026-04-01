# Autor: Leandro Beraldo (Leandruz)
# GitHub: https://github.com/Leandruz/TribalWars-Maps

import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from Automação.map_core import generate_map, archive_daily_data

# Carregar Config
CONFIG_PATH = os.path.join("Automação", "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SERVERS = CONFIG["servers"]
PASTA_RAIZ = "Resultados"

def process_world(server, mundo):
    """Função para processar um único mundo (pode rodar em paralelo)"""
    try:
        print(f"\n>>>> [Início] {server} {mundo.upper()}")
        
        # 1. Mapas de Tribo (Points, ODA, ODD)
        for metric in ["points", "oda", "odd"]:
            generate_map(mundo, server, PASTA_RAIZ, mode='ranking', entity='tribe', metric=metric)

        # 2. Mapas de Player (Points, ODA, ODD, xGoal)
        for metric in ["points", "oda", "odd", "xgoal"]:
            generate_map(mundo, server, PASTA_RAIZ, mode='ranking', entity='player', metric=metric)

        # 3. Dominância e Conquistas
        generate_map(mundo, server, PASTA_RAIZ, mode='dominance_k', entity='tribe')
        generate_map(mundo, server, PASTA_RAIZ, mode='dominance_k', entity='player')
        generate_map(mundo, server, PASTA_RAIZ, mode='conquests')

        # 4. Arquivamento de Dados
        archive_daily_data(mundo, server, PASTA_RAIZ)

        print(f" [OK] {mundo} finalizado com sucesso!")
        return True
    except Exception as e:
        print(f" [ERRO] Falha ao processar {mundo}: {e}")
        return False

def main():
    total_mundos = sum(len(worlds) for worlds in SERVERS.values())
    print(f"=== [ SISTEMA CORE V2.2 ] Iniciando Geração paralela ({total_mundos} mundos) ===\n")
    
    # Criar lista de tarefas (flatten)
    tasks = []
    for server, mundos in SERVERS.items():
        for mundo in mundos:
            tasks.append((server, mundo))

    # Executar em paralelo (máximo de 4 workers para não sobrecarregar ou ser bloqueado)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_world, srv, m) for srv, m in tasks]
        
        # Aguarda todos terminarem
        results = [f.result() for f in futures]

    # 5. Atualizar o Índice da Galeria Web
    print("\n=== [ GALERIA ] Atualizando Índice Web... ===")
    from Automação.gerar_index import main as update_index
    update_index()

    # 6. Notificar Telegram
    print("\n=== [ NOTIFICAÇÃO ] Enviando aviso para o Telegram... ===")
    try:
        from Automação.notificar_telegram import main as notify
        notify()
    except Exception as e:
        print(f"Aviso: Telegram não notificado.")

    print(f"\n=== OPERAÇÃO CONCLUÍDA: {sum(results)}/{total_mundos} mundos processados! ===")

if __name__ == "__main__":
    main()
