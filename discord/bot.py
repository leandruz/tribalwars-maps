import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import io
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=INTENTS)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "channels_config.json")
GITHUB_BASE_URL = "https://raw.githubusercontent.com/Leandruz/TribalWars-Maps/main/Resultados"

# Mapa de nomes amigáveis para caminhos de arquivos relativos ao mundo
MAP_TYPES = {
    "dominancia_k": ("Tribes", "mapa_top15_dominancia_K_{mundo}.png", "Dominância de Continente"),
    "hotspot": ("Tribes", "mapa_conquest_hotspot_{mundo}.png", "Hotspot de Conquistas"),
    "top15_jogadores": ("Players", "mapa_top15_jogadores_{mundo}.png", "Top 15 Jogadores (Pontos)"),
    "top15_oda_jogadores": ("Players", "mapa_top15_oda_jogadores_{mundo}.png", "Top 15 ODA Jogadores"),
    "top15_ods_jogadores": ("Players", "mapa_top15_ods_jogadores_{mundo}.png", "Top 15 ODS Jogadores"),
    "top15_odd_jogadores": ("Players", "mapa_top15_odd_jogadores_{mundo}.png", "Top 15 ODD Jogadores"),
    "top15_familias": ("Tribes", "mapa_top15_familias_{mundo}.png", "Top 15 Famílias (Pontos)"),
    "top15_oda_familias": ("Tribes", "mapa_top15_oda_familias_{mundo}.png", "Top 15 ODA Famílias"),
    "calor_combate": ("Tribes", "mapa_calor_combate_{mundo}.png", "Mapa de Calor (Combate)") # fallback / antigo
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def fetch_image(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.read()
            return data
        return None

# --- UI VIEWS ---
class MapSelect(discord.ui.Select):
    def __init__(self, server, mundo):
        self.server_escolhido = server
        self.mundo_escolhido = mundo
        
        options = []
        for key, value in MAP_TYPES.items():
            options.append(discord.SelectOption(label=value[2], value=key))
            
        super().__init__(placeholder="Selecione os mapas que deseja receber diariamente...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        channel_id = str(interaction.channel_id)
        
        config[channel_id] = {
            "servidor": self.server_escolhido,
            "mundo": self.mundo_escolhido,
            "mapas": self.values
        }
        save_config(config)
        
        nomes = [MAP_TYPES[v][2] for v in self.values]
        
        await interaction.response.edit_message(content=f"✅ Configuração salva para o mundo **{self.mundo_escolhido.upper()}** ({self.server_escolhido})!\nMapas selecionados:\n- " + "\n- ".join(nomes), view=None)

class MapSetupView(discord.ui.View):
    def __init__(self, server, mundo):
        super().__init__()
        self.add_item(MapSelect(server, mundo))

# --- EVENTOS ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} online!')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comando(s).")
    except Exception as e:
        print(e)
    if not daily_map_publisher.is_running():
        daily_map_publisher.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Se o bot foi mencionado
    if bot.user.mentioned_in(message):
        await message.channel.send("Olá! Sou o bot de Mapas do Tribal Wars.\n\nUse **`/setup_diario`** (apenas admins) para configurar o envio diário neste canal.\nUse **`/mapa`** ou **`/todos_mapas`** para pedir mapas sob demanda.")
        
    await bot.process_commands(message)


# --- COMANDOS ---
@bot.tree.command(name="setup_diario", description="Configura quais mapas receber diariamente neste canal.")
@app_commands.describe(servidor="Servidor (Ex: .BR, .PT)", mundo="Mundo (Ex: br140)")
@app_commands.default_permissions(manage_channels=True)
@app_commands.choices(servidor=[
    app_commands.Choice(name="Brasil (.BR)", value=".BR"),
    app_commands.Choice(name="Portugal (.PT)", value=".PT"),
    app_commands.Choice(name="Internacional (.NET)", value=".NET"),
    app_commands.Choice(name="Alemanha (.DS)", value=".DS")
])
async def setup_diario(interaction: discord.Interaction, servidor: app_commands.Choice[str], mundo: str):
    if interaction.user.guild_permissions and not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels):
        await interaction.response.send_message("Permissão de 'Administrador' ou 'Gerenciar Canais' necessária.", ephemeral=True)
        return
        
    view = MapSetupView(servidor.value, mundo.lower())
    await interaction.response.send_message(f"Configurando o mundo **{mundo.upper()}** ({servidor.value}). Selecione os mapas abaixo:", view=view, ephemeral=True)

async def _send_maps(channel_or_interaction, servidor, mundo, requested_maps):
    """Lógica unificada para baixar e enviar mapas para um canal ou interação"""
    is_interaction = isinstance(channel_or_interaction, discord.Interaction)
    
    if is_interaction:
        await channel_or_interaction.response.defer()
    
    valid_files = []
    
    async with aiohttp.ClientSession() as session:
        for map_key in requested_maps:
            if map_key not in MAP_TYPES: continue
            
            pasta, padrao_nome, nome_legivel = MAP_TYPES[map_key]
            nome_arquivo = padrao_nome.format(mundo=mundo)
            url = f"{GITHUB_BASE_URL}/{servidor}/{mundo}/{pasta}/{nome_arquivo}"
            
            data = await fetch_image(session, url)
            if data:
                # O nome do arquivo no anexo deve ser o mesmo
                valid_files.append(discord.File(io.BytesIO(data), filename=nome_arquivo))
            else:
                print(f"[Aviso] Mapa não encontrado no Git: {url}")

    if not valid_files:
        msg = f"⚠️ Nenhum dos mapas solicitados do mundo **{mundo.upper()}** ({servidor}) pôde ser baixado do GitHub. Talvez eles ainda não tenham sido gerados hoje."
        if is_interaction:
            await channel_or_interaction.followup.send(msg)
        else:
            await channel_or_interaction.send(msg)
        return

    embed = discord.Embed(
        title=f"🗺️ Mapas de Inteligência - {mundo.upper()} ({servidor})",
        description=f"Recuperados do GitHub em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
        color=discord.Color.dark_theme()
    )
    
    if is_interaction:
        await channel_or_interaction.followup.send(embed=embed, files=valid_files)
    else:
        await channel_or_interaction.send(embed=embed, files=valid_files)

@bot.tree.command(name="mapa", description="Pede um mapa específico do mundo escolhido.")
@app_commands.choices(servidor=[
    app_commands.Choice(name="Brasil (.BR)", value=".BR"),
    app_commands.Choice(name="Portugal (.PT)", value=".PT"),
    app_commands.Choice(name="Internacional (.NET)", value=".NET"),
    app_commands.Choice(name="Alemanha (.DS)", value=".DS")
])
@app_commands.choices(tipo_mapa=[app_commands.Choice(name=v[2], value=k) for k, v in list(MAP_TYPES.items())[:25]]) # Limite de 25 choices do Discord
async def pedir_mapa(interaction: discord.Interaction, servidor: app_commands.Choice[str], mundo: str, tipo_mapa: app_commands.Choice[str]):
    await _send_maps(interaction, servidor.value, mundo.lower(), [tipo_mapa.value])

@bot.tree.command(name="todos_mapas", description="Pede todos os mapas disponíveis do mundo escolhido.")
@app_commands.choices(servidor=[
    app_commands.Choice(name="Brasil (.BR)", value=".BR"),
    app_commands.Choice(name="Portugal (.PT)", value=".PT"),
    app_commands.Choice(name="Internacional (.NET)", value=".NET"),
    app_commands.Choice(name="Alemanha (.DS)", value=".DS")
])
async def todos_mapas(interaction: discord.Interaction, servidor: app_commands.Choice[str], mundo: str):
    await _send_maps(interaction, servidor.value, mundo.lower(), list(MAP_TYPES.keys()))

@bot.tree.command(name="force_update", description="Força a publicação imediata dos mapas diários configurados para este canal.")
@app_commands.default_permissions(manage_channels=True)
async def force_update(interaction: discord.Interaction):
    if interaction.user.guild_permissions and not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels):
        await interaction.response.send_message("Permissão negada.", ephemeral=True)
        return
    
    config = load_config()
    channel_id = str(interaction.channel_id)
    
    if channel_id not in config:
        await interaction.response.send_message("Nenhum mundo configurado para este canal. Use `/setup_diario` primeiro.", ephemeral=True)
        return
        
    cfg = config[channel_id]
    await _send_maps(interaction, cfg["servidor"], cfg["mundo"], cfg["mapas"])


# --- TASKS ---
@tasks.loop(hours=1)
async def daily_map_publisher():
    now = datetime.now()
    # Postar todos os dias às 10 da manhã (Ajuste conforme necessário)
    if now.hour == 10:
        config = load_config()
        for channel_id_str, cfg in config.items():
            try:
                channel_id = int(channel_id_str)
                channel = bot.get_channel(channel_id)
                if channel:
                    await _send_maps(channel, cfg["servidor"], cfg["mundo"], cfg["mapas"])
            except Exception as e:
                print(f"Erro ao enviar mapa para o canal {channel_id_str}: {e}")

if __name__ == "__main__":
    print("Iniciando Bot...")
    if not TOKEN or TOKEN == "INSIRA_SEU_TOKEN_AQUI":
        print("ERRO: O Token não foi encontrado no arquivo .env!")
    else:
        bot.run(TOKEN)
