import os
import discord
import json
import asyncio
import shutil
import atexit
import traceback
from threading import Lock
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands

# ======================
# CONFIGURAÇÕES GLOBAIS
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 709705286083936256

# Configuração de persistência
DATA_DIR = "data"
DADOS_FILE = os.path.join(DATA_DIR, "dados.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
CANAL_RANKING_ID = 1360294622768926901
MINIMO_JOGADORES = 2

# Lock para operações de arquivo
file_lock = Lock()

# ======================
# INICIALIZAÇÃO DO BOT
# ======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ======================
# SISTEMA DE PERSISTÊNCIA (JSON)
# ======================
def init_persistence():
    """Garante a estrutura de arquivos e diretórios"""
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"📁 Diretório '{DATA_DIR}' criado")

        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"📁 Diretório de backups '{BACKUP_DIR}' criado")

        if not os.path.exists(DADOS_FILE):
            with open(DADOS_FILE, "w") as f:
                json.dump({"partidas": [], "pontuacao": {}}, f)
            print(f"📄 Arquivo '{DADOS_FILE}' criado com estrutura inicial")

    except Exception as e:
        print(f"❌ Erro na inicialização: {str(e)}")
        traceback.print_exc()

def carregar_dados():
    """Carrega os dados do arquivo JSON"""
    try:
        with file_lock:
            if not os.path.exists(DADOS_FILE) or os.path.getsize(DADOS_FILE) == 0:
                return {"partidas": [], "pontuacao": {}}

            with open(DADOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        backup_corrupt_file()
        return {"partidas": [], "pontuacao": {}}

def salvar_dados(dados):
    """Salva os dados no arquivo JSON"""
    try:
        with file_lock:
            temp_file = DADOS_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)

            if os.path.exists(DADOS_FILE):
                os.replace(temp_file, DADOS_FILE)
            else:
                shutil.move(temp_file, DADOS_FILE)
    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise

def backup_corrupt_file():
    """Faz backup de um arquivo possivelmente corrompido"""
    try:
        if not os.path.exists(DADOS_FILE) or os.path.getsize(DADOS_FILE) == 0:
            return

        corrupt_backup = os.path.join(BACKUP_DIR, f"dados_corruptos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(DADOS_FILE, corrupt_backup)
        print(f"⚠️ Backup do arquivo corrompido salvo em: {corrupt_backup}")
    except Exception as e:
        print(f"⚠️ Falha ao criar backup do arquivo corrompido: {e}")

def criar_backup_automatico():
    """Cria um backup automático dos dados"""
    try:
        dados = carregar_dados()
        if not dados:
            return

        # Backup diário
        backup_file = os.path.join(BACKUP_DIR, f"dados_backup_{datetime.now().strftime('%Y%m%d')}.json")
        with open(backup_file, "w") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        # Backup com timestamp
        timestamp_backup = os.path.join(BACKUP_DIR, f"dados_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(timestamp_backup, "w") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        print(f"✅ Backup automático criado em: {backup_file}")
    except Exception as e:
        print(f"⚠️ Falha ao criar backup automático: {e}")

# ======================
# FUNÇÕES AUXILIARES
# ======================
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

    partidas = dados.get("partidas", [])
    return [p for p in partidas if (not limite or datetime.fromisoformat(p["data"]) >= limite) and 
                               (not jogo or p["jogo"].lower() == jogo.lower())]

def obter_jogos_unicos(dados):
    partidas = dados.get("partidas", [])
    return sorted({p["jogo"].lower() for p in partidas})

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

# ======================
# COMANDOS DE GERENCIAMENTO DE DADOS
# ======================
@bot.tree.command(name="get_data", description="📥 Baixa o arquivo de dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def download_data(interaction: discord.Interaction):
    try:
        if not os.path.exists(DADOS_FILE) or os.path.getsize(DADOS_FILE) == 0:
            return await interaction.response.send_message(
                "⚠️ O arquivo de dados está vazio!",
                ephemeral=True
            )

        await interaction.response.send_message(
            content="📤 Aqui está o arquivo de dados atual:",
            file=discord.File(DADOS_FILE),
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao preparar arquivo para download: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="upload_data", description="📤 Envia um novo arquivo de dados (substitui o atual)")
@app_commands.default_permissions(administrator=True)
async def upload_data(interaction: discord.Interaction, arquivo: discord.Attachment):
    # Verifica se é um arquivo JSON
    if not arquivo.filename.endswith('.json'):
        return await interaction.response.send_message("❌ O arquivo deve ser .json!", ephemeral=True)

    try:
        # Baixa o arquivo temporariamente
        await arquivo.save(f"temp_{DADOS_FILE}")

        # Valida o conteúdo JSON
        with open(f"temp_{DADOS_FILE}", 'r') as f:
            json.load(f)  # Testa se é JSON válido

        # Substitui o arquivo original
        shutil.move(f"temp_{DADOS_FILE}", DADOS_FILE)

        await interaction.response.send_message(
            "✅ Arquivo de dados atualizado com sucesso!",
            ephemeral=True
        )
    except json.JSONDecodeError:
        await interaction.response.send_message(
            "❌ Arquivo JSON inválido!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao atualizar: {str(e)}",
            ephemeral=True
        )
        if os.path.exists(f"temp_{DADOS_FILE}"):
            os.remove(f"temp_{DADOS_FILE}")

@bot.tree.command(name="view_data", description="👁️ Mostra os dados atuais (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def view_data(interaction: discord.Interaction):
    try:
        dados = carregar_dados()
        formatted_data = json.dumps(dados, indent=2, ensure_ascii=False)

        if len(formatted_data) > 1500:
            parts = [formatted_data[i:i+1500] for i in range(0, len(formatted_data), 1500)]
            await interaction.response.send_message(
                "📊 Dados atuais (parte 1/{}):```json\n{}```".format(len(parts), parts[0]),
                ephemeral=True
            )
            for part in parts[1:]:
                await interaction.followup.send(
                    "```json\n{}```".format(part),
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"📊 Dados atuais:```json\n{formatted_data}```",
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao exibir dados: {str(e)}",
            ephemeral=True
        )

# ======================
# COMANDOS DE REGISTRO
# ======================
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

    try:
        dados = carregar_dados()

        # Cria a nova partida
        nova_partida = {
            "jogo": jogo,
            "duracao": duracao,
            "data": datetime.now().isoformat(),
            "jogadores": [str(j.id) for j in jogadores]
        }

        # Adiciona à lista de partidas
        dados["partidas"].append(nova_partida)

        # Atualiza pontuação acumulada
        total_jogadores = len(jogadores)
        for pos, jogador in enumerate(jogadores):
            pontos = calcular_pontos(pos, total_jogadores)
            jogador_id = str(jogador.id)
            dados["pontuacao"][jogador_id] = dados["pontuacao"].get(jogador_id, 0) + pontos

        salvar_dados(dados)

        # Monta mensagem de resultado
        resultado = f"🎮 {jogo} | ⏱️ {duracao}\n\n"
        for idx, jogador in enumerate(jogadores):
            pontos = calcular_pontos(idx, len(jogadores))
            resultado += f"{POSICOES[idx]} {jogador.display_name} | {pontos:+} ponto{'s' if pontos != 1 else ''}\n"

        # Adiciona pontuação acumulada
        resultado += "\n📊 Pontuação Acumulada:\n"
        for jogador in jogadores:
            jogador_id = str(jogador.id)
            resultado += f"{jogador.display_name}: {dados['pontuacao'].get(jogador_id, 0)} pts\n"

        await interaction.response.send_message(resultado)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao registrar partida: {str(e)}",
            ephemeral=True
        )
        traceback.print_exc()

# ======================
# COMANDOS DE CONSULTA
# ======================
@bot.tree.command(name="jogos", description="Lista todos os jogos registrados")
async def listar_jogos(interaction: discord.Interaction):
    try:
        dados = carregar_dados()
        jogos = obter_jogos_unicos(dados)

        if not jogos:
            return await interaction.response.send_message("❌ Nenhum jogo registrado ainda!", ephemeral=True)

        mensagem = "**🎲 Jogos Registrados:**\n\n" + "\n".join(f"• {jogo.capitalize()}" for jogo in jogos)
        await interaction.response.send_message(mensagem)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao listar jogos: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="rank", description="Mostra o ranking geral")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_geral(interaction: discord.Interaction, jogo: str = None):
    try:
        dados = carregar_dados()
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, None, jogo)
        titulo = "Ranking Geral" + (f" - {jogo.capitalize()}" if jogo else "")
        mensagem = await criar_embed_ranking(partidas, titulo)
        await interaction.response.send_message(mensagem)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao gerar ranking: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="rank_semanal", description="Mostra o ranking da semana")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_semanal(interaction: discord.Interaction, jogo: str = None):
    try:
        dados = carregar_dados()
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, "semana", jogo)
        titulo = "Ranking Semanal" + (f" - {jogo.capitalize()}" if jogo else "")
        mensagem = await criar_embed_ranking(partidas, titulo)
        await interaction.response.send_message(mensagem)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao gerar ranking semanal: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="rank_mensal", description="Mostra o ranking do mês")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_mensal(interaction: discord.Interaction, jogo: str = None):
    try:
        dados = carregar_dados()
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, "mes", jogo)
        titulo = "Ranking Mensal" + (f" - {jogo.capitalize()}" if jogo else "")
        mensagem = await criar_embed_ranking(partidas, titulo)
        await interaction.response.send_message(mensagem)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao gerar ranking mensal: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="rank_anual", description="Mostra o ranking do ano")
@app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
async def rank_anual(interaction: discord.Interaction, jogo: str = None):
    try:
        dados = carregar_dados()
        partidas = filtrar_partidas_por_periodo_e_jogo(dados, "ano", jogo)
        titulo = "Ranking Anual" + (f" - {jogo.capitalize()}" if jogo else "")
        mensagem = await criar_embed_ranking(partidas, titulo)
        await interaction.response.send_message(mensagem)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao gerar ranking anual: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="rank_all", description="Mostra o ranking de todos os jogos")
async def rank_all(interaction: discord.Interaction):
    try:
        dados = carregar_dados()
        jogos = obter_jogos_unicos(dados)

        if not jogos:
            return await interaction.response.send_message("❌ Nenhuma partida registrada ainda!")

        await interaction.response.defer()

        mensagem_final = ""
        for jogo in jogos:
            partidas = filtrar_partidas_por_periodo_e_jogo(dados, None, jogo)
            if partidas:
                ranking = await criar_embed_ranking(partidas, f"Ranking - {jogo.capitalize()}")
                mensagem_final += f"{ranking}\n\n"

        if not mensagem_final:
            return await interaction.followup.send("❌ Nenhum ranking disponível!")

        partes = [mensagem_final[i:i+2000] for i in range(0, len(mensagem_final), 2000)]
        for parte in partes:
            await interaction.followup.send(parte)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao gerar rankings: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="rank_jogador", description="Mostra estatísticas de um jogador específico")
@app_commands.describe(jogador="Jogador para ver as estatísticas")
async def rank_jogador(interaction: discord.Interaction, jogador: discord.Member):
    try:
        dados = carregar_dados()
        jogador_id = str(jogador.id)

        estatisticas = {
            "pontos": 0,
            "partidas": 0,
            "vitorias": 0,
            "fracassos": 0,
            "por_jogo": {}
        }

        for partida in dados["partidas"]:
            if jogador_id in partida["jogadores"]:
                pos = partida["jogadores"].index(jogador_id)
                total_jogadores = len(partida["jogadores"])
                pontos = calcular_pontos(pos, total_jogadores)

                estatisticas["pontos"] += pontos
                estatisticas["partidas"] += 1

                if pos == 0:
                    estatisticas["vitorias"] += 1
                if pos == total_jogadores - 1:
                    estatisticas["fracassos"] += 1

                # Estatísticas por jogo
                jogo = partida["jogo"].lower()
                if jogo not in estatisticas["por_jogo"]:
                    estatisticas["por_jogo"][jogo] = {
                        "pontos": 0,
                        "partidas": 0,
                        "vitorias": 0,
                        "fracassos": 0
                    }

                estatisticas["por_jogo"][jogo]["pontos"] += pontos
                estatisticas["por_jogo"][jogo]["partidas"] += 1
                if pos == 0:
                    estatisticas["por_jogo"][jogo]["vitorias"] += 1
                if pos == total_jogadores - 1:
                    estatisticas["por_jogo"][jogo]["fracassos"] += 1

        if estatisticas["partidas"] == 0:
            return await interaction.response.send_message(
                f"ℹ️ {jogador.display_name} não possui partidas registradas!",
                ephemeral=True
            )

        media = estatisticas["pontos"] / estatisticas["partidas"]

        mensagem = (
            f"**📊 Estatísticas de {jogador.display_name}**\n\n"
            f"🏆 **Pontuação Total:** {estatisticas['pontos']}\n"
            f"🎮 **Partidas Jogadas:** {estatisticas['partidas']}\n"
            f"🥇 **Vitórias:** {estatisticas['vitorias']}\n"
            f"💀 **Fracassos:** {estatisticas['fracassos']}\n"
            f"📈 **Média de Pontos/Partida:** {round(media, 2)}\n\n"
            f"**🎲 Desempenho por Jogo:**\n"
        )

        for jogo, stats in estatisticas["por_jogo"].items():
            mensagem += (
                f"\n**{jogo.capitalize()}:** "
                f"{stats['pontos']} pts | "
                f"{stats['partidas']} partidas | "
                f"{stats['vitorias']}🥇 | "
                f"{stats['fracassos']}💀"
            )

        await interaction.response.send_message(mensagem)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao gerar estatísticas do jogador: {str(e)}",
            ephemeral=True
        )

# ======================
# COMANDOS DE BACKUP
# ======================
@bot.tree.command(name="backup", description="🔵 Cria um backup dos dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def criar_backup(interaction: discord.Interaction):
    try:
        criar_backup_automatico()
        await interaction.response.send_message(
            "✅ Backup criado com sucesso!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao criar backup: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="reset_data", description="🔴 RESETA todos os dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def reset_data(interaction: discord.Interaction, confirmacao: str):
    if confirmacao.lower() != "confirmar-reset-total":
        return await interaction.response.send_message(
            "❌ Confirmação inválida! Use `confirmar-reset-total` para resetar.",
            ephemeral=True
        )

    try:
        criar_backup_automatico()
        with open(DADOS_FILE, "w") as f:
            json.dump({"partidas": [], "pontuacao": {}}, f)

        await interaction.response.send_message(
            "✅ Banco de dados resetado com sucesso! Todos os registros foram apagados.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao resetar: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="debug_files", description="Mostra estrutura de arquivos")
async def debug_files(interaction: discord.Interaction):
    try:
        import os
        from pathlib import Path

        # Lista todos os arquivos no diretório atual
        files = []
        for root, dirs, filenames in os.walk('.'):
            for filename in filenames:
                files.append(os.path.join(root, filename))

        # Verifica se o arquivo de dados existe
        dados_exists = os.path.exists(DADOS_FILE)

        # Mostra informações
        message = (
            f"📁 Diretório atual: {os.getcwd()}\n"
            f"📄 Arquivo de dados existe: {dados_exists}\n"
            f"📄 Caminho completo: {os.path.abspath(DADOS_FILE)}\n\n"
            f"📂 Arquivos encontrados:\n" + "\n".join(files[:20])  # Limita a 20 arquivos
        )

        await interaction.response.send_message(f"```{message}```", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

# ======================
# SISTEMA AUTOMÁTICO
# ======================
async def enviar_rankings_automaticos():
    await bot.wait_until_ready()
    canal = bot.get_channel(CANAL_RANKING_ID)
    if not canal:
        print(f"❌ Canal de rankings ({CANAL_RANKING_ID}) não encontrado!")
        return

    while not bot.is_closed():
        now = datetime.now()

        try:
            # Domingo às 23:59 - Ranking Semanal
            if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
                dados = carregar_dados()
                partidas = filtrar_partidas_por_periodo_e_jogo(dados, "semana")
                mensagem = await criar_embed_ranking(partidas, "Ranking Semanal")
                await canal.send(mensagem)
                criar_backup_automatico()

            # Último dia do mês às 23:59 - Ranking Mensal
            if (now + timedelta(days=1)).month != now.month and now.hour == 23 and now.minute == 59:
                dados = carregar_dados()
                partidas = filtrar_partidas_por_periodo_e_jogo(dados, "mes")
                mensagem = await criar_embed_ranking(partidas, "Ranking Mensal")
                await canal.send(mensagem)
                criar_backup_automatico()

            # 31/12 às 23:59 - Ranking Anual
            if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 59:
                dados = carregar_dados()
                partidas = filtrar_partidas_por_periodo_e_jogo(dados, "ano")
                mensagem = await criar_embed_ranking(partidas, "Ranking Anual")
                await canal.send(mensagem)
                criar_backup_automatico()

            await asyncio.sleep(60)
        except Exception as e:
            print(f"⚠️ Erro no sistema automático: {e}")
            await asyncio.sleep(60)

# ======================
# EVENTOS DO BOT
# ======================
@bot.event
async def on_ready():
    init_persistence()  # Garante que os diretórios e arquivos existam

    # Cabeçalho de inicialização
    print("\n" + "="*50)
    print(f"🟢 BOT INICIALIZADO - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*50)
    print(f"🔷 Nome: {bot.user.name}")
    print(f"🔷 ID: {bot.user.id}")
    print(f"🔷 Versão Discord.py: {discord.__version__}")
    print(f"🔷 Caminho dos dados: {os.path.abspath(DADOS_FILE)}")
    print("="*50)

    # Sincronização de comandos
    try:
        synced = await bot.tree.sync()
        print(f"\n🔧 COMANDOS SLASH ({len(synced)} registrados):")
        for cmd in sorted(synced, key=lambda c: c.name):
            print(f"├─ /{cmd.name}: {cmd.description}")
    except Exception as e:
        print(f"\n⚠️ ERRO NA SINCRONIZAÇÃO:")
        traceback.print_exc()

    # Status e tarefas
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="/game e /rank"
    ))
    bot.loop.create_task(enviar_rankings_automaticos())

    print("\n" + "="*50)
    print("✅ BOT PRONTO PARA USO")
    print(f"🕒 Última inicialização: {datetime.now().strftime('%H:%M:%S')}")
    print("="*50 + "\n")

# ======================
# COMANDOS DE ADMINISTRAÇÃO
# ======================
@bot.command()
async def sync(ctx):
    """Sincroniza os comandos slash (apenas dono)"""
    if ctx.author.id == 221794283009736705:  # Seu ID
        await bot.tree.sync()
        await ctx.send("✅ Comandos sincronizados!")
    else:
        await ctx.send("❌ Você não tem permissão para executar este comando.")


# ======================
# INICIALIZAÇÃO
# ======================
if __name__ == "__main__":
    # Garante que os diretórios existam
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    # Cria arquivo de dados se não existir
    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump({"partidas": [], "pontuacao": {}}, f)

    # Registra backup automático ao sair
    atexit.register(criar_backup_automatico)

    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        traceback.print_exc()
        criar_backup_automatico()