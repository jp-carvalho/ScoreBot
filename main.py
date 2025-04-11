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

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Funções de dados
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

def filtrar_partidas_por_periodo(dados, periodo):
    agora = datetime.now()
    if periodo == "semana":
        limite = agora - timedelta(weeks=1)
    elif periodo == "mes":
        limite = agora - timedelta(days=30)
    elif periodo == "ano":
        limite = agora - timedelta(days=365)
    else:
        return dados

    return [p for p in dados if datetime.fromisoformat(p["data"]) >= limite]

@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como {bot.user.name}")
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/ranking"))

# Comando registrar
@bot.tree.command(name="registrar", description="Registra uma partida competitiva")
@app_commands.describe(
    jogo="Nome do jogo (ex: Uno, Xadrez)",
    duracao="Duração (ex: 1h30m)",
    jogador1="1º lugar (vencedor)",
    jogador2="2º lugar",
    jogador3="3º lugar",
    jogador4="4º lugar (opcional)",
    jogador5="5º lugar (opcional)",
    jogador6="6º lugar (opcional)",
    jogador7="7º lugar (opcional)",
    jogador8="8º lugar (opcional)"
)
async def registrar_partida(interaction: discord.Interaction, jogo: str, duracao: str, jogador1: discord.Member, jogador2: discord.Member, jogador3: discord.Member, jogador4: discord.Member = None, jogador5: discord.Member = None, jogador6: discord.Member = None, jogador7: discord.Member = None, jogador8: discord.Member = None):
    jogadores = [j for j in [jogador1, jogador2, jogador3, jogador4, jogador5, jogador6, jogador7, jogador8] if j is not None]

    if len(jogadores) < 3:
        return await interaction.response.send_message(
            "❌ Mínimo de 3 jogadores para registrar!",
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

# Comandos de ranking
@bot.tree.command(name="ranking", description="Mostra o ranking geral")
async def ranking_geral(interaction: discord.Interaction):
    dados = carregar_dados()
    await mostrar_ranking(interaction, dados, "Geral", mostrar_estatisticas=False)

@bot.tree.command(name="ranking_semanal", description="Mostra o ranking da semana")
async def ranking_semanal(interaction: discord.Interaction):
    dados = carregar_dados()
    semana = filtrar_partidas_por_periodo(dados, "semana")
    await mostrar_ranking(interaction, semana, "Semanal", mostrar_estatisticas=False)

@bot.tree.command(name="ranking_mensal", description="Mostra o ranking do mês")
async def ranking_mensal(interaction: discord.Interaction):
    dados = carregar_dados()
    mes = filtrar_partidas_por_periodo(dados, "mes")
    await mostrar_ranking(interaction, mes, "Mensal", mostrar_estatisticas=True)

@bot.tree.command(name="ranking_anual", description="Mostra o ranking do ano")
async def ranking_anual(interaction: discord.Interaction):
    dados = carregar_dados()
    ano = filtrar_partidas_por_periodo(dados, "ano")
    await mostrar_ranking(interaction, ano, "Anual", mostrar_estatisticas=False)

async def mostrar_ranking(interaction: discord.Interaction, partidas, titulo, mostrar_estatisticas=False):
    if not partidas:
        return await interaction.response.send_message(
            f"📭 Nenhuma partida registrada no período {titulo.lower()}!",
            ephemeral=True
        )

    estatisticas = {}

    for partida in partidas:
        total_jogadores = len(partida["jogadores"])
        for pos, jogador_id in enumerate(partida["jogadores"]):
            pontos = calcular_pontos(pos, total_jogadores)

            if jogador_id not in estatisticas:
                estatisticas[jogador_id] = {"pontos": 0, "partidas": 0}

            estatisticas[jogador_id]["pontos"] += pontos
            estatisticas[jogador_id]["partidas"] += 1

    ranking = []
    for jogador_id, stats in estatisticas.items():
        try:
            jogador = await interaction.guild.fetch_member(int(jogador_id))
            media = stats["pontos"] / stats["partidas"]
            ranking.append({
                "nome": jogador.display_name,
                "pontos": stats["pontos"],
                "partidas": stats["partidas"],
                "media": round(media, 2)
            })
        except:
            continue

    ranking.sort(key=lambda x: x["pontos"], reverse=True)

    embed = discord.Embed(
        title=f"🏆 RANKING {titulo.upper()}",
        color=0x00ff00
    )

    for pos, jogador in enumerate(ranking, start=1):
        emoji = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}º"

        if mostrar_estatisticas:
            embed.add_field(
                name=f"{emoji} {jogador['nome']} | {jogador['pontos']} pts",
                value=(
                    f"📊 Partidas: {jogador['partidas']}\n"
                    f"📈 Média: {jogador['media']} pts/partida"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name=f"{emoji} {jogador['nome']}",
                value=f"**{jogador['pontos']} pontos**",
                inline=False
            )

    embed.set_footer(text=f"Total de partidas no período: {len(partidas)}")
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)
    bot.run(TOKEN)