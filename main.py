import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ----- CONFIGURAÇÕES -----
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=None, intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")  # Defina no ambiente (Railway)

# ----- JSON DE PONTUAÇÃO -----
ARQUIVO_PONTUACAO = "pontuacao.json"

def carregar_pontuacoes():
    if not os.path.exists(ARQUIVO_PONTUACAO):
        return {}
    with open(ARQUIVO_PONTUACAO, "r") as f:
        return json.load(f)

def salvar_pontuacoes(pontuacoes):
    with open(ARQUIVO_PONTUACAO, "w") as f:
        json.dump(pontuacoes, f, indent=4)

# ----- EVENTO DE BOT ONLINE E SYNC -----
@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    try:
        GUILD_ID = 709705286083936256  # <<< coloque aqui o ID do seu servidor
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Comandos Slash sincronizados manualmente: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# ----- COMANDO /registrar -----
@bot.tree.command(name="registrar", description="Registrar uma nova partida")
@app_commands.describe(
    jogo="Nome do jogo",
    jogadores="Menções dos jogadores em ordem (ex: @A @B @C ...)",
    duracao="Duração da partida (ex: 2h, 30min)"
)
async def registrar(interaction: discord.Interaction, jogo: str, jogadores: str, duracao: str):
    mencoes = jogadores.split()
    pontuacoes = carregar_pontuacoes()

    total_jogadores = len(mencoes)
    if total_jogadores < 3 or total_jogadores > 8:
        await interaction.response.send_message("❌ A partida deve ter entre 3 e 8 jogadores.", ephemeral=True)
        return

    resultado = []
    for i, mencao in enumerate(mencoes):
        pontos = 0
        if i == 0:
            pontos = 3
        elif i == 1:
            pontos = 1
        elif i == total_jogadores - 1:
            pontos = -1

        user_id = mencao.strip("<@!>")
        pontuacoes[user_id] = pontuacoes.get(user_id, 0) + pontos

        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "💩" if i == total_jogadores - 1 else "•"
        resultado.append(f"{emoji} {mencao} — **{pontos:+} ponto(s)**")

    salvar_pontuacoes(pontuacoes)

    resposta = f"✅ Partida de **{jogo}** registrada!\n🕒 Duração: `{duracao}`\n\n" + "\n".join(resultado)
    await interaction.response.send_message(resposta)

# ----- COMANDO /ranking -----
@bot.tree.command(name="ranking", description="Ver ranking atual")
async def ranking(interaction: discord.Interaction):
    pontuacoes = carregar_pontuacoes()

    if not pontuacoes:
        await interaction.response.send_message("📉 Ainda não há dados no ranking.")
        return

    ranking_ordenado = sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True)
    texto = "🏆 **Ranking Geral**\n\n"
    for pos, (user_id, pontos) in enumerate(ranking_ordenado, 1):
        medalha = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else "🔹"
        texto += f"{medalha} <@{user_id}> — **{pontos} ponto(s)**\n"

    await interaction.response.send_message(texto)

# ----- EXECUÇÃO -----
bot.run(TOKEN)
