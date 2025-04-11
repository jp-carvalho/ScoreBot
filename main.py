import os
import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime

# Pega o token dos secrets
TOKEN = os.environ["TOKEN"]

# ID do servidor Discord onde os comandos serão registrados
GUILD_ID = 709705286083936256

# Caminho para salvar os dados
DADOS_FILE = "dados.json"

# Emojis para as posições
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

# Cria estrutura inicial de dados se não existir
if not os.path.exists(DADOS_FILE):
    with open(DADOS_FILE, "w") as f:
        json.dump([], f)

# Inicializa o bot com intents básicos
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Função para carregar e salvar dados
def carregar_dados():
    with open(DADOS_FILE, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DADOS_FILE, "w") as f:
        json.dump(dados, f, indent=2)

# Calcula pontuação por posição
def calcular_pontos(pos, total_jogadores):
    if pos == 0:
        return 3
    elif pos == 1:
        return 1
    elif pos == total_jogadores - 1:
        return -1
    else:
        return 0

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"🤖 Bot online como {bot.user}")

# Comando para registrar uma partida
@bot.tree.command(name="registrar", description="Registrar uma partida", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    jogo="Nome do jogo",
    duracao="Duração da partida (ex: 2h)",
    jogador1="1º lugar", jogador2="2º lugar", jogador3="3º lugar",
    jogador4="4º lugar", jogador5="5º lugar", jogador6="6º lugar",
    jogador7="7º lugar", jogador8="8º lugar"
)
async def registrar(
    interaction: discord.Interaction,
    jogo: str,
    duracao: str,
    jogador1: discord.Member,
    jogador2: discord.Member,
    jogador3: discord.Member,
    jogador4: discord.Member = None,
    jogador5: discord.Member = None,
    jogador6: discord.Member = None,
    jogador7: discord.Member = None,
    jogador8: discord.Member = None
):
    jogadores = [j for j in [jogador1, jogador2, jogador3, jogador4, jogador5, jogador6, jogador7, jogador8] if j]
    total_jogadores = len(jogadores)

    dados = carregar_dados()
    partida = {
        "jogo": jogo,
        "duracao": duracao,
        "data": datetime.now().isoformat(),
        "jogadores": [j.mention for j in jogadores]
    }
    dados.append(partida)
    salvar_dados(dados)

    # Monta mensagem de confirmação
    resultado = ""
    for idx, jogador in enumerate(jogadores):
        pontos = calcular_pontos(idx, total_jogadores)
        resultado += f"{POSICOES[idx]} {jogador.mention} ({pontos:+} pts)\n"

    await interaction.response.send_message(
        f"✅ Partida registrada!\n🎮 **{jogo}** - ⏱️ {duracao}\n\n{resultado}"
    )

# Comando para exibir ranking
@bot.tree.command(name="ranking", description="Ver ranking de pontuações", guild=discord.Object(id=GUILD_ID))
async def ranking(interaction: discord.Interaction):
    dados = carregar_dados()
    pontuacoes = {}

    for partida in dados:
        jogadores = partida["jogadores"]
        total = len(jogadores)
        for i, nome in enumerate(jogadores):
            pontos = calcular_pontos(i, total)
            pontuacoes[nome] = pontuacoes.get(nome, 0) + pontos

    ranking_ordenado = sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True)

    if not ranking_ordenado:
        await interaction.response.send_message("📉 Ainda não há partidas registradas.")
        return

    mensagem = "🏆 **Ranking Geral**:\n\n"
    for idx, (nome, pontos) in enumerate(ranking_ordenado, start=1):
        medalha = POSICOES[idx - 1] if idx <= len(POSICOES) else f"{idx}º"
        cor = "🟩" if pontos > 0 else "🟥" if pontos < 0 else "⬜"
        mensagem += f"{medalha} {nome} — {cor} {pontos} pontos\n"

    await interaction.response.send_message(mensagem)

bot.run(TOKEN)
