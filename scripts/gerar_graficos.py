"""
Gera os gráficos e a tabela de resultados usados no README.
Execute na raiz do repositório: python scripts/gerar_graficos.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from energia import config, despacho, kpis  # noqa: E402

SAIDA = RAIZ / "docs" / "img"
SAIDA.mkdir(parents=True, exist_ok=True)

COR = {"solar": "#F2A900", "ve": "#1E6FD9", "loja": "#1B1B1B", "rede": "#E50012", "bateria": "#2E9E4F"}
NOMES = {"convencional": "Convencional (só rede)", "solar_basico": "Solar básico", "inteligente": "Inteligente GoodWe"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def sombrear_tarifa(ax):
    ax.axvspan(17, 18, color=COR["solar"], alpha=0.10, lw=0)
    ax.axvspan(18, 21, color=COR["rede"], alpha=0.10, lw=0, label="Ponta (18h–21h)")
    ax.axvspan(21, 22, color=COR["solar"], alpha=0.10, lw=0)


def grafico_fluxo(r, arquivo, titulo):
    s = r["serie"]
    h = [p["passo"] * config.DT_H for p in s]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    sombrear_tarifa(ax)
    ax.fill_between(h, [p["solar_kw"] for p in s], color=COR["solar"], alpha=0.35, label="Geração solar (ET)")
    ax.plot(h, [p["ve_kw"] for p in s], color=COR["ve"], lw=1.8, label="Recarga VEs (HCA G2)")
    ax.plot(h, [p["carga_kw"] for p in s], color=COR["loja"], lw=1, ls="--", label="Loja")
    ax.plot(h, [p["rede_kw"] for p in s], color=COR["rede"], lw=1.8, label="Rede (+ importa)")
    ax.plot(h, [p["bateria_kw"] for p in s], color=COR["bateria"], lw=1.8, label="Bateria Lynx (+ descarrega)")
    ax.axhline(config.DEMANDA_CONTRATADA_KW, color=COR["rede"], ls=":", lw=1)
    ax.text(0.3, config.DEMANDA_CONTRATADA_KW + 1.5, "demanda contratada 50 kW", color=COR["rede"], fontsize=8)
    ax.set(xlim=(0, 24), xticks=range(0, 25, 2), xlabel="Hora do dia", ylabel="kW", title=titulo)
    ax.legend(loc="upper left", fontsize=8, ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=130)
    plt.close(fig)


def grafico_soc(resultados, arquivo):
    fig, ax = plt.subplots(figsize=(10, 3.4))
    sombrear_tarifa(ax)
    for e, cor in (("solar_basico", COR["solar"]), ("inteligente", COR["bateria"])):
        s = resultados[e]["serie"]
        ax.plot([p["passo"] * config.DT_H for p in s], [100 * p["soc"] for p in s], color=cor, lw=2, label=NOMES[e])
    ax.set(xlim=(0, 24), ylim=(0, 100), xticks=range(0, 25, 2), xlabel="Hora do dia", ylabel="SoC (%)",
           title="Estado de carga da bateria Lynx: o algoritmo enche antes da ponta e esvazia na ponta")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=130)
    plt.close(fig)


def grafico_comparativo(tabela, arquivo):
    climas = list(config.CLIMAS)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    metricas = [("custo_energia_rs", "Custo da energia (R$/dia)"),
                ("energia_rede_ponta_kwh", "Rede no horário de ponta (kWh)"),
                ("co2_rede_kg", "CO₂ da energia da rede (kg/dia)")]
    largura = 0.26
    for ax, (chave, titulo) in zip(axes, metricas):
        for i, (e, cor) in enumerate(zip(despacho.ESTRATEGIAS, ("#9AA0A6", COR["solar"], COR["rede"]))):
            ax.bar([x + (i - 1) * largura for x in range(len(climas))],
                   [tabela[c][e][chave] for c in climas], largura, color=cor, label=NOMES[e])
        ax.set_xticks(range(len(climas)), [c.capitalize() for c in climas])
        ax.set_title(titulo, fontsize=10)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(SAIDA / arquivo, dpi=130)
    plt.close(fig)


def tabela_markdown(tabela, ganhos):
    linhas = ["| Clima | Estratégia | Custo (R$/dia) | Custo médio (R$/kWh) | Rede (kWh) | Rede na ponta (kWh) | "
              "Autossuficiência | Recargas completas | CO₂ rede (kg) |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, por_estrategia in tabela.items():
        for e, k in por_estrategia.items():
            linhas.append(f"| {c} | {NOMES[e]} | {k['custo_energia_rs']:.2f} | {k['custo_medio_kwh_rs']:.3f} | "
                          f"{k['energia_rede_kwh']:.0f} | {k['energia_rede_ponta_kwh']:.0f} | {k['autossuficiencia_pct']:.0f}% | "
                          f"{k['sessoes_concluidas']}/{k['sessoes_total']} | {k['co2_rede_kg']:.1f} |")
    linhas += ["", "| Clima | Redução de custo | Redução da rede | Redução na ponta | Economia/ano |",
               "|---|---:|---:|---:|---:|"]
    for c, g in ganhos.items():
        linhas.append(f"| {c} | {g['reducao_custo_pct']:.1f}% | {g['reducao_rede_pct']:.1f}% | "
                      f"{g['reducao_ponta_pct']:.1f}% | R$ {g['economia_ano_rs']:,.0f} |".replace(",", "."))
    return "\n".join(linhas)


if __name__ == "__main__":
    tabela, ganhos = {}, {}
    for clima in config.CLIMAS:
        resultados = {e: despacho.simular(e, clima) for e in despacho.ESTRATEGIAS}
        tabela[clima] = {e: kpis.calcular_kpis(r) for e, r in resultados.items()}
        ganhos[clima] = kpis.comparar(resultados)
        if clima == "ensolarado":
            grafico_fluxo(resultados["convencional"], "fluxo_convencional.png", "Posto convencional: tudo vem da rede, inclusive na ponta")
            grafico_fluxo(resultados["inteligente"], "fluxo_inteligente.png", "Posto inteligente GoodWe: sol de dia, bateria na ponta")
            grafico_soc(resultados, "soc_bateria.png")
    grafico_comparativo(tabela, "comparativo_estrategias.png")
    md = tabela_markdown(tabela, ganhos)
    (RAIZ / "docs" / "RESULTADOS.md").write_text("# Resultados da simulação (semente 42, 24 sessões)\n\n"
                                                 "Gerado por `python scripts/gerar_graficos.py`.\n\n" + md + "\n", encoding="utf-8")
    print(md)
