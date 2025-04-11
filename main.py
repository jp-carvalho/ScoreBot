import discord
from discord import app_commands
from discord.ext import commands
import os

# Seu token e ID do servidor
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=709705286083936256)  # substitua pelo ID do seu servidor

# Criação do bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Evento quando o bot está pronto
@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"✅ {len(synced)} comandos Slash sincronizados com o servidor.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# Comando Slash de exemplo
@bot.tree.command(name="ping", description="Responde com pong!", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=False)

bot.run(TOKEN)
