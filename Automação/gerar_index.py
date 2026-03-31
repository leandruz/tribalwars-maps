import os
import json
from datetime import datetime

# Script para gerar o índice da galeria (gallery.json)
# Varre a pasta Resultados e organiza os mapas gerados por mundo e categoria.

BASE_DIR = "Resultados"
OUTPUT_FILE = os.path.join(BASE_DIR, "gallery.json")

def scan_results():
    gallery_data = {
        "last_update": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "worlds": {}
    }
    
    if not os.path.exists(BASE_DIR):
        print(f"Erro: Pasta {BASE_DIR} não encontrada.")
        return gallery_data

    # Listar mundos (pastas dentro de Resultados)
    worlds = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d)) and d.startswith("br")]
    worlds.sort(reverse=True) # Mostrar mundos mais recentes primeiro

    for world in worlds:
        world_path = os.path.join(BASE_DIR, world)
        world_info = {
            "name": world.upper(),
            "players": [],
            "tribes": []
        }
        
        # Escanear Players
        player_path = os.path.join(world_path, "Players")
        if os.path.exists(player_path):
            files = [f for f in os.listdir(player_path) if f.endswith(".png")]
            files.sort()
            for f in files:
                world_info["players"].append({
                    "title": parse_title(f),
                    "path": f"{BASE_DIR}/{world}/Players/{f}"
                })
        
        # Escanear Tribes
        tribe_path = os.path.join(world_path, "Tribes")
        if os.path.exists(tribe_path):
            files = [f for f in os.listdir(tribe_path) if f.endswith(".png")]
            files.sort()
            for f in files:
                world_info["tribes"].append({
                    "title": parse_title(f),
                    "path": f"{BASE_DIR}/{world}/Tribes/{f}"
                })
        
        if world_info["players"] or world_info["tribes"]:
            gallery_data["worlds"][world] = world_info

    return gallery_data

def parse_title(filename):
    # Traduzir nomes de arquivos em títulos amigáveis
    if "oda" in filename: return "Ranking ODA"
    if "odd" in filename: return "Ranking ODD"
    if "ods" in filename: return "Ranking ODS"
    if "xgoal" in filename: return "Média de Noblagens"
    if "dominancia" in filename: return "Dominância K"
    if "conquistas" in filename: return "Conquistas (24h)"
    if "points" in filename or "jogadores" in filename or "familias" in filename:
        return "Ranking Pontos"
    return filename

def main():
    print("Iniciando escaneamento de resultados para a galeria...")
    data = scan_results()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Sucesso! {OUTPUT_FILE} gerado com {len(data['worlds'])} mundos.")

if __name__ == "__main__":
    main()
