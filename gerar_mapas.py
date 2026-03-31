# Autor: Leandro Beraldo (Leandruz)
# GitHub: https://github.com/Leandruz/TribalWars-Maps

import os
import json
import time
from Automação.map_core import generate_map

# Carregar Mundos do Config
CONFIG_PATH = os.path.join("Automação", "config.json")
with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

MUNDOS = CONFIG["worlds"]
PASTA_RAIZ = "Resultados"

def main():
    print(f"=== [ SISTEMA CORE V2 ] Iniciando Geração ({len(MUNDOS)} mundos) ===\n")
    
    for mundo in MUNDOS:
        print(f"\n>>>> MUNDO: {mundo.upper()} <<<<")
        
        # 1. Mapas de Tribo (3 ranking + Dominância + Conquistas = 5)
        for metric in ["points", "oda", "odd"]:
            path = os.path.join(PASTA_RAIZ, mundo, "Tribes")
            generate_map(mundo, path, mode='ranking', entity='tribe', metric=metric)
            time.sleep(0.5)

        # 2. Mapas de Player (4 ranking + Dominância = 5)
        for metric in ["points", "oda", "odd", "ods"]:
            path = os.path.join(PASTA_RAIZ, mundo, "Players")
            generate_map(mundo, path, mode='ranking', entity='player', metric=metric)
            time.sleep(0.5)

        # 3. Dominância e Conquistas
        path_t = os.path.join(PASTA_RAIZ, mundo, "Tribes")
        path_p = os.path.join(PASTA_RAIZ, mundo, "Players")
        
        generate_map(mundo, path_t, mode='dominance_k', entity='tribe')      # mapa_top15_dominancia_K
        generate_map(mundo, path_p, mode='dominance_k', entity='player')     # mapa_top15_dominancia_jogadores_K
        generate_map(mundo, path_t, mode='conquests')                        # mapa_top15_conquistas

        print(f" [OK] {mundo} finalizado com sucesso!")
        time.sleep(1)

    print("\n=== OPERAÇÃO CONCLUÍDA: Todos os mapas foram gerados na pasta /Resultados/ ===")

if __name__ == "__main__":
    main()
