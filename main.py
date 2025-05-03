import os
import discord
import json
import asyncio
import shutil
import atexit
import base64
import zlib
from threading import Lock
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from urllib.parse import urlparse
import asyncpg  # Para operações assíncronas

# ======================
# CONFIGURAÇÕES GLOBAIS
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 709705286083936256

# Configuração de persistência
PERSISTENT_MODE = True
USE_ENV_STORAGE = True  # Usar variáveis de ambiente para armazenamento
DATA_ENV_VAR = "GAME_RANKING_DATA"  # Nome da variável de ambiente
DATA_DIR = "data"
DADOS_FILE = os.path.join(DATA_DIR, "dados.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
POSICOES = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
CANAL_RANKING_ID = 1360294622768926901
MINIMO_JOGADORES = 2



# Lock para operações de arquivo
file_lock = Lock()

def get_db_connection():
    db_url = os.getenv('DATABASE_URL')
    result = urlparse(db_url)

    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn

async def get_async_db_connection():
    db_url = os.getenv('DATABASE_URL')
    return await asyncpg.connect(db_url)

async def get_async_db_connection():
    """Conexão assíncrona para operações do bot"""
    db_url = os.getenv('DATABASE_URL')
    return await asyncpg.connect(db_url)

            async def init_db():
                conn = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    # Cria tabela de partidas
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS partidas (
                            id SERIAL PRIMARY KEY,
                            jogo VARCHAR(255) NOT NULL,
                            duracao VARCHAR(50) NOT NULL,
                            data TIMESTAMP NOT NULL
                        )
                    """)

                    # Cria tabela de jogadores_partida
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS jogadores_partida (
                            partida_id INTEGER REFERENCES partidas(id),
                            jogador_id BIGINT NOT NULL,
                            posicao INTEGER NOT NULL,
                            pontos INTEGER NOT NULL,
                            PRIMARY KEY (partida_id, jogador_id)
                        )
                    """)

                    # Cria tabela de pontuação acumulada
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS pontuacao_acumulada (
                            jogador_id BIGINT PRIMARY KEY,
                            pontos INTEGER NOT NULL DEFAULT 0,
                            partidas INTEGER NOT NULL DEFAULT 0,
                            vitorias INTEGER NOT NULL DEFAULT 0,
                            fracassos INTEGER NOT NULL DEFAULT 0
                        )
                    """)

                    conn.commit()
                    cur.close()
                    print("✅ Banco de dados inicializado com sucesso!")
                except Exception as e:
                    print(f"❌ Erro ao inicializar banco de dados: {e}")
                finally:
                    if conn is not None:
                        conn.close()

# ======================
# INICIALIZAÇÃO DO BOT
# ======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ======================
# SISTEMA DE PERSISTÊNCIA MELHORADO
# ======================
def init_persistence():
    """Garante a estrutura de arquivos e migra dados se necessário"""
    try:
        # Cria diretórios se não existirem (para backups locais)
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"📁 Diretório '{DATA_DIR}' criado")

        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"📁 Diretório de backups '{BACKUP_DIR}' criado")

        # Se estivermos usando armazenamento em variável de ambiente
        if USE_ENV_STORAGE:
            # Verifica se já existe dados na variável de ambiente
            env_data = os.getenv(DATA_ENV_VAR)
            if env_data:
                print("✅ Dados encontrados na variável de ambiente")
                # Garante que temos um arquivo local também (para compatibilidade)
                with open(DADOS_FILE, "w") as f:
                    f.write(decompress_data(env_data))
            else:
                print("ℹ️ Nenhum dado encontrado na variável de ambiente")
                # Cria estrutura inicial se não existir
                initial_data = {"partidas": [], "pontuacao": {}}
                with open(DADOS_FILE, "w") as f:
                    json.dump(initial_data, f)
                # Salva na variável de ambiente também
                update_env_storage(initial_data)
        else:
            # Modo tradicional (arquivo local)
            if not os.path.exists(DADOS_FILE):
                with open(DADOS_FILE, "w") as f:
                    json.dump({"partidas": [], "pontuacao": {}}, f)
                print(f"📄 Arquivo '{DADOS_FILE}' criado com estrutura inicial")

    except Exception as e:
        print(f"❌ Erro na inicialização: {str(e)}")
        traceback.print_exc()

def compress_data(data):
    """Comprime os dados para armazenamento eficiente"""
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.b64encode(zlib.compress(json_str.encode('utf-8'))).decode('utf-8')

def decompress_data(compressed_data):
    """Descomprime os dados armazenados"""
    try:
        decompressed = zlib.decompress(base64.b64decode(compressed_data.encode('utf-8'))).decode('utf-8')
        return decompressed
    except:
        # Fallback para dados não comprimidos (backward compatibility)
        return compressed_data

def update_env_storage(data):
    """Atualiza os dados na variável de ambiente (simulado)"""
    if USE_ENV_STORAGE:
        compressed = compress_data(data)
        # No Railway, você precisaria configurar isso manualmente ou via API
        # Aqui estamos apenas simulando para desenvolvimento
        os.environ[DATA_ENV_VAR] = compressed
        # Também salvamos localmente para backup
        with open(DADOS_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    return False

def get_env_storage():
    """Obtém os dados da variável de ambiente"""
    if USE_ENV_STORAGE:
        env_data = os.getenv(DATA_ENV_VAR)
        if env_data:
            try:
                return json.loads(decompress_data(env_data))
            except:
                # Fallback para arquivo local se a variável estiver corrompida
                pass
    return None

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
        dados = carregar_dados()
        if not dados:
            return

        # Backup diário (sobrescreve se já existir para o dia)
        backup_file = os.path.join(BACKUP_DIR, f"dados_backup_{datetime.now().strftime('%Y%m%d')}.json")
        with open(backup_file, "w") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        # Backup com timestamp (mantém histórico)
        timestamp_backup = os.path.join(BACKUP_DIR, f"dados_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(timestamp_backup, "w") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        print(f"✅ Backup automático criado em: {backup_file}")
    except Exception as e:
        print(f"⚠️ Falha ao criar backup automático: {e}")
        traceback.print_exc()

        async def carregar_dados():
            """Carrega todos os dados do PostgreSQL"""
            try:
                conn = await get_async_db_connection()

                # Carrega partidas
                partidas = []
                rows = await conn.fetch("SELECT * FROM partidas ORDER BY data")
                for row in rows:
                    # Carrega jogadores para cada partida
                    jogadores = await conn.fetch(
                        "SELECT jogador_id, posicao FROM jogadores_partida WHERE partida_id = $1 ORDER BY posicao",
                        row['id']
                    )
                    partidas.append({
                        "jogo": row['jogo'],
                        "duracao": row['duracao'],
                        "data": row['data'].isoformat(),
                        "jogadores": [str(j['jogador_id']) for j in jogadores]
                    })

                # Carrega pontuação acumulada
                pontuacao = {}
                rows = await conn.fetch("SELECT * FROM pontuacao_acumulada")
                for row in rows:
                    pontuacao[str(row['jogador_id'])] = row['pontos']

                await conn.close()

                return {
                    "partidas": partidas,
                    "pontuacao": pontuacao
                }
            except Exception as e:
                print(f"❌ Erro ao carregar dados do PostgreSQL: {e}")
                traceback.print_exc()
                return {"partidas": [], "pontuacao": {}}

        async def salvar_partida(partida):
            """Salva uma nova partida no PostgreSQL"""
            try:
                conn = await get_async_db_connection()

                # Insere a partida
                partida_id = await conn.fetchval(
                    "INSERT INTO partidas (jogo, duracao, data) VALUES ($1, $2, $3) RETURNING id",
                    partida["jogo"],
                    partida["duracao"],
                    datetime.fromisoformat(partida["data"])
                )

                # Insere os jogadores e atualiza pontuação
                total_jogadores = len(partida["jogadores"])
                for pos, jogador_id in enumerate(partida["jogadores"]):
                    pontos = calcular_pontos(pos, total_jogadores)

                    # Insere na tabela de relação
                    await conn.execute(
                        "INSERT INTO jogadores_partida (partida_id, jogador_id, posicao, pontos) VALUES ($1, $2, $3, $4)",
                        partida_id,
                        int(jogador_id),
                        pos,
                        pontos
                    )

                    # Atualiza pontuação acumulada
                    await conn.execute("""
                        INSERT INTO pontuacao_acumulada (jogador_id, pontos, partidas, vitorias, fracassos)
                        VALUES ($1, $2, 1, $3, $4)
                        ON CONFLICT (jogador_id) DO UPDATE
                        SET 
                            pontos = pontuacao_acumulada.pontos + EXCLUDED.pontos,
                            partidas = pontuacao_acumulada.partidas + 1,
                            vitorias = pontuacao_acumulada.vitorias + EXCLUDED.vitorias,
                            fracassos = pontuacao_acumulada.fracassos + EXCLUDED.fracassos
                    """, int(jogador_id), pontos, 1 if pos == 0 else 0, 1 if pos == total_jogadores - 1 else 0)

                await conn.close()
                return True
            except Exception as e:
                print(f"❌ Erro ao salvar partida no PostgreSQL: {e}")
                traceback.print_exc()
                return False

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

    partidas = dados.get("partidas", [])
    return [p for p in partidas if (not limite or datetime.fromisoformat(p["data"]) >= limite) and 
                               (not jogo or p["jogo"].lower() == jogo.lower())]

def obter_jogos_unicos(dados):
    partidas = dados.get("partidas", [])
    return sorted({p["jogo"].lower() for p in partidas})

    async def criar_embed_ranking(periodo=None, jogo=None):
        """Gera ranking diretamente do PostgreSQL"""
        try:
            conn = await get_async_db_connection()

            # Filtro de período
            where_clause = "WHERE TRUE"
            params = []

            if periodo == "semana":
                where_clause += " AND p.data >= NOW() - INTERVAL '1 week'"
            elif periodo == "mes":
                where_clause += " AND p.data >= NOW() - INTERVAL '1 month'"
            elif periodo == "ano":
                where_clause += " AND p.data >= NOW() - INTERVAL '1 year'"

            if jogo:
                where_clause += " AND p.jogo ILIKE $1"
                params.append(jogo)

            # Query para obter estatísticas
            query = f"""
            SELECT 
                jp.jogador_id,
                SUM(jp.pontos) as total_pontos,
                COUNT(DISTINCT jp.partida_id) as total_partidas,
                SUM(CASE WHEN jp.posicao = 0 THEN 1 ELSE 0 END) as vitorias,
                SUM(CASE WHEN jp.posicao = (SELECT COUNT(*) - 1 FROM jogadores_partida WHERE partida_id = jp.partida_id) THEN 1 ELSE 0 END) as fracassos
            FROM jogadores_partida jp
            JOIN partidas p ON jp.partida_id = p.id
            {where_clause}
            GROUP BY jp.jogador_id
            ORDER BY total_pontos DESC
            LIMIT 10
            """

            ranking = await conn.fetch(query, *params)

            # Formata a mensagem
            mensagem = f"**🏆 Ranking {'Geral' if not periodo else periodo.capitalize()}"
            mensagem += f" - {jogo.capitalize()}**\n\n" if jogo else "**\n\n"

            for pos, row in enumerate(ranking, start=1):
                try:
                    jogador = await bot.get_guild(GUILD_ID).fetch_member(row['jogador_id'])
                    emoji = POSICOES[pos-1] if pos <= len(POSICOES) else f"{pos}️⃣"
                    media = row['total_pontos'] / row['total_partidas'] if row['total_partidas'] > 0 else 0

                    mensagem += (
                        f"**{emoji} {jogador.display_name} | Total: {row['total_pontos']} pts**\n"
                        f"📊 Partidas: {row['total_partidas']}\n"
                        f"📈 Média: {round(media, 2)} pts/partida\n"
                        f"🥇 Vitórias: {row['vitorias']}\n"
                        f"💀 Fracassos: {row['fracassos']}\n\n"
                    )
                except:
                    continue

            await conn.close()
            return mensagem.strip()
        except Exception as e:
            print(f"❌ Erro ao gerar ranking: {e}")
            traceback.print_exc()
            return "❌ Erro ao gerar ranking"

# ======================
# COMANDOS DE GERENCIAMENTO DE DADOS
# ======================
@bot.tree.command(name="get_data", description="📥 Baixa o arquivo de dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def download_data(interaction: discord.Interaction):
    """Envia o arquivo de dados atual"""
    try:
        # Garante que o diretório e arquivo existam
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        dados = carregar_dados()

        # Garante que o arquivo existe e tem conteúdo
        if not os.path.exists(DADOS_FILE):
            with open(DADOS_FILE, "w") as f:
                json.dump(dados, f, indent=2)

        # Verifica se o arquivo está acessível
        if os.path.getsize(DADOS_FILE) == 0:
            await interaction.response.send_message(
                "⚠️ O arquivo de dados está vazio!",
                ephemeral=True
            )
            return

        # Envia o arquivo
        await interaction.response.send_message(
            content="📤 Aqui está o arquivo de dados atual:",
            file=discord.File(DADOS_FILE),
            ephemeral=True
        )

        print(f"✅ Arquivo de dados enviado para {interaction.user.name}")

    except Exception as e:
        error_msg = f"❌ Erro ao preparar arquivo para download: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        await interaction.response.send_message(
            error_msg,
            ephemeral=True
        )

@bot.tree.command(name="view_data", description="👁️ Mostra os dados atuais (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def view_data(interaction: discord.Interaction):
    """Mostra os dados atuais formatados"""
    try:
        dados = carregar_dados()

        # Formata os dados para exibição
        formatted_data = json.dumps(dados, indent=2, ensure_ascii=False)

        # Divide em partes se for muito grande
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
                # Cria a nova partida
                nova_partida = {
                    "jogo": jogo,
                    "duracao": duracao,
                    "data": datetime.now().isoformat(),
                    "jogadores": [str(j.id) for j in jogadores]
                }

                # Salva no PostgreSQL
                success = await salvar_partida(nova_partida)

                if not success:
                    return await interaction.response.send_message(
                        "❌ Erro ao registrar partida no banco de dados!",
                        ephemeral=True
                    )

                # Monta mensagem de resultado
                resultado = f"🎮 {jogo} | ⏱️ {duracao}\n\n"
                for idx, jogador in enumerate(jogadores):
                    pontos = calcular_pontos(idx, len(jogadores))
                    resultado += f"{POSICOES[idx]} {jogador.display_name} | {pontos:+} ponto{'s' if pontos != 1 else ''}\n"

                # Adiciona pontuação acumulada (agora buscando do PostgreSQL)
                dados = await carregar_dados()
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
            """Mostra o ranking geral de todos os tempos"""
            try:
                await interaction.response.defer()
                titulo = "Ranking Geral" + (f" - {jogo.capitalize()}" if jogo else "")
                mensagem = await criar_embed_ranking(None, jogo)
                await interaction.followup.send(mensagem)
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao gerar ranking geral: {str(e)}",
                    ephemeral=True
                )

        @bot.tree.command(name="rank_semanal", description="Mostra o ranking da semana")
        @app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
        async def rank_semanal(interaction: discord.Interaction, jogo: str = None):
            """Mostra o ranking dos últimos 7 dias"""
            try:
                await interaction.response.defer()
                titulo = "Ranking Semanal" + (f" - {jogo.capitalize()}" if jogo else "")
                mensagem = await criar_embed_ranking("semana", jogo)
                await interaction.followup.send(mensagem)
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao gerar ranking semanal: {str(e)}",
                    ephemeral=True
                )

        @bot.tree.command(name="rank_mensal", description="Mostra o ranking do mês")
        @app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
        async def rank_mensal(interaction: discord.Interaction, jogo: str = None):
            """Mostra o ranking dos últimos 30 dias"""
            try:
                await interaction.response.defer()
                titulo = "Ranking Mensal" + (f" - {jogo.capitalize()}" if jogo else "")
                mensagem = await criar_embed_ranking("mes", jogo)
                await interaction.followup.send(mensagem)
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao gerar ranking mensal: {str(e)}",
                    ephemeral=True
                )

        @bot.tree.command(name="rank_anual", description="Mostra o ranking do ano")
        @app_commands.describe(jogo="(Opcional) Filtra por um jogo específico")
        async def rank_anual(interaction: discord.Interaction, jogo: str = None):
            """Mostra o ranking dos últimos 365 dias"""
            try:
                await interaction.response.defer()
                titulo = "Ranking Anual" + (f" - {jogo.capitalize()}" if jogo else "")
                mensagem = await criar_embed_ranking("ano", jogo)
                await interaction.followup.send(mensagem)
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao gerar ranking anual: {str(e)}",
                    ephemeral=True
                )

        @bot.tree.command(name="rank_all", description="Mostra o ranking de todos os jogos")
        async def rank_all(interaction: discord.Interaction):
            """Mostra rankings separados para cada jogo"""
            try:
                await interaction.response.defer()

                # Obtém a lista de jogos distintos do PostgreSQL
                conn = await get_async_db_connection()
                jogos = await conn.fetch("SELECT DISTINCT jogo FROM partidas ORDER BY jogo")
                await conn.close()

                if not jogos:
                    return await interaction.followup.send("❌ Nenhuma partida registrada ainda!")

                mensagem_final = ""
                for jogo_record in jogos:
                    jogo = jogo_record['jogo']
                    mensagem = await criar_embed_ranking(None, jogo)
                    mensagem_final += f"{mensagem}\n\n"

                # Divide a mensagem se for muito grande
                partes = [mensagem_final[i:i+2000] for i in range(0, len(mensagem_final), 2000)]
                for parte in partes:
                    await interaction.followup.send(parte)

            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao gerar rankings: {str(e)}",
                    ephemeral=True
                )

        @bot.tree.command(name="rank_jogador", description="Mostra estatísticas de um jogador específico")
        @app_commands.describe(jogador="Jogador para ver as estatísticas")
        async def rank_jogador(interaction: discord.Interaction, jogador: discord.Member):
            """Mostra estatísticas detalhadas de um jogador específico"""
            try:
                await interaction.response.defer()

                conn = await get_async_db_connection()

                # Obtém estatísticas gerais
                stats = await conn.fetchrow("""
                    SELECT pontos, partidas, vitorias, fracassos 
                    FROM pontuacao_acumulada 
                    WHERE jogador_id = $1
                """, jogador.id)

                if not stats:
                    return await interaction.followup.send(
                        f"ℹ️ {jogador.display_name} não possui partidas registradas!"
                    )

                # Obtém desempenho por jogo
                jogos = await conn.fetch("""
                    SELECT 
                        p.jogo,
                        COUNT(*) as partidas,
                        SUM(jp.pontos) as pontos,
                        SUM(CASE WHEN jp.posicao = 0 THEN 1 ELSE 0 END) as vitorias,
                        SUM(CASE WHEN jp.posicao = (SELECT COUNT(*) - 1 FROM jogadores_partida WHERE partida_id = p.id) THEN 1 ELSE 0 END) as fracassos
                    FROM jogadores_partida jp
                    JOIN partidas p ON jp.partida_id = p.id
                    WHERE jp.jogador_id = $1
                    GROUP BY p.jogo
                    ORDER BY pontos DESC
                """, jogador.id)

                await conn.close()

                # Formata a mensagem
                mensagem = (
                    f"**📊 Estatísticas de {jogador.display_name}**\n\n"
                    f"🏆 **Pontuação Total:** {stats['pontos']}\n"
                    f"🎮 **Partidas Jogadas:** {stats['partidas']}\n"
                    f"🥇 **Vitórias:** {stats['vitorias']}\n"
                    f"💀 **Fracassos:** {stats['fracassos']}\n"
                    f"📈 **Média de Pontos/Partida:** {round(stats['pontos']/stats['partidas'], 2)}\n\n"
                    f"**🎲 Desempenho por Jogo:**\n"
                )

                for jogo in jogos:
                    mensagem += (
                        f"\n**{jogo['jogo'].capitalize()}:** "
                        f"{jogo['pontos']} pts | "
                        f"{jogo['partidas']} partidas | "
                        f"{jogo['vitorias']}🥇 | "
                        f"{jogo['fracassos']}💀"
                    )

                await interaction.followup.send(mensagem)

            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao gerar estatísticas do jogador: {str(e)}",
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

@bot.tree.command(name="backup_db", description="🔵 Cria backup do banco de dados (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def backup_database(interaction: discord.Interaction):
    """Cria um dump completo do banco de dados"""
    try:
        await interaction.response.defer(ephemeral=True)

        # Nome do arquivo de backup
        backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")

        # Comando para criar o dump (usando pg_dump)
        db_url = os.getenv('DATABASE_URL')
        result = urlparse(db_url)

        cmd = (
            f"pg_dump --dbname=postgresql://{result.username}:{result.password}@"
            f"{result.hostname}:{result.port}/{result.path[1:]} > {backup_file}"
        )

        # Executa o comando
        os.system(cmd)

        # Verifica se o arquivo foi criado
        if os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
            await interaction.followup.send(
                "✅ Backup criado com sucesso!",
                file=discord.File(backup_file),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Falha ao criar backup!",
                ephemeral=True
            )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao criar backup: {str(e)}",
            ephemeral=True
        )
        traceback.print_exc()

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

@bot.tree.command(name="migrate_db", description="🟠 Migra dados do JSON para PostgreSQL (apenas admin)")
@app_commands.default_permissions(administrator=True)
async def migrate_database(interaction: discord.Interaction):
    """Migra todos os dados do arquivo JSON para o PostgreSQL"""
    try:
        await interaction.response.defer(ephemeral=True)

        dados = carregar_dados()
        total = len(dados.get("partidas", []))

        if total == 0:
            return await interaction.followup.send(
                "ℹ️ Nenhum dado para migrar!",
                ephemeral=True
            )

        # Migra cada partida
        migradas = 0
        for partida in dados["partidas"]:
            success = await salvar_partida(partida)
            if success:
                migradas += 1

        await interaction.followup.send(
            f"✅ Migração concluída! {migradas}/{total} partidas migradas",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro durante migração: {str(e)}",
            ephemeral=True
        )
        traceback.print_exc()

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
    await init_db()  # Inicializa o banco de dados
    print(f"✅ Bot conectado como {bot.user.name}")
    print(f"\n✅ Bot conectado como {bot.user.name}")
    print(f"📌 Modo persistente: {'ATIVADO' if PERSISTENT_MODE else 'DESATIVADO'}")
    print(f"📁 Local dos dados: {os.path.abspath(DADOS_FILE)}")
    print(f"🔍 Verificação: Arquivo existe? {os.path.exists(DADOS_FILE)}")
    print(f"📂 Backups: {len(os.listdir(BACKUP_DIR)) if os.path.exists(BACKUP_DIR) else 0} arquivos")

    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados")
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
        # Garante um backup final antes de sair
        criar_backup_automatico()