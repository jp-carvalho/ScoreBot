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

# Funções auxiliares
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

# Comando /game
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

# Função para criar rankings (CORRIGIDA)
async def criar_embed_ranking(partidas, titulo, mostrar_extremos=False):
    estatisticas = {}

    for partida in partidas:
        total_jogadores = len(partida["jogadores"])
        for pos, jogador_id in enumerate(partida["jogadores"]):
            pontos = calcular_pontos(pos, total_jogadores)

            if jogador_id not in estatisticas:
                estatisticas[jogador_id] = {
                    "pontos": 0,
                    "partidas": 0,
                    "vitorias": 0,
                    "fracassos": 0
                }

            estatisticas[jogador_id]["pontos"] += pontos
            estatisticas[jogador_id]["partidas"] += 1

            if pos == 0:
                estatisticas[jogador_id]["vitorias"] += 1
            if pos == total_jogadores - 1:
                estatisticas[jogador_id]["fracassos"] += 1

    ranking = []
    for jogador_id, stats in estatisticas.items():
        try:
            jogador = await bot.get_guild(GUILD_ID).fetch_member(int(jogador_id))
            media = stats["pontos"] / stats["partidas"] if stats["partidas"] > 0 else 0
            ranking.append({
                "nome": jogador.display_name,
                "pontos": stats["pontos"],
                "partidas": stats["partidas"],
                "media": round(media, 2),
                "vitorias": stats["vitorias"],
                "fracassos": stats["fracassos"]
            })
        except:
            continue

    ranking.sort(key=lambda x: x["pontos"], reverse=True)

    embed = discord.Embed(
        title=f"🏆 {titulo.upper()}",
        color=0x00ff00
    )

    for pos, jogador in enumerate(ranking, start=1):
        emoji = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}º"
        field_name = f"{emoji} {jogador['nome']} - {jogador['pontos']} pts"

        stats_lines = [
            f"📊 Partidas: {jogador['partidas']}",
            f"📈 Média: {jogador['media']} pts/partida"
        ]

        if mostrar_extremos:
            stats_lines.extend([
                f"🥇 Vitórias: {jogador['vitorias']}",
                f"💀 Fracassos: {jogador['fracassos']}"
            ])

        embed.add_field(
            name=field_name,
            value="\n".join(stats_lines),
            inline=False
        )

    embed.set_footer(text=f"Total de partidas: {len(partidas)}")
    return embed

# Comandos de ranking (ATUALIZADOS para /rank*)
@bot.tree.command(name="rank", description="Mostra o ranking geral")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_geral(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    if jogo:
        dados = filtrar_partidas_por_periodo_e_jogo(dados, None, jogo)
        titulo = f"Geral - {jogo}"
    else:
        titulo = "Geral"
    embed = await criar_embed_ranking(dados, titulo)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rank_semanal", description="Mostra o ranking da semana")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_semanal(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    semana = filtrar_partidas_por_periodo_e_jogo(dados, "semana", jogo)
    titulo = f"Semanal - {jogo}" if jogo else "Semanal"
    embed = await criar_embed_ranking(semana, titulo)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rank_mensal", description="Mostra o ranking do mês")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_mensal(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    mes = filtrar_partidas_por_periodo_e_jogo(dados, "mes", jogo)
    titulo = f"Mensal - {jogo}" if jogo else "Mensal"
    embed = await criar_embed_ranking(mes, titulo, True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rank_anual", description="Mostra o ranking do ano")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_anual(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    ano = filtrar_partidas_por_periodo_e_jogo(dados, "ano", jogo)
    titulo = f"Anual - {jogo}" if jogo else "Anual"
    embed = await criar_embed_ranking(ano, titulo, True)
    await interaction.response.send_message(embed=embed)

# Sistema automático
async def enviar_rankings_automaticos():
    await bot.wait_until_ready()
    canal = bot.get_channel(CANAL_RANKING_ID)
    if not canal:
        print(f"❌ Canal de rankings ({CANAL_RANKING_ID}) não encontrado!")
        return

    while not bot.is_closed():
        now = datetime.now()

        # Domingo às 23:59 - Ranking Semanal
        if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
            await enviar_ranking_automatico("semana", "Rank Semanal", canal)

        # Último dia do mês às 23:59 - Ranking Mensal
        if (now + timedelta(days=1)).month != now.month and now.hour == 23 and now.minute == 59:
            await enviar_ranking_automatico("mes", "Rank Mensal", canal)

        # 31/12 às 23:59 - Ranking Anual
        if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 59:
            await enviar_ranking_automatico("ano", "Rank Anual", canal)

        await asyncio.sleep(60)

async def enviar_ranking_automatico(periodo, titulo, canal):
    dados = carregar_dados()
    partidas = filtrar_partidas_por_periodo_e_jogo(dados, periodo)

    if not partidas:
        return

    mostrar_extremos = periodo in ["mes", "ano"]
    embed = await criar_embed_ranking(partidas, titulo, mostrar_extremos)
    await canal.send(embed=embed)

@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como {bot.user.name}")
    print(f"📌 Rankings automáticos no canal: {CANAL_RANKING_ID}")
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="/game e /rank"
    ))
    bot.loop.create_task(enviar_rankings_automaticos())

if __name__ == "__main__":
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)
    bot.run(TOKEN)