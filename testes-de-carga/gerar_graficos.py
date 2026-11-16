"""Gera os gráficos do RELATORIO.md a partir dos arquivos *-agregado.json
(saída do analisar.js).

Uso (a partir da pasta testes-de-carga):
    pip install matplotlib

    # Uma medição (padrão: 2026-11-09)
    python gerar_graficos.py
    python gerar_graficos.py 2026-11-15

    # Comparativo: Medição 1 x Medição 2 (informe as duas datas, AAAA-MM-DD,
    # nesta ordem: a primeira é a Medição 1 e a segunda é a Medição 2)
    python gerar_graficos.py 2026-11-09 2026-11-15

Entrada : resultados/<data>/login-agregado.json e cadastro-agregado.json
Saída   : graficos/<data>/*.png                      (uma pasta por medição)
          graficos/comparativo_<data1>_vs_<data2>/   (só no modo comparativo)

Em todos os gráficos de evolução o painel de cima é a concorrência submetida
(VUs simultâneos), e os de baixo são a vazão e a latência, no mesmo eixo de tempo.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

plt.rcParams["font.sans-serif"] = ["Inter", "DejaVu Sans"]  # usa a primeira que existir

BASE = Path(__file__).parent
DATA_PADRAO = "2026-11-09"

SERVICOS = {
    "login": {"titulo": "Login (POST /api/login, leitura)", "cor": "#1f77b4"},
    "cadastro": {"titulo": "Cadastro (POST /api/register, escrita)", "cor": "#d95f02"},
}
COR_P95 = "#c0392b"
COR_ANTES = "#8c8c8c"  # Medição 1 nos gráficos comparativos (a Medição 2 usa a cor do serviço)
COR_TEXTO = "#333333"
LIMITE_P95_MS = 1000  # threshold p(95)<1000 definido nos scripts k6

# Degraus usados nos scripts k6 (STAGES=1,10,50,100): sobe 30 s e mantém 1 min.
DEGRAUS = [1, 10, 50, 100]
INICIO_DEGRAUS = (30, 120, 210, 300)  # início de cada patamar, em segundos
# Deslocamento (s) da caixa de resultados de cada patamar nos gráficos de cenário, para
# que as caixas de 10 e 50 VUs não encostem na rampa de subida seguinte.
AJUSTE_CAIXA = {1: 0, 10: -10, 50: -10, 100: 0}


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
class Medicao:
    """Uma medição: a pasta de entrada, a de saída e os dados dos dois serviços."""

    def __init__(self, data):
        self.data = data
        self.saida = BASE / "graficos" / data
        entrada = BASE / "resultados" / data
        self.dados = {}
        for nome in SERVICOS:
            caminho = entrada / f"{nome}-agregado.json"
            if not caminho.exists():
                sys.exit(f"Não encontrei {caminho}. Rode antes: node analisar.js (veja o README).")
            with open(caminho, encoding="utf-8") as f:
                self.dados[nome] = json.load(f)


def data_br(data):
    """2026-11-09 -> 09/11/2026"""
    ano, mes, dia = data.split("-")
    return f"{dia}/{mes}/{ano}"


def br(valor, casas=0):
    """Formato brasileiro: 1.234,5"""
    txt = f"{valor:,.{casas}f}"
    return txt.replace(",", "#").replace(".", ",").replace("#", ".")


def sombrear_degraus(ax, rotular=False):
    """Marca no gráfico os períodos em que os VUs ficam estáveis (patamares)."""
    for i, (ini, vus) in enumerate(zip(INICIO_DEGRAUS, DEGRAUS)):
        fim = ini + 60
        if i % 2 == 0:
            ax.axvspan(ini, fim, color="#000000", alpha=0.04, lw=0)
        if rotular:
            ax.text((ini + fim) / 2, 1.02, f"{vus} VU{'s' if vus > 1 else ''}",
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=8, color="#555")


def serie(dados, janela, campo):
    # Descarta as janelas finais com 0 VUs: são só a "cauda" do teste (poucas
    # requisições) e fariam a vazão parecer despencar sem motivo real.
    pts = [p for p in dados[f"janela_{janela}s"] if p["vus"] > 0]
    return [p["t_inicio_s"] + janela / 2 for p in pts], [p[campo] for p in pts]


def estilo(ax, ylabel, tempo=False):
    if tempo:
        ax.set_xlim(0, 392)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


def titulo_painel(ax, texto):
    ax.set_title(texto, loc="left", fontsize=10.5, fontweight="bold")


def salvar(fig, saida, nome):
    saida.mkdir(parents=True, exist_ok=True)
    caminho = saida / nome
    fig.savefig(caminho, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("gerado:", caminho.relative_to(BASE))


def tabela_por_vus(dados):
    return {l["vus"]: l for l in dados["por_vus"] if l["vus"] in DEGRAUS and l["segundos"] > 10}


def rotular_patamares(ax, deslocamento=4):
    for ini, vus in zip(INICIO_DEGRAUS, DEGRAUS):
        ax.text(ini + 30, vus + deslocamento, f"{vus}", ha="center", va="bottom", fontsize=9,
                fontweight="bold", color=COR_TEXTO)


# --------------------------------------------------------------------------- #
# Gráficos de UMA medição
# --------------------------------------------------------------------------- #
def grafico_evolucao(m, nome):
    """3 painéis com o mesmo eixo de tempo: concorrência, vazão e latência."""
    cfg, dados = SERVICOS[nome], m.dados[nome]
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 9.4), sharex=True)
    fig.suptitle(f"{cfg['titulo']} - evolução durante o teste ({data_br(m.data)})", y=0.998, fontsize=13)

    # 1) Concorrência submetida ao longo do tempo
    x, y = serie(dados, 1, "vus")
    a1.fill_between(x, y, step="mid", color="#555", alpha=0.18)
    a1.step(x, y, where="mid", color="#333", lw=1.8)
    estilo(a1, "VUs simultâneos", tempo=True)
    a1.set_ylim(0, 112)
    titulo_painel(a1, "Concorrência submetida ao longo do tempo")
    sombrear_degraus(a1)
    rotular_patamares(a1)

    # 2) Vazão
    x1, y1 = serie(dados, 1, "req_por_s")
    x10, y10 = serie(dados, 10, "req_por_s")
    a2.plot(x1, y1, color=cfg["cor"], alpha=0.25, lw=0.9, label="janela de 1 s")
    a2.plot(x10, y10, color=cfg["cor"], lw=2, marker="o", ms=3, label="janela de 10 s")
    estilo(a2, "req/s", tempo=True)
    a2.set_ylim(bottom=0)
    titulo_painel(a2, "Vazão (requisições por segundo)")
    a2.legend(loc="upper left", frameon=False)
    sombrear_degraus(a2)

    # 3) Latência
    xm, ym = serie(dados, 5, "latencia_media_ms")
    xp, yp = serie(dados, 5, "latencia_p95_ms")
    a3.plot(xm, ym, color=cfg["cor"], lw=2, marker="o", ms=3, label="média (janela de 5 s)")
    a3.plot(xp, yp, color=COR_P95, lw=1.8, ls="--", marker="s", ms=3, label="p95 (janela de 5 s)")
    estilo(a3, "ms", tempo=True)
    a3.set_xlabel("Tempo desde o início do teste (s)")
    a3.set_ylim(bottom=0)
    titulo_painel(a3, "Latência (tempo de resposta)")
    a3.legend(loc="upper left", frameon=False)
    sombrear_degraus(a3)

    fig.tight_layout()
    salvar(fig, m.saida, f"{nome}_evolucao.png")


def grafico_comparacao_vus(m):
    """Latência e vazão por nível de concorrência, os dois serviços lado a lado.
    O eixo X é categórico (1, 10, 50, 100 VUs igualmente espaçados)."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8))
    pos = list(range(len(DEGRAUS)))
    maior_vazao = 0
    for nome, dados in m.dados.items():
        cfg = SERVICOS[nome]
        t = tabela_por_vus(dados)
        linhas = [t[v] for v in DEGRAUS]
        a1.plot(pos, [l["latencia_media_ms"] for l in linhas], color=cfg["cor"], marker="o", lw=2,
                label=f"{nome} - média")
        a1.plot(pos, [l["latencia_p95_ms"] for l in linhas], color=cfg["cor"], marker="s", lw=1.6,
                ls="--", label=f"{nome} - p95")
        a2.plot(pos, [l["req_por_s"] for l in linhas], color=cfg["cor"], marker="o", lw=2, label=nome)
        for x, l in zip(pos, linhas):
            a2.annotate(br(l["req_por_s"]), (x, l["req_por_s"]), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color=COR_TEXTO)
        maior_vazao = max(maior_vazao, max(l["req_por_s"] for l in linhas))
    for ax, yl, tit in ((a1, "Latência (ms)", "Latência x concorrência"),
                        (a2, "Vazão (req/s)", "Vazão x concorrência")):
        ax.set_xticks(pos)
        ax.set_xticklabels([str(v) for v in DEGRAUS])
        ax.set_xlim(-0.3, len(DEGRAUS) - 0.7)
        ax.set_xlabel("Usuários virtuais simultâneos (VUs)")
        ax.set_title(f"{tit} ({data_br(m.data)})", fontsize=11)
        estilo(ax, yl)
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, loc="upper left")
    a2.set_ylim(0, maior_vazao * 1.12)  # antes era fixo em 4400 e cortava o gráfico se a vazão passasse disso
    fig.tight_layout()
    salvar(fig, m.saida, "comparacao_por_vus.png")


def grafico_comparacao_tempo(m):
    """Os dois serviços sobrepostos no tempo: concorrência, vazão e latência."""
    fig, (a0, a1, a2) = plt.subplots(3, 1, figsize=(11, 9.4), sharex=True)
    fig.suptitle(f"Login x Cadastro - comparação no tempo ({data_br(m.data)})", y=0.998, fontsize=13)
    estilos_vus = {"login": dict(lw=3.2, alpha=0.9, ls="-"), "cadastro": dict(lw=1.6, alpha=1, ls=(0, (4, 3)))}
    for nome, dados in m.dados.items():
        cfg = SERVICOS[nome]
        x, y = serie(dados, 1, "vus")
        a0.step(x, y, where="mid", color=cfg["cor"], label=f"{nome}", **estilos_vus[nome])
        x, y = serie(dados, 10, "req_por_s")
        a1.plot(x, y, color=cfg["cor"], lw=2, marker="o", ms=3, label=nome)
        x, y = serie(dados, 10, "latencia_media_ms")
        a2.plot(x, y, color=cfg["cor"], lw=2, marker="o", ms=3, label=f"{nome} - média")
        x, y = serie(dados, 10, "latencia_p95_ms")
        a2.plot(x, y, color=cfg["cor"], lw=1.4, ls="--", alpha=0.8, label=f"{nome} - p95")
    estilo(a0, "VUs simultâneos", tempo=True)
    a0.set_ylim(0, 112)
    titulo_painel(a0, "Concorrência submetida ao longo do tempo (mesmo cenário nos dois testes)")
    a0.legend(frameon=False, loc="upper left", ncol=2)
    estilo(a1, "req/s", tempo=True)
    titulo_painel(a1, "Vazão (janelas de 10 s)")
    estilo(a2, "ms", tempo=True)
    titulo_painel(a2, "Latência (janelas de 10 s)")
    a2.set_xlabel("Tempo desde o início do teste (s)")
    for ax in (a1, a2):
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, ncol=2 if ax is a2 else 1, loc="upper left" if ax is a2 else "lower right")
    for ax in (a0, a1, a2):
        sombrear_degraus(ax)
    fig.tight_layout()
    salvar(fig, m.saida, "comparacao_evolucao.png")


def grafico_resumo(m):
    """Barras com os indicadores globais (p95 contra o limite do SLA)."""
    d = m.dados
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    nomes = list(d)
    cores = [SERVICOS[n]["cor"] for n in nomes]
    p95 = [d[n]["resumo"]["latencia_p95_ms"] for n in nomes]
    barras = a1.bar(nomes, p95, color=cores, width=0.5)
    a1.axhline(LIMITE_P95_MS, color=COR_P95, ls="--", lw=1.4)
    a1.text(0.5, LIMITE_P95_MS * 0.93, f"limite do SLA: p95 < {LIMITE_P95_MS} ms", ha="center",
            va="top", fontsize=8, color=COR_TEXTO, transform=a1.get_yaxis_transform())
    a1.set_ylim(0, LIMITE_P95_MS * 1.1)
    a1.bar_label(barras, labels=[f"{br(v, 1)} ms" for v in p95], padding=3, fontsize=9)
    a1.set_title(f"Latência p95 no teste inteiro ({data_br(m.data)})", fontsize=11)
    estilo(a1, "ms")
    vaz = [d[n]["resumo"]["requisicoes"] / d[n]["duracao_s"] for n in nomes]
    barras = a2.bar(nomes, vaz, color=cores, width=0.5)
    a2.bar_label(barras, labels=[f"{br(v)} req/s" for v in vaz], padding=3, fontsize=9)
    a2.set_title(f"Vazão média no teste inteiro ({data_br(m.data)})", fontsize=11)
    estilo(a2, "req/s")
    a2.set_ylim(0, max(vaz) * 1.15)
    fig.tight_layout()
    salvar(fig, m.saida, "comparacao_resumo.png")


def grafico_cenario(m):
    """O cenário de concorrência submetido ao longo do tempo (igual nos dois
    testes), com o resultado medido em cada patamar escrito sobre ele."""
    d = m.dados
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    x, y = serie(d["login"], 1, "vus")  # o perfil de VUs é idêntico nos dois testes
    ax.fill_between(x, y, step="mid", color="#555", alpha=0.15)
    ax.step(x, y, where="mid", color="#222", lw=2.2)
    sombrear_degraus(ax)
    por_vus = {n: tabela_por_vus(v) for n, v in d.items()}

    for ini, vus in zip(INICIO_DEGRAUS, DEGRAUS):
        lg, cd = por_vus["login"][vus], por_vus["cadastro"][vus]
        txt = (f"{vus} VU{'s' if vus > 1 else ''}\n"
               f"Login: {br(lg['req_por_s'])} req/s | {br(lg['latencia_media_ms'], 1)} ms\n"
               f"Cadastro: {br(cd['req_por_s'])} req/s | {br(cd['latencia_media_ms'], 1)} ms")
        ax.text(ini + 30 + AJUSTE_CAIXA[vus], vus + 5, txt, ha="center", va="bottom", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", lw=0.8))
    # nomes das fases de subida/descida, no topo, para não ficarem sobre a curva
    for t, rot in ((15, "subida 0 -> 1"), (105, "subida 1 -> 10"), (195, "subida 10 -> 50"),
                   (285, "subida 50 -> 100"), (375, "descida 100 -> 0")):
        ax.text(t, 141, rot, ha="center", va="center", fontsize=7.5, color="#777")
    ax.set_xlim(0, 392)
    ax.set_ylim(0, 150)
    ax.set_xlabel("Tempo desde o início do teste (s)")
    ax.set_ylabel("Usuários virtuais simultâneos (VUs)")
    ax.set_title(f"Cenário de concorrência submetido ao longo do tempo ({data_br(m.data)})\n"
                 "Mesma rampa nos testes de Login e de Cadastro; sem tempo de espera entre requisições",
                 fontsize=11.5)
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    salvar(fig, m.saida, "concorrencia_cenario.png")


# --------------------------------------------------------------------------- #
# Gráficos COMPARATIVOS (Medição 1 x Medição 2)
# Convenção de cores: Medição 1 = cinza; Medição 2 = cor do serviço.
# Linha cheia = média; tracejada = p95.
# --------------------------------------------------------------------------- #
def anotar_paradas(ax, dados, rotulo, deslocamentos, limite_ms=1000):
    """Marca as janelas de 10 s cuja latência máxima passou de `limite_ms` (as
    "paradas"). `deslocamentos` é a lista de posições (em pontos) do texto, na
    ordem em que as paradas aparecem no tempo."""
    paradas = [p for p in dados["janela_10s"] if p["latencia_max_ms"] >= limite_ms]
    for p, desloc in zip(paradas, deslocamentos):
        x = p["t_inicio_s"] + 5
        ax.annotate(f"{rotulo}: máx. {br(p['latencia_max_ms'])} ms", (x, p["latencia_media_ms"]),
                    xytext=desloc, textcoords="offset points", fontsize=8, color=COR_TEXTO,
                    ha="center", arrowprops=dict(arrowstyle="-", color="#777", lw=0.8))


def grafico_comparativo_tempo(m1, m2, nome, saida):
    """Concorrência submetida, vazão e latência ao longo do tempo, com as duas
    medições do mesmo serviço sobrepostas no mesmo eixo de tempo."""
    cfg = SERVICOS[nome]
    d1, d2 = m1.dados[nome], m2.dados[nome]
    r1, r2 = f"Medição 1 ({data_br(m1.data)})", f"Medição 2 ({data_br(m2.data)})"
    fig, (a0, a1, a2) = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    fig.suptitle(f"{cfg['titulo']} - Medição 1 x Medição 2 ao longo do tempo", y=0.998, fontsize=13)

    # 1) Concorrência: o mesmo cenário nas duas medições (as curvas coincidem)
    x, y = serie(d1, 1, "vus")
    a0.step(x, y, where="mid", color=COR_ANTES, lw=5, alpha=0.55, label=r1)
    x, y = serie(d2, 1, "vus")
    a0.step(x, y, where="mid", color=cfg["cor"], lw=1.6, label=r2)
    estilo(a0, "VUs simultâneos", tempo=True)
    a0.set_ylim(0, 118)
    titulo_painel(a0, "Concorrência submetida ao longo do tempo (mesmo cenário nas duas medições)")
    a0.legend(frameon=False, loc="upper left")
    rotular_patamares(a0)

    # 2) Vazão: linha forte = janela de 10 s; linha clara = janela de 1 s
    for d, cor, lw, rot in ((d1, COR_ANTES, 1.8, r1), (d2, cfg["cor"], 2.2, r2)):
        x1, y1 = serie(d, 1, "req_por_s")
        a1.plot(x1, y1, color=cor, alpha=0.2, lw=0.8)
        x10, y10 = serie(d, 10, "req_por_s")
        a1.plot(x10, y10, color=cor, lw=lw, marker="o", ms=3, label=rot)
    estilo(a1, "req/s", tempo=True)
    a1.set_ylim(bottom=0)
    titulo_painel(a1, "Vazão (linha forte: janelas de 10 s; linha clara: janelas de 1 s)")
    a1.legend(frameon=False, loc="upper left")

    # 3) Latência: média (cheia) e p95 (tracejada), janelas de 10 s
    for d, cor, lw, rot in ((d1, COR_ANTES, 1.8, r1), (d2, cfg["cor"], 2.2, r2)):
        x, y = serie(d, 10, "latencia_media_ms")
        a2.plot(x, y, color=cor, lw=lw, marker="o", ms=3, label=f"{rot} - média")
        x, y = serie(d, 10, "latencia_p95_ms")
        a2.plot(x, y, color=cor, lw=1.4, ls=(0, (4, 2)), alpha=0.9, label=f"{rot} - p95")
    estilo(a2, "ms", tempo=True)
    a2.set_xlabel("Tempo desde o início do teste (s)")
    a2.set_ylim(bottom=0)
    titulo_painel(a2, "Latência (janelas de 10 s)")
    a2.legend(frameon=False, loc="upper left", ncol=2)
    anotar_paradas(a2, d1, "Medição 1", [(-70, 38)])
    anotar_paradas(a2, d2, "Medição 2", [(-75, 55), (0, 50)])

    for ax in (a0, a1, a2):
        sombrear_degraus(ax)
    fig.tight_layout()
    salvar(fig, saida, f"{nome}_comparativo_tempo.png")


def grafico_comparativo_por_vus(m1, m2, nome, saida):
    """Vazão e latência por nível de concorrência: Medição 1 x Medição 2."""
    cfg = SERVICOS[nome]
    t1, t2 = tabela_por_vus(m1.dados[nome]), tabela_por_vus(m2.dados[nome])
    r1, r2 = f"Medição 1 ({data_br(m1.data)})", f"Medição 2 ({data_br(m2.data)})"
    metricas = (("req_por_s", "Vazão (req/s)", "Vazão", 0),
                ("latencia_media_ms", "Latência média (ms)", "Latência média", 1),
                ("latencia_p95_ms", "Latência p95 (ms)", "Latência p95", 1))
    fig, eixos = plt.subplots(1, 3, figsize=(14, 4.8))
    fig.suptitle(f"{cfg['titulo']} - por nível de concorrência", y=1.0, fontsize=13)
    pos = list(range(len(DEGRAUS)))
    larg = 0.36
    for ax, (campo, ylabel, titulo, casas) in zip(eixos, metricas):
        v1 = [t1[v][campo] for v in DEGRAUS]
        v2 = [t2[v][campo] for v in DEGRAUS]
        b1 = ax.bar([p - 0.19 for p in pos], v1, larg, color=COR_ANTES, label=r1)
        b2 = ax.bar([p + 0.19 for p in pos], v2, larg, color=cfg["cor"], label=r2)
        ax.bar_label(b1, labels=[br(v, casas) for v in v1], padding=2, fontsize=7.5, color=COR_TEXTO)
        ax.bar_label(b2, labels=[br(v, casas) for v in v2], padding=2, fontsize=7.5, color=COR_TEXTO)
        ax.set_xticks(pos)
        ax.set_xticklabels([str(v) for v in DEGRAUS])
        ax.set_xlabel("Usuários virtuais simultâneos (VUs)")
        ax.set_title(f"{titulo} x concorrência", fontsize=11)
        estilo(ax, ylabel)
        ax.set_ylim(0, max(v1 + v2) * 1.14)
    eixos[0].legend(frameon=False, loc="upper left", fontsize=8.5)
    fig.tight_layout()
    salvar(fig, saida, f"{nome}_comparativo_por_vus.png")


def grafico_comparativo_resumo(m1, m2, saida):
    """Indicadores globais do teste inteiro, Medição 1 x Medição 2, dos dois serviços."""
    nomes = list(SERVICOS)
    indicadores = (("vazao", "Vazão média (req/s)", 0), ("latencia_media_ms", "Latência média (ms)", 1),
                   ("latencia_p95_ms", "Latência p95 (ms)", 1), ("latencia_max_ms", "Latência máxima (ms)", 0))

    def valor(m, nome, campo):
        d = m.dados[nome]
        if campo == "vazao":  # mesma conta de grafico_resumo: requisições / duração medida
            return d["resumo"]["requisicoes"] / d["duracao_s"]
        return d["resumo"][campo]

    fig, eixos = plt.subplots(1, 4, figsize=(15.5, 4.6))
    fig.suptitle("Indicadores globais do teste inteiro: Medição 1 x Medição 2", y=1.02, fontsize=13)
    larg = 0.36
    for ax, (campo, titulo, casas) in zip(eixos, indicadores):
        for i, nome in enumerate(nomes):
            v1, v2 = valor(m1, nome, campo), valor(m2, nome, campo)
            b1 = ax.bar(i - 0.19, v1, larg, color=COR_ANTES)
            b2 = ax.bar(i + 0.19, v2, larg, color=SERVICOS[nome]["cor"])
            ax.bar_label(b1, labels=[br(v1, casas)], padding=2, fontsize=8, color=COR_TEXTO)
            ax.bar_label(b2, labels=[br(v2, casas)], padding=2, fontsize=8, color=COR_TEXTO)
        ax.set_xticks(range(len(nomes)))
        ax.set_xticklabels([n.capitalize() for n in nomes])
        ax.set_title(titulo, fontsize=11)
        estilo(ax, "")
        ax.set_ylim(0, ax.get_ylim()[1] * 1.1)
    legenda = [Patch(color=COR_ANTES, label=f"Medição 1 ({data_br(m1.data)})")]
    legenda += [Patch(color=SERVICOS[n]["cor"], label=f"Medição 2 - {n.capitalize()} ({data_br(m2.data)})")
                for n in nomes]
    fig.legend(handles=legenda, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout()
    salvar(fig, saida, "comparativo_resumo.png")


def variacao_pct(antes, depois):
    """Variação percentual da Medição 2 em relação à Medição 1, com sinal (ex.: +38%)."""
    v = (depois / antes - 1) * 100
    return f"{v:+.0f}%".replace("-", "\u2212")


def grafico_comparativo_cenario(m1, m2, saida):
    """O cenário de concorrência submetido (idêntico nas duas medições) no topo e,
    abaixo, no MESMO eixo de tempo, a Medição 1 e a Medição 2 como duas linhas:
    vazão e latência média, uma coluna para o Login e outra para o Cadastro.
    O rótulo sobre cada patamar é a variação da Medição 2 em relação à Medição 1
    (média do patamar, a mesma tabela usada no RELATORIO.md)."""
    r1, r2 = f"Medição 1 ({data_br(m1.data)})", f"Medição 2 ({data_br(m2.data)})"
    fig = plt.figure(figsize=(13.5, 9.6))
    grade = fig.add_gridspec(3, 2, height_ratios=[0.75, 1.5, 1.5], hspace=0.34, wspace=0.12)
    a0 = fig.add_subplot(grade[0, :])
    eixos = [[fig.add_subplot(grade[i, j], sharex=a0) for j in range(2)] for i in (1, 2)]
    fig.suptitle(f"Cenário de concorrência: {r1} \u00d7 {r2}", y=0.965, fontsize=14)

    # 1) Cenário: a rampa de VUs (uma só curva, porque o cenário é o mesmo nas duas medições)
    x, y = serie(m2.dados["login"], 1, "vus")
    a0.fill_between(x, y, step="mid", color="#555", alpha=0.15)
    a0.step(x, y, where="mid", color="#222", lw=2.2)
    estilo(a0, "VUs simultâneos", tempo=True)
    a0.set_ylim(0, 125)
    titulo_painel(a0, "Concorrência submetida ao longo do tempo (o mesmo cenário nas duas medições)")
    sombrear_degraus(a0)
    rotular_patamares(a0)
    for t, rot in ((15, "subida 0 \u2192 1"), (105, "subida 1 \u2192 10"), (195, "subida 10 \u2192 50"),
                   (285, "subida 50 \u2192 100"), (375, "descida 100 \u2192 0")):
        a0.text(t, 118, rot, ha="center", va="center", fontsize=7.5, color="#777")

    # 2) Resultados: duas linhas (Medição 1 = cinza, Medição 2 = cor do serviço)
    t1 = {n: tabela_por_vus(m1.dados[n]) for n in SERVICOS}
    t2 = {n: tabela_por_vus(m2.dados[n]) for n in SERVICOS}
    paineis = (("req_por_s", "Vazão (req/s)", "Vazão"),
               ("latencia_media_ms", "Latência média (ms)", "Latência média"))
    for linha, (campo, ylabel, titulo) in enumerate(paineis):
        for col, nome in enumerate(SERVICOS):
            ax, cfg = eixos[linha][col], SERVICOS[nome]
            d1, d2 = m1.dados[nome], m2.dados[nome]
            xa, ya = serie(d1, 10, campo)
            xb, yb = serie(d2, 10, campo)
            ax.plot(xa, ya, color=COR_ANTES, lw=2, marker="s", ms=3.2, label="Medição 1")
            ax.plot(xb, yb, color=cfg["cor"], lw=2.2, marker="o", ms=3.5, label="Medição 2")
            estilo(ax, ylabel if col == 0 else "", tempo=True)
            ax.set_ylim(0, max(ya + yb) * 1.28)
            ax.set_title(f"{nome.capitalize()} - {titulo}", loc="left", fontsize=10.5, fontweight="bold")
            sombrear_degraus(ax)
            # legenda na linha do título (à direita), para não cobrir os rótulos dos patamares
            ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2,
                      fontsize=8.5, handlelength=1.6, columnspacing=1.2, borderaxespad=0.2)
            # variação de cada patamar, no topo da faixa correspondente
            for ini, vus in zip(INICIO_DEGRAUS, DEGRAUS):
                ax.text(ini + 30, 0.965, variacao_pct(t1[nome][vus][campo], t2[nome][vus][campo]),
                        transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=9,
                        fontweight="bold", color=COR_TEXTO,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#ccc", lw=0.7))
            if linha == 1:
                ax.set_xlabel("Tempo desde o início do teste (s)")
            else:
                ax.tick_params(labelbottom=False)
    a0.tick_params(labelbottom=False)
    fig.text(0.5, 0.012,
             "Linhas: janelas de 10 s. Rótulo sobre cada patamar: variação da Medição 2 em relação à Medição 1 "
             "(média do patamar). Vazão: quanto maior, melhor. Latência: quanto menor, melhor.",
             ha="center", va="bottom", fontsize=9, color="#555")
    salvar(fig, saida, "comparativo_concorrencia_cenario.png")


# --------------------------------------------------------------------------- #
def gerar_medicao(m):
    for nome in SERVICOS:
        grafico_evolucao(m, nome)
    grafico_comparacao_vus(m)
    grafico_cenario(m)
    grafico_comparacao_tempo(m)
    grafico_resumo(m)


def gerar_comparativo(m1, m2):
    saida = BASE / "graficos" / f"comparativo_{m1.data}_vs_{m2.data}"
    for nome in SERVICOS:
        grafico_comparativo_tempo(m1, m2, nome, saida)
        grafico_comparativo_por_vus(m1, m2, nome, saida)
    grafico_comparativo_resumo(m1, m2, saida)
    grafico_comparativo_cenario(m1, m2, saida)


if __name__ == "__main__":
    datas = sys.argv[1:] or [DATA_PADRAO]
    if len(datas) > 2:
        sys.exit("Uso: python gerar_graficos.py [data]  ou  python gerar_graficos.py <data1> <data2>")
    medicoes = [Medicao(d) for d in datas]
    for med in medicoes:
        gerar_medicao(med)
    if len(medicoes) == 2:
        gerar_comparativo(*medicoes)
