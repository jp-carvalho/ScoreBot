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
CANAL_RANKING_ID = None  # Defina o ID do canal para envio automático

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# [Restante das funções auxiliares (carregar_dados, salvar_dados, calcular_pontos, filtrar_partidas_por_periodo) permanecem iguais]

async def enviar_ranking_automatico():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()

        # Verifica se é domingo às 23:59 (fim de semana)
        if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
            dados = carregar_dados()
            semana = filtrar_partidas_por_periodo(dados, "semana")
            await mostrar_ranking_automatico(semana, "Semanal")

        # Verifica se é o último dia do mês às 23:59
        if (now + timedelta(days=1)).month != now.month and now.hour == 23 and now.minute == 59:
            dados = carregar_dados()
            mes = filtrar_partidas_por_periodo(dados, "mes")
            await mostrar_ranking_automatico(mes, "Mensal")

        # Verifica se é 31/12 às 23:59
        if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 59:
            dados = carregar_dados()
            ano = filtrar_partidas_por_periodo(dados, "ano")
            await mostrar_ranking_automatico(ano, "Anual")

        await asyncio.sleep(60)  # Verifica a cada minuto

async def mostrar_ranking_automatico(partidas, titulo):
    if not partidas:
        return

    canal = bot.get_channel(CANAL_RANKING_ID)
    if canal:
        embed = await criar_embed_ranking(partidas, titulo, mostrar_estatisticas=True)
        await canal.send(embed=embed)

async def criar_embed_ranking(partidas, titulo, mostrar_estatisticas=False):
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
        title=f"🏆 RANKING {titulo.upper()}",
        color=0x00ff00
    )

    for pos, jogador in enumerate(ranking, start=1):
        emoji = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}º"

        if mostrar_estatisticas or titulo.lower() in ["anual", "mensal"]:
            embed.add_field(
                name=f"{emoji} {jogador['nome']} - {jogador['pontos']} pts",
                value=(
                    f"📊 Partidas: {jogador['partidas']}\n"
                    f"📈 Média: {jogador['media']} pts/partida"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name=f"{emoji} {jogador['nome']} - {jogador['pontos']} pts",
                value="\u200b",
                inline=False
            )

    embed.set_footer(text=f"Total de partidas no período: {len(partidas)}")
    return embed

@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como {bot.user.name}")
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/ranking"))
    bot.loop.create_task(enviar_ranking_automatico())

# [Comandos slash (registrar, ranking, ranking_semanal, ranking_mensal, ranking_anual) permanecem com mesma estrutura]
# Exemplo para ranking_anual:
@bot.tree.command(name="ranking_anual", description="Mostra o ranking do ano")
async def ranking_anual(interaction: discord.Interaction):
    dados = carregar_dados()
    ano = filtrar_partidas_por_periodo(dados, "ano")
    embed = await criar_embed_ranking(ano, "Anual", mostrar_estatisticas=True)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)
    bot.run(TOKEN)