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

# Configuração de persistência (FORÇADO PARA TRUE)
PERSISTENT_MODE = True  # Sobrescreve qualquer variável de ambiente
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
intents.message_content = True  # Habilita a intenção de conteúdo de mensagem
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ======================
# SISTEMA DE PERSISTÊNCIA
# ======================
def init_persistence():
    """Garante a estrutura de arquivos e migra dados se necessário"""
    try:
        # Cria diretórios se não existirem
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"📁 Diretório '{DATA_DIR}' criado")

        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"📁 Diretório de backups '{BACKUP_DIR}' criado")

        # Migração de dados antigos (se existirem)
        old_locations = ["dados.json", "/app/dados.json"]
        for old_file in old_locations:
            if os.path.exists(old_file) and not os.path.exists(DADOS_FILE):
                shutil.move(old_file, DADOS_FILE)
                print(f"♻️ Dados migrados de '{old_file}' para '{DADOS_FILE}'")
                break

        # Cria arquivo se não existir
        if not os.path.exists(DADOS_FILE):
            with open(DADOS_FILE, "w") as f:
                json.dump([], f)
            print(f"📄 Arquivo '{DADOS_FILE}' criado")

    except Exception as e:
        print(f"❌ Erro na inicialização: {str(e)}")
        traceback.print_exc()

def backup_corrupt_file():
    """Faz backup de um arquivo possivelmente corrompido"""
    try:
        if not os.path.exists(DADOS_FILE) or os.path.getsize(DADOS_FILE) == 0:
            return

        corrupt_backup = os.path.join(BACKUP_DIR, f"dados_corruptos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(DADOS_FILE, corrupt_backup)
        print(f"⚠️ Backup do arquivo corrompido salvo em: {corrupt_backup}")
        return corrupt_backup
    except Exception as e:
        print(f"⚠️ Falha ao criar backup do arquivo corrompido: {e}")
        return None

def criar_backup_automatico():
    """Cria um backup automático dos dados"""
    try:
        if not os.path.exists(DADOS_FILE) or os.path.getsize(DADOS_FILE) == 0:
            return

        # Backup diário (sobrescreve se já existir para o dia)
        backup_file = os.path.join(BACKUP_DIR, f"dados_backup_{datetime.now().strftime('%Y%m%d')}.json")
        shutil.copy2(DADOS_FILE, backup_file)

        # Backup com timestamp (mantém histórico)
        timestamp_backup = os.path.join(BACKUP_DIR, f"dados_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(DADOS_FILE, timestamp_backup)

        print(f"✅ Backup automático criado em: {backup_file}")
    except Exception as e:
        print(f"⚠️ Falha ao criar backup automático: {e}")
        traceback.print_exc()

def carregar_dados():
    """Carrega os dados com tratamento robusto de erros"""
    if not os.path.exists(DADOS_FILE):
        return []

    try:
        with file_lock:
            # Verifica se o arquivo não está vazio
            if os.path.getsize(DADOS_FILE) == 0:
                return []

            with open(DADOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠️ Erro ao decodificar JSON (arquivo pode estar corrompido): {e}")
        corrupt_file = backup_corrupt_file()
        if corrupt_file:
            print(f"⚠️ Arquivo corrompido salvo em: {corrupt_file}")
        return []
    except Exception as e:
        print(f"⚠️ Erro inesperado ao carregar dados: {e}")
        traceback.print_exc()
        return []

def salvar_dados(dados):
    """Salva os dados com tratamento robusto de erros"""
    try:
        # Primeiro salva em um arquivo temporário
        temp_file = DADOS_FILE + ".tmp"

        with file_lock:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)

            # Verifica se o arquivo temporário foi criado corretamente
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                raise ValueError("Arquivo temporário não foi criado corretamente")

            # Se chegou aqui sem erros, substitui o arquivo original
            if os.path.exists(DADOS_FILE):
                os.replace(temp_file, DADOS_FILE)
            else:
                shutil.move(temp_file, DADOS_FILE)

        print("✅ Dados salvos com sucesso")
    except Exception as e:
        print(f"⚠️ Erro ao salvar dados: {e}")
        traceback.print_exc()

        # Remove o arquivo temporário se existir
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        raise

# Executa durante a importação
init_persistence()

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
        except Exception as e:
            print(f"⚠️ Erro ao buscar jogador {jogador_id}: {e}")
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

    partida = {
        "jogo": jogo,
        "duracao": duracao,
        "data": datetime.now().isoformat(),
        "jogadores": [str(j.id) for j in jogadores]
    }

    try:
        dados = carregar_dados()
        dados.append(partida)
        salvar_dados(dados)

        resultado = f"🎮 {jogo} | ⏱️ {duracao}\n\n"
        for idx, jogador in enumerate(jogadores):
            pontos = calcular_pontos(idx, len(jogadores))
            resultado += f"{POSICOES[idx]} {jogador.display_name} | {pontos:+} ponto{'s' if pontos != 1 else ''}\n"

        await interaction.response.send_message(resultado)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao registrar partida: {str(e)}",
            ephemeral=True
        )
        traceback.print_exc()

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

    try:
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
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao corrigir partida: {str(e)}",
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
    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao gerar rankings: {str(e)}",
            ephemeral=True
        )

# ======================
# COMANDOS DE BACKUP E MANUTENÇÃO
# ======================
@bot.tree.command(name="backup", description="🔵 Cria um backup dos dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def criar_backup(interaction: discord.Interaction):
    """Cria um backup manual dos dados"""
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

@bot.tree.command(name="download_backup", description="🔵 Baixa o arquivo de dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def download_backup(interaction: discord.Interaction):
    """Permite baixar o arquivo de dados atual"""
    try:
        if not os.path.exists(DADOS_FILE) or os.path.getsize(DADOS_FILE) == 0:
            return await interaction.response.send_message(
                "❌ Nenhum dado disponível para download",
                ephemeral=True
            )

        await interaction.response.send_message(
            "📤 Aqui está o arquivo de dados atual:",
            file=discord.File(DADOS_FILE),
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao preparar arquivo para download: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="debug_persistencia", description="Mostra informações do sistema de arquivos")
async def debug(interaction: discord.Interaction):
    try:
        backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("dados_backup_")]
        backups.sort(reverse=True)

        info = (
            f"🔧 **Debug - Sistema de Arquivos**\n"
            f"Modo Persistente: `{PERSISTENT_MODE}`\n"
            f"Localização dos dados: `{os.path.abspath(DADOS_FILE)}`\n"
            f"Arquivo existe: `{os.path.exists(DADOS_FILE)}`\n"
            f"Tamanho: `{os.path.getsize(DADOS_FILE) if os.path.exists(DADOS_FILE) else 0} bytes`\n"
            f"Última modificação: `{datetime.fromtimestamp(os.path.getmtime(DADOS_FILE)) if os.path.exists(DADOS_FILE) else 'N/A'}`\n"
            f"\n**Backups disponíveis:**\n"
            f"Total: {len(backups)}\n"
            f"Mais recente: `{backups[0] if backups else 'Nenhum'}`"
        )
        await interaction.response.send_message(info, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao coletar informações: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="reset_data", description="🔴 RESETA todos os dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def reset_data(interaction: discord.Interaction, confirmacao: str):
    """
    ⚠️ Comando perigoso! Requer confirmação explícita
    """
    if confirmacao.lower() != "confirmar-reset-total":
        return await interaction.response.send_message(
            "❌ Confirmação inválida! Use `confirmar-reset-total` para resetar.",
            ephemeral=True
        )

    try:
        # Cria backup antes de resetar
        criar_backup_automatico()

        with open(DADOS_FILE, "w") as f:
            json.dump([], f)

        await interaction.response.send_message(
            "✅ Banco de dados resetado com sucesso! Todos os registros foram apagados.",
            ephemeral=True
        )
        print(f"⚠️ Dados resetados por {interaction.user.name}")
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro ao resetar: {str(e)}",
            ephemeral=True
        )

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
                await enviar_ranking_automatico("semana", "Ranking Semanal", canal)
                criar_backup_automatico()

            # Último dia do mês às 23:59 - Ranking Mensal
            if (now + timedelta(days=1)).month != now.month and now.hour == 23 and now.minute == 59:
                await enviar_ranking_automatico("mes", "Ranking Mensal", canal)
                criar_backup_automatico()

            # 31/12 às 23:59 - Ranking Anual
            if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 59:
                await enviar_ranking_automatico("ano", "Ranking Anual", canal)
                criar_backup_automatico()

            await asyncio.sleep(60)
        except Exception as e:
            print(f"⚠️ Erro no sistema automático: {e}")
            await asyncio.sleep(60)

async def enviar_ranking_automatico(periodo, titulo, canal):
    try:
        dados = carregar_dados()
        jogos = obter_jogos_unicos(dados)

        if not jogos:
            return

        for jogo in jogos:
            partidas = filtrar_partidas_por_periodo_e_jogo(dados, periodo, jogo)
            if partidas:
                mensagem = await criar_embed_ranking(partidas, f"{titulo} - {jogo.capitalize()}")
                await canal.send(mensagem)
    except Exception as e:
        print(f"⚠️ Erro ao enviar ranking automático: {e}")

# ======================
# EVENTOS DO BOT
# ======================
@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como {bot.user.name}")
    print(f"📌 Modo persistente: {'ATIVADO' if PERSISTENT_MODE else 'DESATIVADO'}")
    print(f"📁 Local dos dados: {os.path.abspath(DADOS_FILE)}")
    print(f"🔍 Verificação: Arquivo existe? {os.path.exists(DADOS_FILE)}")
    print(f"📂 Backups: {len(os.listdir(BACKUP_DIR)) if os.path.exists(BACKUP_DIR) else 0} arquivos")

    try:
        await bot.tree.sync()
        print("✅ Comandos sincronizados")
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar comandos: {e}")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="/game e /rank"
    ))
    bot.loop.create_task(enviar_rankings_automaticos())
    print("✅ Tarefas automáticas iniciadas")

# ======================
# INICIALIZAÇÃO
# ======================
if __name__ == "__main__":
    # Verificação final de persistência
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w") as f:
            json.dump([], f)

    # Registra backup automático ao sair
    atexit.register(criar_backup_automatico)

    # Verifica e cria backup na inicialização
    if os.path.exists(DADOS_FILE) and os.path.getsize(DADOS_FILE) > 0:
        criar_backup_automatico()

    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        traceback.print_exc()
        # Garante um backup final antes de sair
        criar_backup_automatico()