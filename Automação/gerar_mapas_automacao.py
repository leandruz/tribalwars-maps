import os
import subprocess
import time

# === LISTA DE MUNDOS ALVOS ===
MUNDOS = ["br138", "br139", "br140", "br141"]

# Diretório base é a pasta pai deste arquivo (ou seja, a raiz do projeto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASTA_RAIZ = os.path.join(BASE_DIR, "Resultados")
PASTA_SCRIPTS = os.path.join(BASE_DIR, "Code TOP 15")

SCRIPTS = {
    "Tribes": [
        "Top 15 Tribe",
        "Top 15 Tribe - K",
        "Top 15 Tribe - Noble",
        "Top 15 Tribe - ODA",
        "Top 15 Tribe - ODD",
        "Top 15 Tribe - ODS"
    ],
    "Players": [
        "Top 15 Players",
        "Top 15 Players - K",
        "Top 15 Players - ODA",
        "Top 15 Players - ODD",
        "Top 15 Players - ODS"
    ]
}

def main():
    print(f"=== Iniciando Gerador de Mapas ({len(MUNDOS)} mundos listados) ===\n")
    
    # Criar pasta raiz dos resultados se não existir
    if not os.path.exists(PASTA_RAIZ):
        os.makedirs(PASTA_RAIZ)
        
    for mundo in MUNDOS:
        print(f">>>> Processando Mundo: {mundo} <<<<")
        
        for categoria, lista_scripts in SCRIPTS.items():
            pasta_destino = os.path.join(PASTA_RAIZ, mundo, categoria)
            os.makedirs(pasta_destino, exist_ok=True)
            
            for script_name in lista_scripts:
                # O caminho do script sem a extensão (visto que o nome real deles é igualzinho o dicionário)
                script_path = os.path.abspath(os.path.join(PASTA_SCRIPTS, script_name))
                pasta_destino_abs = os.path.abspath(pasta_destino)
                
                print(f" -> Desenhando: {script_name}")
                
                try:
                    # Executamos o script repassando as variaveis de mundo
                    # Estamos utilizando o interpretador python do seu ambiente virtual se existir
                    python_exec = os.path.abspath(os.path.join(BASE_DIR, ".venv", "bin", "python"))
                    if not os.path.exists(python_exec):
                        python_exec = "python3" # Servirá de fallback caso venv não seja encontrado pelo sistema local
                        
                    resultado = subprocess.run(
                        [python_exec, script_path, mundo, pasta_destino_abs],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Se algum script disser que "Erro ao baixar", mostra para o usuário:
                    if "Erro ao baixar" in resultado.stdout:
                         print(f"    [AVISO] {mundo} pode estar fechado/inacessível ou URL de dados invalida.")
                         
                except subprocess.CalledProcessError as e:
                    print(f"    [ERRO] O script falhou (Fatal). Detalhes: {e}")
                    
                # A API de arquivos txt do .net da inno não gosta de 8 requests simultaneos de mapa por segundo num for loop pesado.
                # Para evitar um timeout preventivo (CloudFlare), vamos botar 1 segundinho apenas de delay!
                time.sleep(1)
                
        print(f" [OK] Imagens do {mundo} transferidas com Sucesso!\n")
                
    print("=== FINALIZADO: Operação concluída em todos os Mundos! ===")
    print(f"Caminho alvo das pastas catalogadas: {os.path.abspath(PASTA_RAIZ)}")

if __name__ == "__main__":
    main()
