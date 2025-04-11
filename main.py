import os
import discord
import json
import asyncio
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands

# Configurações
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 709705286083936256
DADOS_FILE = "dados.json"
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
CANAL_RANKING_ID = 1360294622768926901
MINIMO_JOGADORES = 2

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Funções auxiliares (mantidas iguais)
def carregar_dados():
    try:
        with open(DADOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def salvar_dados(dados):
    with open(DADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def calcular_pontos(pos, total_jogadores):
    if pos == 0: return 3
    elif pos == 1: return 1
    elif pos == total_jogadores - 1: return -1
    else: return 0

def filtrar_partidas_por_periodo_e_jogo(dados, periodo=None, jogo=None):
    agora = datetime.now()    
    if periodo == "semana":
        limite = agora - timedelta(weeks=1)
    elif periodo == "mes":
        limite = agora - timedelta(days=30)
    elif periodo == "ano":
        limite = agora - timedelta(days=365)
    else:
        limite = None

    return [p for p in dados if (not limite or datetime.fromisoformat(p["data"]) >= limite) and 
                               (not jogo or p["jogo"].lower() == jogo.lower())]

def obter_jogos_unicos(dados):
    return sorted({p["jogo"].lower() for p in dados})

# Comando alterado de /registrar para /game
@bot.tree.command(name="game", description="Registra uma partida competitiva")
@app_commands.describe(
    jogo="Nome do jogo (ex: Uno, Xadrez)",
    duracao="Duração (ex: 1h30m)",
    jogador1="1º lugar (vencedor)",
    jogador2="2º lugar",
    jogador3="3º lugar (opcional)",
    jogador4="4º lugar (opcional)",
    jogador5="5º lugar (opcional)",
    jogador6="6º lugar (opcional)",
    jogador7="7º lugar (opcional)",
    jogador8="8º lugar (opcional)"
)
async def registrar_partida(interaction: discord.Interaction, jogo: str, duracao: str, 
                          jogador1: discord.Member, jogador2: discord.Member,
                          jogador3: discord.Member = None, jogador4: discord.Member = None,
                          jogador5: discord.Member = None, jogador6: discord.Member = None,
                          jogador7: discord.Member = None, jogador8: discord.Member = None):

    jogadores = [j for j in [jogador1, jogador2, jogador3, jogador4, 
                            jogador5, jogador6, jogador7, jogador8] if j is not None]

    if len(jogadores) < MINIMO_JOGADORES:
        return await interaction.response.send_message(
            f"❌ Mínimo de {MINIMO_JOGADORES} jogadores para registrar!",
            ephemeral=True
        )

    partida = {
        "jogo": jogo,
        "duracao": duracao,
        "data": datetime.now().isoformat(),
        "jogadores": [str(j.id) for j in jogadores]
    }

    dados = carregar_dados()
    dados.append(partida)
    salvar_dados(dados)

    embed = discord.Embed(
        title=f"🎮 {jogo} | ⏱️ {duracao}",
        color=0x2ecc71
    )

    for idx, jogador in enumerate(jogadores):
        pontos = calcular_pontos(idx, len(jogadores))
        embed.add_field(
            name=f"{POSICOES[idx]} {jogador.display_name}",
            value=f"`{pontos:+} ponto{'s' if pontos != 1 else ''}`",
            inline=False
        )

    embed.set_footer(text=f"Registrado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# [Restante do código permanece IDÊNTICO]
# [...] (Funções de ranking, comandos /ranking, /ranking_semanal, etc.)

@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como {bot.user.name}")
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="/game e /ranking"
    ))
    bot.loop.create_task(enviar_rankings_automaticos())

if __name__ == "__main__":
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)
    bot.run(TOKEN)