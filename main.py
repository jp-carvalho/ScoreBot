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
CANAL_RANKING_ID = 1360294622768926901  # Defina o ID do canal para envio automático

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# [Funções auxiliares carregar_dados, salvar_dados, calcular_pontos permanecem iguais]

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

    partidas_filtradas = []
    for partida in dados:
        # Filtra por período
        if limite and datetime.fromisoformat(partida["data"]) < limite:
            continue
        # Filtra por jogo
        if jogo and partida["jogo"].lower() != jogo.lower():
            continue
        partidas_filtradas.append(partida)

    return partidas_filtradas

def obter_jogos_unicos(dados):
    jogos = set()
    for partida in dados:
        jogos.add(partida["jogo"].lower())
    return sorted(jogos)

async def enviar_rankings_automaticos():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()

        # Verifica se é domingo às 23:59 (fim de semana)
        if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
            await enviar_rankings_por_jogo("semana", "Ranking Semanal")

        # Verifica se é o último dia do mês às 23:59
        if (now + timedelta(days=1)).month != now.month and now.hour == 23 and now.minute == 59:
            await enviar_rankings_por_jogo("mes", "Ranking Mensal")

        # Verifica se é 31/12 às 23:59
        if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 59:
            await enviar_rankings_por_jogo("ano", "Ranking Anual")

        await asyncio.sleep(60)  # Verifica a cada minuto

async def enviar_rankings_por_jogo(periodo, titulo_principal):
    dados = carregar_dados()
    jogos = obter_jogos_unicos(dados)
    canal = bot.get_channel(CANAL_RANKING_ID)

    if not canal or not jogos:
        return

    # Mensagem inicial
    embed_principal = discord.Embed(
        title=f"🏆 {titulo_principal.upper()} 🏆",
        description="Confira os rankings por jogo:",
        color=0x00ff00
    )
    await canal.send(embed=embed_principal)

    # Envia um ranking para cada jogo
    for jogo in jogos:
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, periodo, jogo)
        if partidas:
            embed = await criar_embed_ranking(partidas, f"{titulo_principal} - {jogo}", mostrar_estatisticas=True)
            await canal.send(embed=embed)

    # Espaçamento final
    await canal.send("━━━━━━━━━━━━━━━━━━")

async def criar_embed_ranking(partidas, titulo, mostrar_estatisticas=True):
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
            jogador = await bot.get_guild(GUILD_ID).fetch_member(int(jogador_id))
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
        title=f"🎮 {titulo.upper()}",
        color=0x00ff00
    )

    for pos, jogador in enumerate(ranking, start=1):
        emoji = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}º"
        embed.add_field(
            name=f"{emoji} {jogador['nome']} - {jogador['pontos']} pts",
            value=(
                f"📊 Partidas: {jogador['partidas']}\n"
                f"📈 Média: {jogador['media']} pts/partida"
            ),
            inline=False
        )

    embed.set_footer(text=f"Total de partidas: {len(partidas)}")
    return embed

@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como {bot.user.name}")
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/ranking"))
    bot.loop.create_task(enviar_rankings_automaticos())

# [Comandos de registro e rankings manuais permanecem iguais, apenas atualize para usar filtrar_partidas_por_periodo_e_jogo]

if __name__ == "__main__":
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)
    bot.run(TOKEN)