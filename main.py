import os
import discord
import json
import asyncio
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands

# =============================================
# CONFIGURAÇÕES GLOBAIS
# =============================================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 709705286083936256
DADOS_FILE = "dados.json"
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
CANAL_RANKING_ID = 1360294622768926901
MINIMO_JOGADORES = 2

# =============================================
# INICIALIZAÇÃO DO BOT
# =============================================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# =============================================
# FUNÇÕES AUXILIARES
# =============================================
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

async def criar_embed_ranking(partidas, titulo):
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

    mensagem = f"**🏆 {titulo.upper()}**\n\n"
    for pos, jogador in enumerate(ranking[:10], start=1):
        emoji = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}️⃣"
        mensagem += (
            f"**{emoji} {jogador['nome']} | Total: {jogador['pontos']} pts**\n"
            f"📊 Partidas: {jogador['partidas']}\n"
            f"📈 Média: {jogador['media']} pts/partida\n"
            f"🥇 Vitórias: {jogador['vitorias']}\n"
            f"💀 Fracassos: {jogador['fracassos']}\n\n"
        )

    return mensagem.strip()

# =============================================
# COMANDOS DE REGISTRO
# =============================================
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

    resultado = f"🎮 {jogo} | ⏱️ {duracao}\n\n"
    for idx, jogador in enumerate(jogadores):
        pontos = calcular_pontos(idx, len(jogadores))
        resultado += f"{POSICOES[idx]} {jogador.display_name} | {pontos:+} ponto{'s' if pontos != 1 else ''}\n"

    await interaction.response.send_message(resultado)

@bot.tree.command(name="correct", description="Corrige a última partida registrada")
@app_commands.describe(
    jogo="Nome correto do jogo",
    duracao="Duração correta (ex: 1h30m)",
    jogador1="1º lugar correto (vencedor)",
    jogador2="2º lugar correto",
    jogador3="3º lugar correto (opcional)",
    jogador4="4º lugar correto (opcional)",
    jogador5="5º lugar correto (opcional)",
    jogador6="6º lugar correto (opcional)",
    jogador7="7º lugar correto (opcional)",
    jogador8="8º lugar correto (opcional)"
)
async def correct_partida(interaction: discord.Interaction, jogo: str, duracao: str,
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

    dados = carregar_dados()
    if not dados:
        return await interaction.response.send_message("❌ Nenhuma partida para corrigir!", ephemeral=True)

    # Remove a última partida
    ultima_partida = dados.pop()
    salvar_dados(dados)

    # Registra a partida corrigida
    partida_corrigida = {
        "jogo": jogo,
        "duracao": duracao,
        "data": ultima_partida["data"],  # Mantém a data original
        "jogadores": [str(j.id) for j in jogadores]
    }

    dados.append(partida_corrigida)
    salvar_dados(dados)

    resultado = f"✅ **Partida corrigida com sucesso!**\n\n🎮 {jogo} | ⏱️ {duracao}\n\n"
    for idx, jogador in enumerate(jogadores):
        pontos = calcular_pontos(idx, len(jogadores))
        resultado += f"{POSICOES[idx]} {jogador.display_name} | {pontos:+} ponto{'s' if pontos != 1 else ''}\n"

    await interaction.response.send_message(resultado)

# =============================================
# COMANDOS DE CONSULTA
# =============================================
@bot.tree.command(name="jogos", description="Lista todos os jogos registrados")
async def listar_jogos(interaction: discord.Interaction):
    dados = carregar_dados()
    jogos = obter_jogos_unicos(dados)

    if not jogos:
        return await interaction.response.send_message("❌ Nenhum jogo registrado ainda!", ephemeral=True)

    mensagem = "**🎲 Jogos Registrados:**\n\n" + "\n".join(f"• {jogo.capitalize()}" for jogo in jogos)
    await interaction.response.send_message(mensagem)

@bot.tree.command(name="rank", description="Mostra o ranking geral")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_geral(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    partidas = filtrar_partidas_por_periodo_e_jogo(dados, None, jogo)
    titulo = "Ranking Geral" + (f" - {jogo}" if jogo else "")
    mensagem = await criar_embed_ranking(partidas, titulo)
    await interaction.response.send_message(mensagem)

@bot.tree.command(name="rank_semanal", description="Mostra o ranking da semana")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_semanal(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    partidas = filtrar_partidas_por_periodo_e_jogo(dados, "semana", jogo)
    titulo = "Ranking Semanal" + (f" - {jogo}" if jogo else "")
    mensagem = await criar_embed_ranking(partidas, titulo)
    await interaction.response.send_message(mensagem)

@bot.tree.command(name="rank_mensal", description="Mostra o ranking do mês")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_mensal(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    partidas = filtrar_partidas_por_periodo_e_jogo(dados, "mes", jogo)
    titulo = "Ranking Mensal" + (f" - {jogo}" if jogo else "")
    mensagem = await criar_embed_ranking(partidas, titulo)
    await interaction.response.send_message(mensagem)

@bot.tree.command(name="rank_anual", description="Mostra o ranking do ano")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_anual(interaction: discord.Interaction, jogo: str = None):
    dados = carregar_dados()
    partidas = filtrar_partidas_por_periodo_e_jogo(dados, "ano", jogo)
    titulo = "Ranking Anual" + (f" - {jogo}" if jogo else "")
    mensagem = await criar_embed_ranking(partidas, titulo)
    await interaction.response.send_message(mensagem)

@bot.tree.command(name="rank_all", description="Mostra o ranking de todos os jogos")
async def rank_all(interaction: discord.Interaction):
    dados = carregar_dados()
    jogos = obter_jogos_unicos(dados)

    if not jogos:
        return await interaction.response.send_message("❌ Nenhuma partida registrada ainda!", ephemeral=True)

    await interaction.response.defer()

    mensagem_final = ""
    for jogo in jogos:
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, None, jogo)
        if partidas:
            ranking = await criar_embed_ranking(partidas, f"Ranking - {jogo.capitalize()}")
            mensagem_final += f"{ranking}\n\n"

    if not mensagem_final:
        return await interaction.followup.send("❌ Nenhum ranking disponível!")

    # Divide a mensagem se for muito grande
    partes = [mensagem_final[i:i+2000] for i in range(0, len(mensagem_final), 2000)]
    for parte in partes:
        await interaction.followup.send(parte)

# =============================================
# SISTEMA AUTOMÁTICO
# =============================================
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
            await enviar_ranking_automatico("semana", "Ranking Semanal", canal)

        # Último dia do mês às 23:59 - Ranking Mensal
        if (now + timedelta(days=1)).month != now.month and now.hour == 23 and now.minute == 59:
            await enviar_ranking_automatico("mes", "Ranking Mensal", canal)

        # 31/12 às 23:59 - Ranking Anual
        if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 59:
            await enviar_ranking_automatico("ano", "Ranking Anual", canal)

        await asyncio.sleep(60)

async def enviar_ranking_automatico(periodo, titulo, canal):
    dados = carregar_dados()
    jogos = obter_jogos_unicos(dados)

    if not jogos:
        return

    for jogo in jogos:
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, periodo, jogo)
        if partidas:
            mensagem = await criar_embed_ranking(partidas, f"{titulo} - {jogo}")
            await canal.send(mensagem)

# =============================================
# EVENTOS DO BOT
# =============================================
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

# =============================================
# INICIALIZAÇÃO
# =============================================
if __name__ == "__main__":
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)
    bot.run(TOKEN)