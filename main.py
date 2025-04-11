import os
import discord
import json
import asyncio
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# ===== CONFIGURAÇÕES =====
TOKEN = os.getenv("DISCORD_TOKEN") or os.environ.get("TOKEN")  # Compatível com Replit e Railway
if not TOKEN:
    raise ValueError("🔴 Token não encontrado! Verifique as variáveis de ambiente.")

GUILD_ID = 709705286083936256  # Substitua pelo ID do seu servidor
DADOS_FILE = "dados.json"
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

# ===== INICIALIZAÇÃO =====
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ===== FUNÇÕES AUXILIARES =====
def carregar_dados():
    """Carrega dados do JSON com tratamento de erros."""
    try:
        with open(DADOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def salvar_dados(dados):
    """Salva dados no JSON com formatação."""
    with open(DADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def calcular_pontos(posicao, total_jogadores):
    """Calcula pontos baseados na posição."""
    return {
        0: 3,                     # 1º lugar
        1: 1,                     # 2º lugar
        total_jogadores - 1: -1    # Último lugar
    }.get(posicao, 0)              # Outras posições

# ===== EVENTOS =====
@bot.event
async def on_ready():
    """Handler de inicialização com sincronização robusta."""
    print(f"\n⚡ Bot conectado como {bot.user} (ID: {bot.user.id})")
    print(f"📅 Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    await asyncio.sleep(2)  # Espera para evitar race conditions

    # Sincronização em 2 etapas (servidor + global)
    try:
        # 1. Sincronização no servidor específico
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        print(f"🔄 Comandos sincronizados no servidor (ID: {GUILD_ID})")
    except Exception as e:
        print(f"⚠️ Sync local falhou: {type(e).__name__} - {e}")

    try:
        # 2. Sincronização global como fallback
        synced = await bot.tree.sync()
        print(f"🌍 {len(synced)} comandos sincronizados globalmente")
    except Exception as e:
        print(f"🚨 Sync global falhou: {type(e).__name__} - {e}")
    finally:
        print("✅ Sincronização concluída!\n")

    # Atualiza status do bot
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"/registrar | {len(bot.guilds)} servidores"
        )
    )

# ===== COMANDOS SLASH =====
@bot.tree.command(
    name="registrar",
    description="Registra uma partida com os jogadores e suas posições"
)
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
    """Registra uma nova partida no sistema."""
    jogadores = [j for j in [
        jogador1, jogador2, jogador3,
        jogador4, jogador5, jogador6,
        jogador7, jogador8
    ] if j is not None]

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

    # Cria embed de resposta
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

@bot.tree.command(
    name="ranking",
    description="Mostra o ranking atual de pontuações"
)
async def ranking(interaction: discord.Interaction):
    """Exibe o ranking geral."""
    dados = carregar_dados()
    pontuacoes = {}

    for partida in dados:
        total = len(partida["jogadores"])
        for pos, jogador_id in enumerate(partida["jogadores"]):
            pontuacoes[jogador_id] = pontuacoes.get(jogador_id, 0) + calcular_pontos(pos, total)

    if not pontuacoes:
        return await interaction.response.send_message(
            "📭 Nenhuma partida registrada ainda!",
            ephemeral=True
        )

    # Converte IDs para membros
    ranking_list = []
    for jogador_id, pontos in sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True):
        try:
            jogador = await interaction.guild.fetch_member(int(jogador_id))
            ranking_list.append((jogador, pontos))
        except:
            continue

    # Formata o embed
    embed = discord.Embed(
        title="🏆 Ranking Geral",
        color=0xf1c40f
    )

    for pos, (jogador, pontos) in enumerate(ranking_list, start=1):
        medalha = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}º"
        embed.add_field(
            name=f"{medalha} {jogador.display_name}",
            value=f"`{pontos} ponto{'s' if pontos != 1 else ''}`",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ===== COMANDO DE DEBUG =====
@bot.command()
@commands.is_owner()
async def sync(ctx):
    """(Owner only) Força a sincronização dos comandos slash."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ {len(synced)} comandos sincronizados!")
    except Exception as e:
        await ctx.send(f"❌ Erro: {type(e).__name__} - {e}")

# ===== INICIALIZAÇÃO =====
if __name__ == "__main__":
    # Garante que o arquivo de dados existe
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)

    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("🔴 Falha no login: Token inválido!")
    except KeyboardInterrupt:
        print("\n🛑 Bot encerrado manualmente")