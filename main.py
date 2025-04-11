import discord
from discord.ext import commands
import json
from datetime import datetime, timedelta
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ARQUIVO_PARTIDAS = "partidas.json"
PONTOS = {1: 3, 2: 1}

# Inicializa o arquivo se não existir
if not os.path.exists(ARQUIVO_PARTIDAS):
    with open(ARQUIVO_PARTIDAS, "w") as f:
        json.dump([], f)

def salvar_partida(partida):
    with open(ARQUIVO_PARTIDAS, "r") as f:
        partidas = json.load(f)
    partidas.append(partida)
    with open(ARQUIVO_PARTIDAS, "w") as f:
        json.dump(partidas, f, indent=2)

def carregar_partidas():
    with open(ARQUIVO_PARTIDAS, "r") as f:
        return json.load(f)

def calcular_ranking(periodo=None):
    partidas = carregar_partidas()
    agora = datetime.utcnow()
    pontuacao = {}

    for partida in partidas:
        data = datetime.fromisoformat(partida["data"])
        if periodo == "semanal" and (agora - data).days > 7:
            continue
        elif periodo == "mensal" and (agora - data).days > 30:
            continue
        elif periodo == "anual" and (agora - data).days > 365:
            continue

        for p in partida["posicoes"]:
            pontos = PONTOS.get(p["colocacao"], 0)
            if p["nome"] not in pontuacao:
                pontuacao[p["nome"]] = 0
            pontuacao[p["nome"]] += pontos

    return sorted(pontuacao.items(), key=lambda x: x[1], reverse=True)

@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("!ranking"):
        partes = message.content.split()
        periodo = partes[1] if len(partes) > 1 else None
        ranking = calcular_ranking(periodo)

        if not ranking:
            await message.channel.send("Nenhuma pontuação encontrada para esse período.")
            return

        resposta = f"🏆 Ranking {periodo or 'geral'}:\n"
        for i, (nome, pontos) in enumerate(ranking, start=1):
            resposta += f"{i}. {nome} - {pontos} pontos\n"

        await message.channel.send(resposta)
        return

    if message.content.count("\n") >= 5:
        linhas = message.content.strip().split("\n")
        jogo = linhas[0]
        jogadores = linhas[1:-1]
        duracao = linhas[-1]

        posicoes = []
        for linha in jogadores:
            try:
                colocacao, mencao = linha.strip().split(" ")
                user = mencao.replace("<@", "").replace(">", "").replace("!", "")
                membro = await message.guild.fetch_member(int(user))
                posicoes.append({
                    "id": membro.id,
                    "nome": membro.display_name,
                    "colocacao": int(colocacao)
                })
            except:
                continue

        partida = {
            "jogo": jogo,
            "posicoes": posicoes,
            "duracao": duracao,
            "data": datetime.utcnow().isoformat()
        }

        salvar_partida(partida)
        await message.channel.send(f"Partida de {jogo} registrada com sucesso!")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)