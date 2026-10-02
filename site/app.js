"use strict";
const REPO = "GloedenJoao/profissional";
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (v, casas = 2) => (v == null ? "—" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(casas).replace(".", ",")}%`);
const pctSimples = (v, casas = 0) => (v == null ? "—" : `${(v * 100).toFixed(casas).replace(".", ",")}%`);
const brl = (v) => (v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }));
const mi = (v) => (v == null ? "—" : `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} mi`);
const num = (v, casas = 2) => (v == null ? "—" : Number(v).toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: Math.min(casas, 2) }));
const dataBR = (iso) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const sinal = (v) => (v == null ? "" : v >= 0 ? "pos" : "neg");

const NOME_AREA = { extracao: "Extração", dashboards: "Dashboards", executivos: "Executivos", fundo: "Fundo" };
const SEV = { alta: "ruim", media: "aviso", baixa: "info" };
const TIPO_INC = { atraso: "aviso", fora_do_ar: "ruim", mudanca_formato: "ruim", falha_real: "ruim" };

let P = null;

async function carregar() {
  for (const url of ["painel.json", "../dados/painel.json"]) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (r.ok) return r.json();
    } catch (_) { /* tenta o próximo */ }
  }
  throw new Error("painel.json não encontrado");
}

// ------------------------------------------------------------------ gráficos (SVG puro)
function grafico(series, { altura = 180, formato = (v) => num(v), zero = false } = {}) {
  // a largura do SVG acompanha o cartão, para o texto ficar sempre em 11px reais
  const W = Math.max(300, Math.min(1000, ($("#conteudo").clientWidth || 640) - 34)), H = altura, m = { t: 10, r: 10, b: 22, l: 52 };
  const pts = series.flatMap((s) => s.pontos.filter((p) => p[1] != null));
  if (pts.length < 2) return `<p class="vazio">Histórico ainda curto para o gráfico.</p>`;
  const xs = [...new Set(pts.map((p) => p[0]))].sort();
  let lo = Math.min(...pts.map((p) => p[1])), hi = Math.max(...pts.map((p) => p[1]));
  if (zero) lo = Math.min(lo, 0);
  if (hi === lo) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const x = (d) => m.l + (xs.indexOf(d) / Math.max(1, xs.length - 1)) * (W - m.l - m.r);
  const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const ticks = [lo + pad, (lo + hi) / 2, hi - pad];
  let svg = `<svg class="grafico" viewBox="0 0 ${W} ${H}" role="img">`;
  for (const t of ticks) svg += `<line class="eixo" x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${m.l - 6}" y="${y(t) + 4}" text-anchor="end">${esc(formato(t))}</text>`;
  const idx = [0, Math.floor((xs.length - 1) / 2), xs.length - 1];
  for (const i of idx) svg += `<text x="${x(xs[i])}" y="${H - 4}" text-anchor="${i === 0 ? "start" : i === xs.length - 1 ? "end" : "middle"}">${dataBR(xs[i]).slice(0, 5)}</text>`;
  series.forEach((s, k) => {
    const d = s.pontos.filter((p) => p[1] != null).map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
    svg += `<path d="${d}" fill="none" stroke="var(--serie-${k + 1})" stroke-width="${k ? 1.6 : 2.2}" ${s.tracejado ? 'stroke-dasharray="5 4"' : ""} stroke-linejoin="round" stroke-linecap="round"/>`;
    const u = s.pontos.filter((p) => p[1] != null).at(-1);
    if (u) svg += `<circle cx="${x(u[0])}" cy="${y(u[1])}" r="3" fill="var(--serie-${k + 1})"/>`;
  });
  svg += "</svg>";
  const leg = series.length > 1 ? `<div class="legenda">${series.map((s, k) => `<span><i style="background:var(--serie-${k + 1})"></i>${esc(s.nome)}</span>`).join("")}</div>` : "";
  return svg + leg;
}

const kpi = (rot, val, det = "", cls = "") => `<div class="cartao kpi"><div class="rot">${rot}</div><div class="val ${cls}">${val}</div><div class="det">${det}</div></div>`;
const selo = (txt, cls) => `<span class="selo ${cls || ""}">${esc(txt)}</span>`;
const linkIssue = (i) => (i ? ` <a href="${esc(i.url)}">#${i.numero}</a>` : "");

// ------------------------------------------------------------------ abas
function hoje() {
  const r = P.resumo, h = P.historico;
  const excesso = r.retorno_total - r.cdi_total;
  const alertas = P.alertas.length
    ? `<ul class="lista">${P.alertas.map((a) => `<li>${selo(a.sev, SEV[a.sev])}<div><strong>${esc(a.titulo)}</strong>${linkIssue(a.issue)}<div class="det">${esc(NOME_AREA[a.area] || a.area)} · desde ${dataBR(a.aberto_em)}${a.detalhe ? " · " + esc(a.detalhe) : ""}</div></div></li>`).join("")}</ul>`
    : `<p class="vazio">Nenhum alerta ativo. Dia tranquilo.</p>`;
  const eventos = P.dias.slice(0, 5).flatMap((d) => d.eventos.map((e) => ({ ...e, data: d.data })));
  return `
  <section class="grade">
    ${kpi("Cota", num(r.cota, 6), `dia ${pct(r.retorno_dia)}`, sinal(r.retorno_dia))}
    ${kpi("Patrimônio", mi(r.pl), `fluxo ${brl(r.fluxo_dia)}`)}
    ${kpi("Desde o início", pct(r.retorno_total), `CDI ${pct(r.cdi_total)} · <span class="${sinal(excesso)}">${excesso >= 0 ? "acima" : "abaixo"} ${pctSimples(Math.abs(excesso), 2)}</span>`, sinal(r.retorno_total))}
    ${kpi("Incidentes abertos", r.incidentes_abertos, `dívida técnica ${num(r.divida_tecnica, 0)}/100`, r.incidentes_abertos ? "neg" : "pos")}
    ${kpi("Credibilidade dos painéis", pctSimples(r.credibilidade), `confiança hoje ${pctSimples(r.confianca_media)}`)}
    ${kpi("Caixa da gestora", mi(r.caixa_gestora), "receita de taxa − custos", sinal(r.caixa_gestora))}
  </section>
  <section class="cartao"><h2>Cota × CDI</h2>${grafico([
    { nome: "Fundo", pontos: h.map((x) => [x.data, (x.cota - 1) * 100]) },
    { nome: "CDI", pontos: h.map((x) => [x.data, (x.bench - 1) * 100]), tracejado: true },
  ], { formato: (v) => `${num(v, 1)}%` })}</section>
  <section class="grade-2">
    <div class="cartao"><h2>Alertas ativos</h2>${alertas}</div>
    <div class="cartao"><h2>O que aconteceu</h2>${eventos.length ? `<ul class="lista">${eventos.slice(0, 12).map((e) => `<li><span class="quando">${dataBR(e.data)}</span><div>${selo(NOME_AREA[e.area] || e.area, e.tipo === "aberto" || e.tipo === "alerta" ? "aviso" : e.tipo === "resolvido" ? "ok" : "")} ${esc(e.texto)}</div></li>`).join("")}</ul>` : `<p class="vazio">Sem eventos recentes.</p>`}</div>
  </section>
  <section class="cartao"><h2>Acionar</h2>
    <p class="vazio" style="margin-bottom:10px">O fechamento roda sozinho de segunda a sexta. Você pode antecipar ou deixar uma diretriz para o agente.</p>
    <div class="acoes">
      <a class="botao prim" href="https://github.com/${REPO}/actions/workflows/fechamento.yml">Rodar fechamento</a>
      <a class="botao" href="https://github.com/${REPO}/issues/new?labels=conselho&title=${encodeURIComponent("Diretriz do conselho: ")}&body=${encodeURIComponent("O que os executivos devem considerar na próxima decisão:\n\n")}">Enviar diretriz</a>
      <a class="botao" href="https://github.com/${REPO}/pulls?q=is%3Apr+label%3Adia">Decisões (PRs)</a>
    </div>
  </section>`;
}

function extracao() {
  const ex = P.extracao, dias = ex.disponibilidade;
  const fontes = ex.fontes.map((f) => {
    const lib = Object.values(f.liberado_ate).filter(Boolean).sort().at(-1);
    const st = f.incidente ? selo(f.incidente, "ruim") : selo("ok", "ok");
    const real = f.real === "ok" ? selo("extração real ok", "ok") : f.real === "erro" ? selo("extração real falhou", "ruim") : "";
    return `<li class="fonte"><div><strong>${esc(f.nome)}</strong><div class="det">${f.series.join(", ")} · liberado até ${dataBR(lib)}</div>${f.erro_real ? `<div class="det neg">${esc(f.erro_real)}</div>` : ""}</div><div class="selos">${st}${f.alternativa_ligada ? selo("alternativa ligada", "info") : ""}${real}</div></li>`;
  }).join("");
  const matriz = dias.length
    ? `<div class="matriz" style="grid-template-columns: 110px repeat(${dias.length}, 1fr)">${ex.fontes.map((f) => `<div class="nome">${esc(f.nome.split(" ·")[0] === "BCB" ? f.nome.replace("BCB · ", "BCB ") : f.nome)}</div>${dias.map((d) => `<div class="cel ${d.fontes[f.id]}" title="${dataBR(d.data)}: ${d.fontes[f.id]}"></div>`).join("")}`).join("")}</div>
       <div class="legenda"><span><i style="background:var(--ok)"></i>ok</span><span><i style="background:var(--aviso)"></i>atraso</span><span><i style="background:var(--ruim)"></i>fora do ar / falha real</span><span><i style="background:var(--serie-5)"></i>mudou formato</span></div>`
    : `<p class="vazio">Sem histórico.</p>`;
  const incs = ex.incidentes.length
    ? ex.incidentes.map((i) => `<details ${i.estado === "aberto" ? "open" : ""}><summary>${selo(i.estado === "aberto" ? i.tipo : "resolvido", i.estado === "aberto" ? TIPO_INC[i.tipo] : "ok")} <strong>${i.id}</strong> · ${esc(i.fonte)} · ${dataBR(i.aberto_em)}${i.resolvido_em ? " → " + dataBR(i.resolvido_em) : ""}${linkIssue(i.issue)}</summary><p>${esc(i.detalhe)}. Ação: <code>${esc(i.acao)}</code>, ${i.dias} dia(s).</p><ul>${i.historico.map((h) => `<li>${esc(h)}</li>`).join("")}</ul></details>`).join("")
    : `<p class="vazio">Nenhum incidente nos últimos 30 dias.</p>`;
  return `
  <section class="grade">
    ${kpi("Dívida técnica", `${num(ex.divida_tecnica, 0)}/100`, "mais dívida, mais incidentes", ex.divida_tecnica > 50 ? "neg" : "")}
    ${kpi("Equipe", ex.equipe, "engenheiros de dados")}
    ${kpi("Orçamento", brl(ex.orcamento_dia), "por dia útil")}
  </section>
  <section class="cartao"><h2>Fontes</h2><ul class="lista fontes">${fontes}</ul></section>
  <section class="cartao"><h2>Disponibilidade (últimos dias úteis)</h2>${matriz}</section>
  <section class="cartao"><h2>Dívida técnica</h2>${grafico([{ nome: "Dívida", pontos: P.historico.map((x) => [x.data, x.divida_tecnica]) }], { formato: (v) => num(v, 0) })}</section>
  <section class="cartao"><h2>Incidentes</h2>${incs}</section>`;
}

function dashboards() {
  const db = P.dashboards;
  const linhas = db.indicadores.map((i) => {
    const st = i.defasagem === 0 ? selo(i.via === "alternativa" ? "via alternativa" : "em dia", i.via === "alternativa" ? "info" : "ok") : selo(`${i.defasagem}d atrás · ${i.estrategia}`, i.estrategia === "suspender" ? "ruim" : "aviso");
    const varia = i.valor != null && i.valor_anterior ? i.valor / i.valor_anterior - 1 : null;
    return `<tr><td><strong>${esc(i.nome)}</strong></td><td class="num">${i.valor == null ? "—" : num(i.valor, i.valor > 1000 ? 0 : 4)}${varia ? `<div class="det ${sinal(varia)}">${pct(varia)}</div>` : ""}</td><td>${dataBR(i.data_ref)}</td><td>${st}</td><td><div class="barra" title="${pctSimples(i.confianca)}"><span style="width:${i.confianca * 100}%"></span></div></td></tr>`;
  }).join("");
  return `
  <section class="grade">
    ${kpi("Credibilidade", pctSimples(db.credibilidade), "cai quando uma estimativa erra")}
    ${kpi("Confiança média hoje", pctSimples(db.confianca_media), "dos números entregues")}
    ${kpi("Estimativas a conferir", db.estimativas_pendentes.length, `estratégia padrão: ${db.estrategia_padrao}`)}
  </section>
  <section class="cartao"><h2>Números levados aos executivos</h2><div class="rolagem"><table><thead><tr><th>Indicador</th><th class="num">Valor</th><th>Referência</th><th>Situação</th><th style="width:90px">Confiança</th></tr></thead><tbody>${linhas}</tbody></table></div></section>
  <section class="cartao"><h2>Credibilidade e confiança</h2>${grafico([
    { nome: "Credibilidade", pontos: P.historico.map((x) => [x.data, x.credibilidade * 100]) },
    { nome: "Confiança do dia", pontos: P.historico.map((x) => [x.data, x.confianca_media * 100]), tracejado: true },
  ], { formato: (v) => `${num(v, 0)}%` })}</section>
  <section class="cartao"><h2>Estratégias quando falta dado</h2><ul class="lista">${Object.entries(P.nomes.estrategias).map(([k, v]) => `<li><code>${k}</code><span>${esc(v)}</span></li>`).join("")}</ul></section>`;
}

function executivos() {
  const e = P.executivos, g = e.gestora;
  const aloc = Object.keys(e.alvo).map((a) => {
    const [mn, mx] = e.limites[a];
    return `<div class="aloc"><span>${esc(P.nomes.ativos[a])}${e.congelados.includes(a) ? " ❄" : ""}</span><div class="faixa"><span class="lim" style="left:${mn * 100}%;width:${(mx - mn) * 100}%"></span><span class="atual" style="width:${e.pesos[a] * 100}%"></span><span class="alvo" style="left:${e.alvo[a] * 100}%"></span></div><span class="num">${pctSimples(e.pesos[a], 1)} → ${pctSimples(e.alvo[a])}</span></div>`;
  }).join("");
  const decs = e.decisoes_recentes.length
    ? `<ul class="lista">${e.decisoes_recentes.map((d) => `<li><span class="quando">${dataBR(d.data)}</span><div>${selo(d.autor, "info")} ${esc(d.resumo || "sem justificativa")}</div></li>`).join("")}</ul>`
    : `<p class="vazio">Nenhuma decisão registrada ainda: o fundo está no piloto automático.</p>`;
  return `
  <section class="grade">
    ${kpi("Dias sem decisão", e.dias_sem_decisao, e.ultima_decisao ? `última em ${dataBR(e.ultima_decisao)}` : "nenhuma ainda", e.dias_sem_decisao >= 3 ? "neg" : "")}
    ${kpi("Receita do dia", brl(g.receita_dia), "taxa de administração")}
    ${kpi("Custo do dia", brl(g.custo_dia), "casa + equipe + orçamento")}
    ${kpi("Caixa da gestora", mi(g.caixa), "", sinal(g.caixa))}
  </section>
  <section class="cartao"><h2>Alocação: atual (barra) × alvo (traço) × limite (faixa)</h2><div style="display:grid;gap:10px">${aloc}</div>${e.congelados.length ? `<p class="vazio" style="margin-top:8px">❄ congelado: sem número confiável no painel, os executivos não mexem.</p>` : ""}</section>
  <section class="cartao"><h2>Patrimônio</h2>${grafico([{ nome: "PL", pontos: P.historico.map((x) => [x.data, x.pl / 1e6]) }], { formato: (v) => `${num(v, 0)} mi` })}</section>
  <section class="cartao"><h2>Pesos ao longo do tempo</h2>${grafico(Object.keys(e.alvo).map((a) => ({ nome: P.nomes.ativos[a], pontos: P.historico.map((x) => [x.data, x.pesos[a] * 100]) })), { formato: (v) => `${num(v, 0)}%`, zero: true })}</section>
  <section class="cartao"><h2>Decisões recentes</h2>${decs}</section>`;
}

function processos() {
  const abertas = P.processos.issues_abertas;
  return `
  <section class="cartao"><h2>Issues abertas</h2>${abertas.length ? `<ul class="lista">${abertas.map((i) => `<li><span class="quando">#${i.numero}</span><div><a href="${esc(i.url)}">${esc(i.titulo)}</a><div class="det">${i.rotulos.map((r) => esc(r)).join(" · ")}</div></div></li>`).join("")}</ul>` : `<p class="vazio">Nenhuma issue aberta.</p>`}</section>
  <section class="cartao"><h2>Dias simulados</h2><ul class="lista">${P.dias.map((d) => `<li><span class="quando">${dataBR(d.data)}</span><div>${d.decisao.existe ? selo("decisão: " + d.decisao.autor, "info") : selo("piloto automático", "")} ${d.eventos.length} evento(s)</div></li>`).join("")}</ul></section>
  <section class="cartao"><h2>Como a empresa funciona</h2>
    <ol>
      <li><strong>Fechamento</strong> (GitHub Actions, seg–sex 08h): extrai BCB, Tesouro, Yahoo e B3; simula Extração → Dashboards → Executivos → fundo; abre e fecha issues.</li>
      <li><strong>Agente Claude</strong> (rotina agendada, depois do fechamento): lê o briefing e as issues, decide pelas três áreas e abre o PR do dia em <code>empresa/decisoes/</code>.</li>
      <li>A decisão vale no fechamento seguinte: o que acontece hoje muda o amanhã.</li>
    </ol>
  </section>`;
}

const ABAS = { hoje, extracao, dashboards, executivos, processos };

function render() {
  const aba = (location.hash.slice(1) || "hoje");
  const f = ABAS[aba] || hoje;
  document.querySelectorAll(".abas button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.aba === aba)));
  $("#conteudo").innerHTML = f();
}

document.querySelectorAll(".abas button").forEach((b) => b.addEventListener("click", () => { location.hash = b.dataset.aba; }));
window.addEventListener("hashchange", () => P && render());
let redim;
window.addEventListener("resize", () => { clearTimeout(redim); redim = setTimeout(() => P && render(), 150); });

carregar().then((p) => {
  P = p;
  $("#sub").textContent = `${p.fundo} · fechamento de ${dataBR(p.data_referencia)}`;
  $("#aviso").textContent = p.aviso;
  render();
}).catch((e) => {
  $("#sub").textContent = "sem dados";
  $("#conteudo").innerHTML = `<div class="cartao"><p class="vazio">Não foi possível carregar o painel: ${esc(e.message)}</p></div>`;
});
