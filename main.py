import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# Intents obrigatórios
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")  # Token vem da variável de ambiente

DADOS_ARQUIVO = "dados.json"

def carregar_dados():
    if os.path.exists(DADOS_ARQUIVO):
        with open(DADOS_ARQUIVO, "r") as f:
            return json.load(f)
    return {}

def salvar_dados(dados):
    with open(DADOS_ARQUIVO, "w") as f:
        json.dump(dados, f, indent=4)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🤖 Bot online como {bot.user}")

@bot.tree.command(name="registrar", description="Registrar partida")
@app_commands.describe(
    jogo="Nome do jogo",
    primeiro="Jogador em 1º lugar",
    segundo="Jogador em 2º lugar",
    terceiro="Jogador em 3º lugar",
    quarto="Jogador em 4º lugar",
    duracao="Duração da partida (ex: 2h30)"
)
async def registrar(
    interaction: discord.Interaction,
    jogo: str,
    primeiro: discord.Member,
    segundo: discord.Member,
    terceiro: discord.Member,
    quarto: discord.Member,
    duracao: str
):
    jogadores = [primeiro, segundo, terceiro, quarto]
    pontos = [3, 1, 0, -1]

    dados = carregar_dados()
    if jogo not in dados:
        dados[jogo] = {}

    for jogador, ponto in zip(jogadores, pontos):
        user_id = str(jogador.id)
        if user_id in dados[jogo]:
            dados[jogo][user_id] += ponto
        else:
            dados[jogo][user_id] = ponto

    salvar_dados(dados)

    resposta = (
        f"✅ Partida de **{jogo}** registrada!\n"
        f"🏆 Pontuação:\n"
        f"🥇 {primeiro.mention} (+3)\n"
        f"🥈 {segundo.mention} (+1)\n"
        f"🥉 {terceiro.mention} (+0)\n"
        f"💀 {quarto.mention} (-1)\n"
        f"⏱️ Duração: **{duracao}**"
    )
    await interaction.response.send_message(resposta)

@bot.tree.command(name="ranking", description="Mostra o ranking geral de um jogo")
@app_commands.describe(jogo="Nome do jogo")
async def ranking(interaction: discord.Interaction, jogo: str):
    dados = carregar_dados()
    ranking = dados.get(jogo, {})
    if not ranking:
        await interaction.response.send_message(f"Nenhum dado encontrado para o jogo {jogo}.")
        return

    ranking_ordenado = sorted(ranking.items(), key=lambda item: item[1], reverse=True)
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    texto = f"🏆 **Ranking Geral - {jogo}**\n\n"
    for i, (user_id, pontos) in enumerate(ranking_ordenado[:10]):
        emoji = emojis[i] if i < len(emojis) else f"{i+1}º"
        texto += f"{emoji} <@{user_id}> — **{pontos}** pontos\n"

    await interaction.response.send_message(texto)

bot.run(TOKEN)
