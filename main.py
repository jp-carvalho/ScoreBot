import discord
from discord import app_commands
from discord.ext import commands
import os

# 🔑 Pegando o token do secrets do Railway
TOKEN = os.getenv("DISCORD_TOKEN")

# 🏠 Coloque aqui o ID do seu servidor (guild)
GUILD_ID = 709705286083936256  # <-- troque pelo ID do seu servidor!

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Evento quando o bot está pronto
@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ {len(synced)} comandos Slash sincronizados com o servidor.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# Slash Command simples de teste
@bot.tree.command(name="registrar", description="Registrar uma partida", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    jogo="Nome do jogo",
    jogador1="Jogador em 1º lugar",
    jogador2="Jogador em 2º lugar",
    jogador3="Jogador em 3º lugar",
    jogador4="Jogador em último lugar",
    duracao="Duração da partida (ex: 2h)"
)
async def registrar(interaction: discord.Interaction, jogo: str, jogador1: str, jogador2: str, jogador3: str, jogador4: str, duracao: str):
    await interaction.response.send_message(
        f"🏆 **{jogo}** registrado!\n"
        f"🥇 {jogador1} (+3 pts)\n"
        f"🥈 {jogador2} (+1 pt)\n"
        f"👤 {jogador3} (0 pts)\n"
        f"💀 {jogador4} (-1 pt)\n"
        f"⏱️ Duração: {duracao}"
    )

# Inicia o bot
bot.run(TOKEN)
