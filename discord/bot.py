import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import io
import aiohttp
from datetime import datetime, date
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
    # Players
    "dominancia_k_jogadores": ("Players", "mapa_top15_dominancia_jogadores_K_{mundo}.png", "Top 15 Dominância por K (Jogadores)"),
    "top15_jogadores": ("Players", "mapa_top15_jogadores_{mundo}.png", "Top 15 Jogadores"),
    "top15_oda_jogadores": ("Players", "mapa_top15_oda_jogadores_{mundo}.png", "Top 15 ODA Jogadores"),
    "top15_odd_jogadores": ("Players", "mapa_top15_odd_jogadores_{mundo}.png", "Top 15 ODD Jogadores"),
    "top15_ods_jogadores": ("Players", "mapa_top15_ods_jogadores_{mundo}.png", "Top 15 ODS Jogadores"),
    "top15_xgoal_jogadores": ("Players", "mapa_top15_xgoal_jogadores_{mundo}.png", "Top 15 Fast Nobles jogadores"),
    
    # Tribes
    "hotspot": ("Tribes", "mapa_conquest_hotspot_{mundo}.png", "Conquest_Hotspot"),
    "top15_conquistas": ("Tribes", "mapa_top15_conquistas_{mundo}.png", "Top 15 Conquistas"),
    "dominancia_k": ("Tribes", "mapa_top15_dominancia_K_{mundo}.png", "Top 15 Dominância por K"),
    "top15_tribos": ("Tribes", "mapa_top15_tribos_{mundo}.png", "Top 15 Tribos"),
    "top15_oda_tribos": ("Tribes", "mapa_top15_oda_tribos_{mundo}.png", "Top 15 ODA Tribos"),
    "top15_odd_tribos": ("Tribes", "mapa_top15_odd_tribos_{mundo}.png", "Top 15 ODD Tribos")
}

def format_mundo(servidor: str, mundo: str) -> str:
    mundo = mundo.lower()
    if mundo.isdigit():
        prefix_map = {
            ".BR": "br",
            ".PT": "pt",
            ".NET": "en",
            ".DS": "de"
        }
        prefix = prefix_map.get(servidor, "")
        return f"{prefix}{mundo}"
    return mundo

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
    def __init__(self, server, mundo, cargo_id=None):
        self.server_escolhido = server
        self.mundo_escolhido = mundo
        self.cargo_id = cargo_id
        
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
            "mapas": self.values,
            "cargo_id": self.cargo_id
        }
        save_config(config)
        
        nomes = [MAP_TYPES[v][2] for v in self.values]
        
        await interaction.response.edit_message(content=f"✅ Configuração salva para o mundo **{self.mundo_escolhido.upper()}** ({self.server_escolhido})!\nMapas selecionados:\n- " + "\n- ".join(nomes), view=None)

class MapSetupView(discord.ui.View):
    def __init__(self, server, mundo, cargo_id=None):
        super().__init__()
        self.add_item(MapSelect(server, mundo, cargo_id))

# --- EVENTOS ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} online!')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comando(s).")
        print(f"Horário atual do bot: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
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
@app_commands.describe(servidor="Servidor (Ex: .BR, .PT)", mundo="Mundo (Ex: br140)", cargo_notificacao="Cargo para mencionar (Opcional)")
@app_commands.default_permissions(manage_channels=True)
@app_commands.choices(servidor=[
    app_commands.Choice(name="Brasil (.BR)", value=".BR"),
    app_commands.Choice(name="Portugal (.PT)", value=".PT"),
    app_commands.Choice(name="Internacional (.NET)", value=".NET"),
    app_commands.Choice(name="Alemanha (.DS)", value=".DS")
])
async def setup_diario(interaction: discord.Interaction, servidor: app_commands.Choice[str], mundo: str, cargo_notificacao: discord.Role = None):
    if interaction.user.guild_permissions and not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels):
        await interaction.response.send_message("Permissão de 'Administrador' ou 'Gerenciar Canais' necessária.", ephemeral=True)
        return
        
    mundo_formatado = format_mundo(servidor.value, mundo)
    cargo_id = cargo_notificacao.id if cargo_notificacao else None
    view = MapSetupView(servidor.value, mundo_formatado, cargo_id)
    await interaction.response.send_message(f"Configurando o mundo **{mundo_formatado.upper()}** ({servidor.value}). Selecione os mapas abaixo:", view=view, ephemeral=True)

async def _send_maps(channel_or_interaction, servidor, mundo, requested_maps, ping_role_id=None):
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
        msg = f"😅 Poxa, parece que os mapas de **{mundo.upper()}** ({servidor}) ainda não saíram do forno hoje! Tentarei enviá-los amanhã, ou você pode usar o comando `/force_update` mais tarde."
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
    
    content_msg = f"<@&{ping_role_id}>" if ping_role_id else None
    
    # Discord has a limit of 10 files per message. We need to split if there are more.
    chunk_size = 10
    file_chunks = [valid_files[i:i + chunk_size] for i in range(0, len(valid_files), chunk_size)]
    
    for idx, chunk in enumerate(file_chunks):
        # Only send the content (ping) and embed on the first message
        current_content = content_msg if idx == 0 else None
        current_embed = embed if idx == 0 else None
        
        try:
            if is_interaction:
                await channel_or_interaction.followup.send(content=current_content, embed=current_embed, files=chunk)
            else:
                await channel_or_interaction.send(content=current_content, embed=current_embed, files=chunk)
        except Exception as e:
            print(f"Erro ao enviar mapas: {e}")
class PainelView(discord.ui.View):
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="Cancelar Envio Diário", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def cancelar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        ch_id = str(interaction.channel_id)
        if ch_id in config:
            del config[ch_id]
            save_config(config)
            await interaction.response.send_message("✅ Envio diário cancelado com sucesso para este canal.", ephemeral=True)
            button.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("Nenhuma configuração ativa encontrada.", ephemeral=True)

@bot.tree.command(name="painel", description="Mostra a configuração diária ativa neste canal e permite cancelá-la.")
@app_commands.default_permissions(manage_channels=True)
async def painel(interaction: discord.Interaction):
    config = load_config()
    ch_id = str(interaction.channel_id)
    if ch_id not in config:
        await interaction.response.send_message("Não há nenhum envio diário configurado para este canal. Use `/setup_diario` primeiro.", ephemeral=True)
        return
        
    cfg = config[ch_id]
    cargo_str = f"<@&{cfg['cargo_id']}>" if cfg.get("cargo_id") else "Nenhum"
    mapas_nomes = [MAP_TYPES[m][2] for m in cfg['mapas'] if m in MAP_TYPES]
    
    embed = discord.Embed(title="⚙️ Painel de Configuração Diária", color=discord.Color.blue())
    embed.add_field(name="Servidor / Mundo", value=f"{cfg['servidor']} / {cfg['mundo'].upper()}", inline=False)
    embed.add_field(name="Cargo Notificado", value=cargo_str, inline=False)
    embed.add_field(name="Mapas Diários", value="\n".join([f"• {m}" for m in mapas_nomes]), inline=False)
    embed.add_field(name="Canal ID", value=f"`{ch_id}`", inline=False)
    embed.add_field(name="Horário de Envio", value="Todos os dias às 10:00 (UTC)", inline=False)
    
    view = PainelView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="mapa", description="Pede um mapa específico do mundo escolhido.")
@app_commands.choices(servidor=[
    app_commands.Choice(name="Brasil (.BR)", value=".BR"),
    app_commands.Choice(name="Portugal (.PT)", value=".PT"),
    app_commands.Choice(name="Internacional (.NET)", value=".NET"),
    app_commands.Choice(name="Alemanha (.DS)", value=".DS")
])
@app_commands.choices(tipo_mapa=[app_commands.Choice(name=v[2], value=k) for k, v in list(MAP_TYPES.items())[:25]]) # Limite de 25 choices do Discord
async def pedir_mapa(interaction: discord.Interaction, servidor: app_commands.Choice[str], mundo: str, tipo_mapa: app_commands.Choice[str]):
    mundo_formatado = format_mundo(servidor.value, mundo)
    await _send_maps(interaction, servidor.value, mundo_formatado, [tipo_mapa.value])

@bot.tree.command(name="todos_mapas", description="Pede todos os mapas disponíveis do mundo escolhido.")
@app_commands.choices(servidor=[
    app_commands.Choice(name="Brasil (.BR)", value=".BR"),
    app_commands.Choice(name="Portugal (.PT)", value=".PT"),
    app_commands.Choice(name="Internacional (.NET)", value=".NET"),
    app_commands.Choice(name="Alemanha (.DS)", value=".DS")
])
async def todos_mapas(interaction: discord.Interaction, servidor: app_commands.Choice[str], mundo: str):
    mundo_formatado = format_mundo(servidor.value, mundo)
    await _send_maps(interaction, servidor.value, mundo_formatado, list(MAP_TYPES.keys()))

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
    await _send_maps(interaction, cfg["servidor"], cfg["mundo"], cfg["mapas"], cfg.get("cargo_id"))


# --- TASKS ---
last_sent_date = None

@tasks.loop(minutes=5)
async def daily_map_publisher():
    global last_sent_date
    now = datetime.now()
    
    # Postar todos os dias a partir das 10 da manhã
    # Se o bot cair e voltar às 11:00, ele ainda enviará os mapas que faltam de hoje.
    if now.hour >= 10 and last_sent_date != now.date():
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando tarefa de envio diário...")
        config = load_config()
        if not config:
            print("Nenhuma configuração encontrada em channels_config.json.")
            last_sent_date = now.date() # Marca como feito para não repetir o log
            return

        for channel_id_str, cfg in config.items():
            try:
                channel_id = int(channel_id_str)
                # Tenta pegar do cache
                channel = bot.get_channel(channel_id)
                
                # Se não estiver no cache, tenta buscar na API (importante para após reinicializações)
                if not channel:
                    try:
                        channel = await bot.fetch_channel(channel_id)
                        print(f"Canal {channel_id} recuperado via API (fetch).")
                    except Exception as e:
                        print(f"Erro ao buscar canal {channel_id_str} via API: {e}")
                        continue
                
                if channel:
                    channel_name = channel.name if hasattr(channel, 'name') else "N/A"
                    guild_name = channel.guild.name if hasattr(channel, 'guild') else "N/A"
                    print(f"Enviando mapas para {cfg['mundo']} no canal #{channel_name} (Servidor: {guild_name})...")
                    await _send_maps(channel, cfg["servidor"], cfg["mundo"], cfg["mapas"], cfg.get("cargo_id"))
                else:
                    print(f"Canal {channel_id_str} não encontrado.")
            except Exception as e:
                print(f"Erro ao processar canal {channel_id_str}: {e}")
        
        last_sent_date = now.date()
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Tarefa de envio diário concluída.")

if __name__ == "__main__":
    print("Iniciando Bot...")
    if not TOKEN or TOKEN == "INSIRA_SEU_TOKEN_AQUI":
        print("ERRO: O Token não foi encontrado no arquivo .env!")
    else:
        bot.run(TOKEN)
