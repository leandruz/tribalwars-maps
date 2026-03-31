# 🗺️ TribalWars Maps Automation

![TribalWars](https://img.shields.io/badge/TribalWars-BR-orange)
![Automação](https://img.shields.io/badge/Automação-Daily-blue)
![Licença](https://img.shields.io/badge/Licença-MIT-green)

Sistema automático de geração de infográficos de guerra para o jogo TribalWars (Servidores Brasileiros).

## 🚀 Como Funciona?

O projeto utiliza a API pública oficial da InnoGames para capturar dados em tempo real (aldeias, jogadores, tribos e ODs) e gera mapas de alta definição com as seguintes métricas:

- **Top 15 Famílias/Tribos**: Rankings por Pontos, ODA, ODD, ODS e Dominância por Continente (K).
- **Top 15 Jogadores**: Rankings por Pontos, ODA, ODD, ODS e Dominância por Continente (K).
- **Top 15 Noblagens**: Rastreamento de conquistas do dia.

## 🕒 Atualização Diária

Utilizamos o **GitHub Actions** para rodar todos os scripts automaticamente todos os dias às **01:00 (Horário de Brasília)**. As imagens na pasta `Resultados/` são atualizadas e podem ser linkadas diretamente em fóruns e mensagens coletivas de tribos.

## 📂 Estrutura do Projeto

- `/Automação`: Contém o script orquestrador e dependências.
- `/Code TOP 15`: Scripts individuais em Python para cada tipo de mapa.
- `/Resultados`: Onde as imagens finais estão hospedadas (BR138, BR139, BR140, BR141).

## 🛠️ Como usar localmente

Caso queira rodar os mapas agora mesmo no seu computador:

1. Instale o Python 3.9+ 
2. Instale as dependências: `pip install -r Automação/requirements.txt`
3. Execute o script mestre: `python Automação/gerar_mapas_automacao.py`

## 👤 Autoria

Desenvolvido por **Leandro Beraldo (Leandruz)**.
GitHub: [https://github.com/Leandruz/TribalWars-Maps](https://github.com/Leandruz/TribalWars-Maps)

---
*Este projeto é de uso livre sob a Licença MIT. Sinta-se à vontade para contribuir ou usar os mapas em seus mundos!*
