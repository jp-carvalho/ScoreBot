import os
import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime

# Configurações iniciais
TOKEN = os.getenv("TOKEN")  # Melhor prática para variáveis de ambiente
if not TOKEN:
    raise ValueError("Token não encontrado! Verifique suas variáveis de ambiente.")

GUILD_ID = 709705286083936256  # ID do servidor para comandos específicos
DADOS_FILE = "dados.json"
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

# Inicialização do bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Funções Auxiliares ---
def carregar_dados():
    """Carrega os dados do arquivo JSON."""
    try:
        with open(DADOS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []  # Retorna lista vazia se o arquivo não existir ou for inválido

def salvar_dados(dados):
    """Salva os dados no arquivo JSON."""
    with open(DADOS_FILE, "w") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def calcular_pontos(pos, total_jogadores):
    """Calcula os pontos com base na posição."""
    return {
        0: 3,                   # 1º lugar
        1: 1,                   # 2º lugar
        total_jogadores - 1: -1 # Último lugar
    }.get(pos, 0)               # Outras posições

# --- Eventos ---
@bot.event
async def on_ready():
    """Evento disparado quando o bot está pronto."""
    print(f"\n🤖 Bot conectado como {bot.user}")
    print(f"📅 Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    try:
        # Sincroniza comandos apenas no servidor especificado
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ {len(synced)} comandos sincronizados no servidor {GUILD_ID}")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {type(e).__name__} - {e}")

# --- Comandos Slash ---
@bot.tree.command(
    name="registrar",
    description="Registra uma partida com os jogadores e suas posições",
    guild=discord.Object(id=GUILD_ID)
@app_commands.describe(
    jogo="Nome do jogo",
    duracao="Duração da partida (ex: 2h30m)",
    jogador1="1º lugar (Vencedor)",
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
    # Filtra jogadores não nulos
    jogadores = [j for j in [
        jogador1, jogador2, jogador3, 
        jogador4, jogador5, jogador6, 
        jogador7, jogador8
    ] if j]

    if len(jogadores) < 3:
        return await interaction.response.send_message(
            "⚠️ É necessário pelo menos 3 jogadores para registrar uma partida!",
            ephemeral=True
        )

    # Processa os dados
    partida = {
        "jogo": jogo,
        "duracao": duracao,
        "data": datetime.now().isoformat(),
        "jogadores": [str(j.id) for j in jogadores]  # Salva IDs em vez de menções
    }

    dados = carregar_dados()
    dados.append(partida)
    salvar_dados(dados)

    # Gera mensagem de resultado
    resultado = []
    for idx, jogador in enumerate(jogadores):
        pontos = calcular_pontos(idx, len(jogadores))
        resultado.append(
            f"{POSICOES[idx]} {jogador.mention} → **{pontos:+} ponto{'s' if abs(pontos) != 1 else ''}**"
        )

    embed = discord.Embed(
        title=f"🎮 {jogo} | ⏱️ {duracao}",
        description="\n".join(resultado),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Partida registrada em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    await interaction.response.send_message(
        content="✅ **Partida registrada com sucesso!**",
        embed=embed
    )

@bot.tree.command(
    name="ranking",
    description="Mostra o ranking atual de pontuações",
    guild=discord.Object(id=GUILD_ID)
)
async def ranking(interaction: discord.Interaction):
    """Exibe o ranking geral de jogadores."""
    dados = carregar_dados()
    pontuacoes = {}

    # Calcula pontuações
    for partida in dados:
        total_jogadores = len(partida["jogadores"])
        for pos, jogador_id in enumerate(partida["jogadores"]):
            pontuacoes[jogador_id] = pontuacoes.get(jogador_id, 0) + calcular_pontos(pos, total_jogadores)

    if not pontuacoes:
        return await interaction.response.send_message(
            "📭 Nenhuma partida registrada ainda!",
            ephemeral=True
        )

    # Converte IDs para menções e ordena
    ranking_ordenado = []
    for jogador_id, pontos in sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True):
        try:
            jogador = await interaction.guild.fetch_member(int(jogador_id))
            ranking_ordenado.append((jogador.mention, pontos))
        except:
            continue  # Ignora jogadores não encontrados

    # Formata a mensagem
    embed = discord.Embed(
        title="🏆 Ranking Geral",
        color=discord.Color.gold()
    )

    for pos, (jogador, pontos) in enumerate(ranking_ordenado, start=1):
        medalha = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}º"
        embed.add_field(
            name=f"{medalha} {jogador}",
            value=f"`{pontos} ponto{'s' if abs(pontos) != 1 else ''}`",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# --- Execução ---
if __name__ == "__main__":
    # Verifica se o arquivo de dados existe
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)

    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token inválido! Verifique suas variáveis de ambiente.")