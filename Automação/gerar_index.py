import os
import json
from datetime import datetime

# Script para gerar o índice da galeria (gallery.json) com suporte multi-servidor
BASE_DIR = "Resultados"
OUTPUT_FILE = os.path.join(BASE_DIR, "gallery.json")

def scan_results():
    gallery_data = {
        "last_update": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "servers": {}
    }
    
    if not os.path.exists(BASE_DIR):
        print(f"Erro: Pasta {BASE_DIR} não encontrada.")
        return gallery_data

    # Listar servidores (.BR, .NET, .PT, .DS)
    servers = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d)) and d.startswith(".")]
    servers.sort()

    for server in servers:
        server_path = os.path.join(BASE_DIR, server)
        gallery_data["servers"][server] = {}
        
        # Listar mundos dentro do servidor
        worlds = [d for d in os.listdir(server_path) if os.path.isdir(os.path.join(server_path, d))]
        # Sort customizado para mundos (br141, br140...)
        worlds.sort(key=lambda x: str(x), reverse=True)

        for world in worlds:
            world_path = os.path.join(server_path, world)
            world_info = {
                "name": world.upper(),
                "players": [],
                "tribes": []
            }
            
            # Escanear Players e Tribes
            for cat in ["Players", "Tribes"]:
                cat_path = os.path.join(world_path, cat)
                if os.path.exists(cat_path):
                    files = [f for f in os.listdir(cat_path) if f.endswith(".png")]
                    files.sort()
                    for f in files:
                        world_info[cat.lower()].append({
                            "title": parse_title(f),
                            "path": f"Resultados/{server}/{world}/{cat}/{f}"
                        })
            
            if world_info["players"] or world_info["tribes"]:
                gallery_data["servers"][server][world] = world_info

    return gallery_data

def parse_title(filename):
    f = filename.lower()
    if "oda" in f: return "Ranking ODA"
    if "odd" in f: return "Ranking ODD"
    if "ods" in f: return "Ranking ODS"
    if "xgoal" in f: return "Média de Noblagens"
    if "dominancia" in f: return "Dominância K"
    if "conquistas" in f: return "Conquistas (24h)"
    if "conquest_hotspot" in f: return "Análise Tática (Dinâmica)"
    if "points" in f or "jogadores" in f or "familias" in f:
        return "Ranking Pontos"
    return filename

def main():
    print("Iniciando escaneamento de resultados multi-servidor...")
    data = scan_results()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    serv_count = len(data['servers'])
    print(f"Sucesso! {OUTPUT_FILE} gerado com {serv_count} servidores.")

if __name__ == "__main__":
    main()
