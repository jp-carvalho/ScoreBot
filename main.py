import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# Intents obrigatórios
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")

DADOS_ARQUIVO = "dados.json"

def carregar_dados():
    if os.path.exists(DADOS_ARQUIVO):
        with open(DADOS_ARQUIVO, "r") as f:
            return json.load(f)
    return {}

def salvar_dados(dados):
    with open(DADOS_ARQUIVO, "w") as f:
        json.dump(dados, f, indent=4)

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"🤖 Bot online como {bot.user}")
    print(f"✅ {len(synced)} comando(s) Slash sincronizado(s): {[cmd.name for cmd in synced]}")

@bot.tree.command(name="registrar", description="Registrar partida (3 a 8 jogadores)")
@app_commands.describe(
    jogo="Nome do jogo",
    duracao="Duração da partida (ex: 1h30)",
    jogadores="Mencione os jogadores em ordem de colocação (ex: @A @B @C)"
)
async def registrar(
    interaction: discord.Interaction,
    jogo: str,
    duracao: str,
    jogadores: str
):
    mencoes = jogadores.split()
    if not (3 <= len(mencoes) <= 8):
        await interaction.response.send_message("❌ Informe entre 3 e 8 jogadores (mencionando cada um com @).")
        return

    membros = []
    for mencao in mencoes:
        if mencao.startswith("<@") and mencao.endswith(">"):
            mencao = mencao.replace("<@", "").replace("!", "").replace(">", "")
            membro = interaction.guild.get_member(int(mencao))
            if membro:
                membros.append(membro)
            else:
                await interaction.response.send_message(f"❌ Jogador com ID {mencao} não encontrado no servidor.")
                return
        else:
            await interaction.response.send_message("❌ Use apenas menções válidas aos jogadores.")
            return

    pontos = [0] * len(membros)
    pontos[0] = 3  # 1º lugar
    if len(membros) >= 2:
        pontos[1] = 1  # 2º lugar
    pontos[-1] = -1  # Último lugar

    dados = carregar_dados()
    if jogo not in dados:
        dados[jogo] = {}

    for jogador, ponto in zip(membros, pontos):
        user_id = str(jogador.id)
        if user_id in dados[jogo]:
            dados[jogo][user_id] += ponto
        else:
            dados[jogo][user_id] = ponto

    salvar_dados(dados)

    emojis = ["🥇", "🥈", "🥉"] + [f"{i+1}️⃣" for i in range(3, len(membros))]
    resposta = f"✅ Partida de **{jogo}** registrada!\n🏆 Pontuação:\n"

    for i, (jogador, ponto) in enumerate(zip(membros, pontos)):
        emoji = emojis[i] if i < len(emojis) else f"{i+1}º"
        resposta += f"{emoji} {jogador.mention} ({'+' if ponto >= 0 else ''}{ponto})\n"

    resposta += f"⏱️ Duração: **{duracao}**"
    await interaction.response.send_message(resposta)

@bot.tree.command(name="ranking", description="Mostra o ranking geral de um jogo")
@app_commands.describe(jogo="Nome do jogo")
async def ranking(interaction: discord.Interaction, jogo: str):
    dados = carregar_dados()
    ranking = dados.get(jogo, {})
    if not ranking:
        await interaction.response.send_message(f"Nenhum dado encontrado para o jogo {jogo}.")
        return

    ranking_ordenado = sorted(ranking.items(), key=lambda item: item[1], reverse=True)
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    texto = f"🏆 **Ranking Geral - {jogo}**\n\n"
    for i, (user_id, pontos) in enumerate(ranking_ordenado[:10]):
        emoji = emojis[i] if i < len(emojis) else f"{i+1}º"
        texto += f"{emoji} <@{user_id}> — **{pontos}** pontos\n"

    await interaction.response.send_message(texto)

bot.run(TOKEN)
