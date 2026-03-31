# 🗺️ TribalWars Maps Automation

![TribalWars](https://img.shields.io/badge/TribalWars-BR-orange)
![Automação](https://img.shields.io/badge/Automação-Daily-blue)
![Licença](https://img.shields.io/badge/Licença-MIT-green)

Sistema automático de geração de infográficos de guerra para o jogo TribalWars (Servidor Brasil).

## 🚀 Como Funciona?

O projeto utiliza a API oficial da InnoGames para capturar dados em tempo real e gera mapas de alta definição:

- **Top 15 Famílias/Jogadores**: Rankings por Pontos, ODA, ODD, ODS e Dominância (K).
- **Relatório de Conquistas**: Rastreamento de noblagens das últimas 24h.

## 📂 Estrutura do Projeto (V2 Modular)

- **`gerar_mapas.py`**: Único arquivo necessário para gerar todos os 48 mapas de uma vez.
- **`Automação/map_core.py`**: O motor central de processamento e desenho.
- **`Automação/config.json`**: Configuração de mundos ativos e paleta de cores.
- **`assets/fonts/`**: Fontes locais (Arial) para funcionamento universal.
- **`Resultados/`**: Mapas PNG atualizados diariamente.

---

## 🛠️ Como Usar Localmente

1. Tenha o Python 3.9+ instalado.
2. Instale as dependências: `pip install -r Automação/requirements.txt`
3. Execute o gerador: `python gerar_mapas.py`

---

## 🤖 Automação (GitHub Actions)

Os mapas são atualizados automaticamente **todos os dias às 01:00 (Horário de Brasília)** via GitHub Actions. As imagens na pasta `Resultados/` podem ser linkadas diretamente em fóruns e mensagens coletivas.

## 👤 Autoria

Desenvolvido por **Leandro Beraldo (Leandruz)**.
GitHub: [https://github.com/Leandruz/TribalWars-Maps](https://github.com/Leandruz/TribalWars-Maps)

---
*Este projeto é de uso livre sob a Licença MIT.*
