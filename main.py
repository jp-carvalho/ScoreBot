import discord
from discord import app_commands
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")  # Pegando o token das variáveis de ambiente
DATA_FILE = "dados.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Função para salvar dados
def salvar_dados(jogo, posicoes, duracao):
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)

    with open(DATA_FILE, "r") as f:
        dados = json.load(f)

    if jogo not in dados:
        dados[jogo] = {}

    pontos = [3, 1, 0, 0]

    for i, jogador in enumerate(posicoes):
        if jogador not in dados[jogo]:
            dados[jogo][jogador] = 0
        dados[jogo][jogador] += pontos[i]

    with open(DATA_FILE, "w") as f:
        json.dump(dados, f, indent=4)

# Evento para iniciar o bot
@client.event
async def on_ready():
    await tree.sync()
    print(f"🤖 Bot online como {client.user}")

# Slash Command: /registrar
@tree.command(name="registrar", description="Registrar uma nova partida")
@app_commands.describe(
    jogo="Nome do jogo",
    pos1="Jogador em 1º lugar",
    pos2="Jogador em 2º lugar",
    pos3="Jogador em 3º lugar",
    pos4="Jogador em 4º lugar",
    duracao="Duração da partida (ex: 2h)"
)
async def registrar(interaction: discord.Interaction, jogo: str, pos1: discord.User, pos2: discord.User, pos3: discord.User, pos4: discord.User, duracao: str):
    posicoes = [str(pos1.id), str(pos2.id), str(pos3.id), str(pos4.id)]
    salvar_dados(jogo, posicoes, duracao)

    await interaction.response.send_message(
        f"✅ Partida registrada!\n🎮 Jogo: **{jogo}**\n1️⃣ {pos1.mention}\n2️⃣ {pos2.mention}\n3️⃣ {pos3.mention}\n4️⃣ {pos4.mention}\n🕒 Duração: **{duracao}**"
    )

# Slash Command: /ranking
@tree.command(name="ranking", description="Ver ranking de um jogo")
@app_commands.describe(jogo="Nome do jogo")
async def ranking(interaction: discord.Interaction, jogo: str):
    if not os.path.exists(DATA_FILE):
        await interaction.response.send_message("Ainda não há dados salvos.")
        return

    with open(DATA_FILE, "r") as f:
        dados = json.load(f)

    if jogo not in dados or not dados[jogo]:
        await interaction.response.send_message(f"Sem dados para o jogo **{jogo}**.")
        return

    ranking_ordenado = sorted(dados[jogo].items(), key=lambda x: x[1], reverse=True)
    texto = f"📊 **Ranking de {jogo}**:\n\n"
    for i, (jogador_id, pontos) in enumerate(ranking_ordenado, 1):
        texto += f"{i}º <@{jogador_id}> - {pontos} pontos\n"

    await interaction.response.send_message(texto)

client.run(TOKEN)
