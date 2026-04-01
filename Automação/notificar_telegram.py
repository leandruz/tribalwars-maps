import os
import requests

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Aviso: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não encontrados nos Secrets.")
        return

    # Link da Galeria no GitHub Pages
    repo = os.environ.get("GITHUB_REPOSITORY", "Leandruz/TribalWars-Maps")
    try:
        user, repo_name = repo.split('/')
        gallery_url = f"https://{user.lower()}.github.io/{repo_name}/"
    except:
        gallery_url = "https://leandruz.github.io/TribalWars-Maps/"
    
    msg = f"🗺️ *Mapas Diários Atualizados!*\n\nConfira todos os mapas e rankings mundiais na sua galeria:\n👉 {gallery_url}"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("Sucesso: Telegram notificado!")
        else:
            print(f"Erro ao enviar: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Erro na conexão com Telegram: {e}")

if __name__ == "__main__":
    main()
