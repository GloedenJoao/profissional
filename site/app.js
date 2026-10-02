"use strict";
// Central da Capivara Asset: lê o painel.json de cada cenário (foto do último fechamento) e, quando o
// GitHub responde, completa com o que está acontecendo agora (execuções, PRs, issues).
// O modo "Ao vivo" toca as reuniões dos times dia a dia (dias/AAAA-MM-DD.json → ata) e segue sozinho quando
// chega um dia novo: a página confere versao.json a cada minuto, sem precisar de Shift+F5.
const REPO = "GloedenJoao/profissional";
const GH = `https://github.com/${REPO}`;
const API = `https://api.github.com/repos/${REPO}`;
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
const ABA_DA_AREA = { extracao: "extracao", dashboards: "dashboards", executivos: "executivos", fundo: "executivos" };
const SEV = { alta: "ruim", media: "aviso", baixa: "info" };
const TIPO_INC = { atraso: "aviso", fora_do_ar: "ruim", mudanca_formato: "ruim", falha_real: "ruim" };
const NIVEL = {
  ruim: { icone: "●", rotulo: "Urgente", ordem: 0 },
  aviso: { icone: "▲", rotulo: "Atenção", ordem: 1 },
  info: { icone: "○", rotulo: "Pendente", ordem: 2 },
  ok: { icone: "✓", rotulo: "Feito", ordem: 3 },
};
const WORKFLOWS = { "Fechamento": "fechamento.yml", "Simulação · avançar": "simulacao.yml", "CI": "ci.yml" };
const ABAS = [["aovivo", "Ao vivo"], ["hoje", "Hoje"], ["extracao", "Extração"], ["dashboards", "Dashboards"], ["executivos", "Executivos"], ["processos", "Processos"]];

let CENARIOS = []; // [{id, nome, descricao, modo, inicio, P}]
let VIVO = null; // o que o GitHub diz agora: {runs, prs, issues, decisoes, erro}
let P = null; // painel do cenário aberto (as abas por área leem daqui)
let C = null; // cenário aberto
let FILTRO = "todos";

// ------------------------------------------------------------------ datas (horário de Brasília, dias úteis da B3)
function agoraBRT() {
  const s = new Date().toLocaleString("sv-SE", { timeZone: "America/Sao_Paulo" });
  return { data: s.slice(0, 10), hora: Number(s.slice(11, 13)) };
}
const somaDias = (iso, n) => { const d = new Date(`${iso}T12:00:00Z`); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const diaUtil = (iso, fer) => { const w = new Date(`${iso}T12:00:00Z`).getUTCDay(); return w !== 0 && w !== 6 && !fer.has(iso); };
function diaUtilAnterior(iso, fer) { let d = somaDias(iso, -1); while (!diaUtil(d, fer)) d = somaDias(d, -1); return d; }
function diasUteisEntre(a, b, fer) { let n = 0; for (let d = somaDias(a, 1); d <= b; d = somaDias(d, 1)) if (diaUtil(d, fer)) n++; return n; }
function haQuanto(iso) {
  if (!iso) return "";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  if (min < 48 * 60) return `há ${Math.round(min / 60)} h`;
  return `há ${Math.round(min / 1440)} dias`;
}

// ------------------------------------------------------------------ carga
async function json(url, fresco = true) {
  const r = await fetch(fresco && !url.startsWith("http") ? `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}` : url, { cache: fresco ? "no-store" : "default" });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function carregarCenarios() {
  let indice;
  try {
    indice = (await json("cenarios.json")).cenarios;
  } catch (_) {
    // site aberto direto do repositório (sem `python -m gestora site`): só o ao vivo
    indice = [{ id: "ao-vivo", nome: "Dia a dia", modo: "diario", painel: "painel.json", alternativo: "../dados/painel.json", dias: "../dados/dias/" }];
  }
  return Promise.all(indice.map(async (c) => {
    let painel = null;
    for (const url of [c.painel, c.alternativo].filter(Boolean)) {
      try { painel = await json(url); break; } catch (_) { /* tenta o próximo */ }
    }
    return { ...c, nome: painel?.cenario?.nome || c.nome, inicio: painel?.cenario?.inicio || c.inicio, P: painel };
  }));
}

const CACHE = "capivara-github-v1";
async function consultarGitHub(forcar = false) {
  try {
    const salvo = forcar ? null : JSON.parse(sessionStorage.getItem(CACHE) || "null");
    if (salvo && Date.now() - salvo.em < 120000) return salvo.dados;
  } catch (_) { /* sem sessionStorage: consulta de novo */ }
  const api = (c) => json(`${API}${c}`);
  const dados = { runs: {}, prs: [], issues: [], decisoes: {}, erro: null, em: new Date().toISOString() };
  try {
    const [runs, prs, issues] = await Promise.all([
      api("/actions/runs?per_page=40"), api("/pulls?state=open&per_page=30"), api("/issues?state=open&per_page=60"),
    ]);
    for (const r of runs.workflow_runs) {
      if (r.conclusion === "skipped" || dados.runs[r.name]) continue; // comentários que não são /avancar viram execuções puladas
      dados.runs[r.name] = { status: r.status, conclusion: r.conclusion, url: r.html_url, quando: r.run_started_at || r.created_at, evento: r.event, titulo: r.display_title, branch: r.head_branch };
    }
    dados.prs = prs.map((p) => ({ numero: p.number, titulo: p.title, url: p.html_url, rotulos: p.labels.map((l) => l.name), rascunho: p.draft, criado: p.created_at }));
    dados.issues = issues.filter((i) => !i.pull_request).map((i) => ({ numero: i.number, titulo: i.title, url: i.html_url, rotulos: i.labels.map((l) => l.name) }));
    await Promise.all(CENARIOS.filter((c) => c.P && !c.P.decisao_proxima?.existe).map(async (c) => {
      const r = await fetch(`${API}/contents/${c.P.decisao_proxima.caminho}?ref=main`, { cache: "no-store" });
      dados.decisoes[c.id] = r.ok;
    }));
  } catch (e) {
    dados.erro = e.message;
  }
  try { sessionStorage.setItem(CACHE, JSON.stringify({ em: Date.now(), dados })); } catch (_) { /* tudo bem */ }
  return dados;
}

// ------------------------------------------------------------------ situação de cada cenário
function controleDe(c) {
  const vivo = VIVO?.issues?.find((i) => i.rotulos.includes("controle") && i.rotulos.includes(`cenario:${c.id}`));
  if (vivo) return { numero: vivo.numero, url: vivo.url };
  return c.P?.processos?.controle || null;
}

function decisaoPronta(c) {
  if (!c.P) return false;
  return c.P.decisao_proxima?.existe || VIVO?.decisoes?.[c.id] === true;
}

function situacao(c) {
  const run = VIVO?.runs?.[c.modo === "diario" ? "Fechamento" : "Simulação · avançar"];
  if (run && run.status !== "completed") return { nivel: "info", rotulo: "Rodando agora", texto: `execução iniciada ${haQuanto(run.quando)}`, link: run.url };
  if (!c.P) return { nivel: "info", rotulo: "Não iniciada", texto: `o primeiro avanço funda a empresa em ${dataBR(c.inicio)}` };
  if (run && run.conclusion === "failure") return { nivel: "ruim", rotulo: "Última execução falhou", texto: haQuanto(run.quando), link: run.url };
  const P = c.P;
  if (c.modo === "diario") {
    const { data, hora } = agoraBRT();
    const prazo = P.proximo_fechamento_em;
    if (prazo && (data > prazo || (data === prazo && hora >= 10))) {
      return { nivel: "ruim", rotulo: "Atrasado", texto: `o fechamento de ${dataBR(P.proximo_dia_util)} devia ter rodado em ${dataBR(prazo)} às 08h`, link: `${GH}/actions/workflows/fechamento.yml` };
    }
    return { nivel: "ok", rotulo: "Em dia", texto: prazo ? `próximo fechamento em ${dataBR(prazo)}, 08h` : "" };
  }
  const fer = new Set(P.feriados || []);
  const ontem = diaUtilAnterior(agoraBRT().data, fer);
  const total = diasUteisEntre(P.cenario.inicio, ontem, fer);
  const faltam = diasUteisEntre(P.data_referencia, ontem, fer);
  if (!faltam) return { nivel: "ok", rotulo: "Alcançou o presente", texto: "agora anda um dia útil por dia, como o ao vivo", progresso: 1 };
  const auto = c.automatico;
  return { nivel: "info", rotulo: auto ? "Andando sozinha" : `Pausada em ${dataBR(P.data_referencia)}`, texto: `${total - faltam} de ${total} dias úteis · faltam ${faltam} até ontem${auto ? ` · ${auto.dias_por_execucao || 1} dia(s) a cada ${auto.intervalo || "30 min"}` : ""}`, progresso: (total - faltam) / total };
}

function pior(niveis) {
  return niveis.reduce((a, b) => (NIVEL[b].ordem < NIVEL[a].ordem ? b : a), "ok");
}

// ------------------------------------------------------------------ tarefas (foto do painel + o que o GitHub diz agora)
function tarefasDe(c) {
  const out = [];
  if (!c.P) {
    out.push({ nivel: "info", area: "executivos", titulo: `Começar a ${c.nome}`, detalhe: c.automatico ? `A próxima execução agendada (a cada ${c.automatico.intervalo || "30 min"}) funda a empresa em ${dataBR(c.inicio)}; para não esperar, rode o workflow.` : `Rode o workflow "Simulação · avançar" com cenário ${c.id}: ele funda a empresa em ${dataBR(c.inicio)}.`, link: `${GH}/actions/workflows/simulacao.yml`, acao: "Começar agora" });
    return out.map((t) => ({ ...t, cenario: c }));
  }
  for (const t of c.P.tarefas || []) {
    if (t.id.startsWith("CONSELHO-") && VIVO && !VIVO.erro && !VIVO.issues.some((i) => `CONSELHO-${i.numero}` === t.id)) continue; // já respondida e fechada
    out.push(t);
  }
  if (VIVO && !VIVO.erro) {
    for (const i of VIVO.issues) {
      const doCenario = c.id === "ao-vivo" ? !i.rotulos.some((r) => r.startsWith("cenario:")) : i.rotulos.includes(`cenario:${c.id}`);
      if (doCenario && i.rotulos.includes("conselho") && !out.some((t) => t.id === `CONSELHO-${i.numero}`)) {
        out.push({ id: `CONSELHO-${i.numero}`, area: "executivos", nivel: "aviso", titulo: `Diretriz do conselho #${i.numero}: ${i.titulo}`, detalhe: "nova desde o último fechamento", link: i.url, acao: "Responder" });
      }
    }
  }
  return out.map((t) => ({ ...t, cenario: c }));
}

function tarefasGerais() {
  const out = [];
  if (!VIVO || VIVO.erro) return out;
  for (const [nome, r] of Object.entries(VIVO.runs)) {
    if (r.conclusion === "failure") out.push({ nivel: nome === "CI" ? "aviso" : "ruim", area: "extracao", titulo: `${nome} falhou`, detalhe: `${r.titulo || ""} · ${haQuanto(r.quando)}`, link: r.url, acao: "Ver execução" });
  }
  for (const p of VIVO.prs) {
    const politica = p.rotulos.includes("politica");
    out.push({ nivel: politica ? "aviso" : "info", area: "executivos", titulo: `PR #${p.numero}: ${p.titulo}`, detalhe: politica ? "mudança de política: período de veto de um dia útil" : p.rotulos.includes("dia") ? "PR do dia: merge com a CI verde" : p.rascunho ? "rascunho" : `aberto ${haQuanto(p.criado)}`, link: p.url, acao: "Revisar" });
  }
  return out;
}

function todasTarefas() {
  const lista = [...tarefasGerais(), ...CENARIOS.flatMap(tarefasDe)];
  return lista.sort((a, b) => NIVEL[a.nivel].ordem - NIVEL[b.nivel].ordem);
}

// ------------------------------------------------------------------ gráficos (SVG puro, com cursor e dica)
let GRAFICOS = [];
function grafico(series, { altura = 180, formato = (v) => num(v), zero = false, compacto = false } = {}) {
  const disponivel = ($("#conteudo").clientWidth || 640) - 34;
  const largura = compacto ? Math.min(460, disponivel - 34) : disponivel;
  const W = Math.max(280, Math.min(1000, largura)), H = altura, m = { t: 10, r: 10, b: 22, l: compacto ? 44 : 52 };
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
  let svg = `<svg class="grafico" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map((s) => s.nome).join(", "))}">`;
  for (const t of ticks) svg += `<line class="eixo" x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${m.l - 6}" y="${y(t) + 4}" text-anchor="end">${esc(formato(t))}</text>`;
  if (zero && lo < 0 && hi > 0) svg += `<line class="zero" x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}"/>`;
  const idx = [0, Math.floor((xs.length - 1) / 2), xs.length - 1];
  for (const i of idx) svg += `<text x="${x(xs[i])}" y="${H - 4}" text-anchor="${i === 0 ? "start" : i === xs.length - 1 ? "end" : "middle"}">${dataBR(xs[i]).slice(0, xs.length > 200 ? 10 : 5)}</text>`;
  series.forEach((s, k) => {
    const cor = s.cor || `var(--serie-${k + 1})`;
    const d = s.pontos.filter((p) => p[1] != null).map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
    svg += `<path d="${d}" fill="none" stroke="${cor}" stroke-width="2" ${s.tracejado ? 'stroke-dasharray="5 4"' : ""} stroke-linejoin="round" stroke-linecap="round"/>`;
    const u = s.pontos.filter((p) => p[1] != null).at(-1);
    if (u) svg += `<circle cx="${x(u[0])}" cy="${y(u[1])}" r="4" fill="${cor}" stroke="var(--cartao)" stroke-width="2"/>`;
  });
  svg += `<line class="cursor" x1="0" x2="0" y1="${m.t}" y2="${H - m.b}" visibility="hidden"/></svg>`;
  const id = GRAFICOS.push({ xs, series, formato, W, x, mapa: series.map((s) => new Map(s.pontos)) }) - 1;
  const leg = series.length > 1 ? `<div class="legenda">${series.map((s, k) => `<span><i class="${s.tracejado ? "tracejado" : ""}" style="--cor:${s.cor || `var(--serie-${k + 1})`}"></i>${esc(s.nome)}</span>`).join("")}</div>` : "";
  return `<div class="grafico-box" data-g="${id}" tabindex="0" aria-label="Gráfico: use as setas para ver os valores">${svg}<div class="dica" hidden></div></div>${leg}`;
}

function mostrarDica(box, i) {
  const g = GRAFICOS[Number(box.dataset.g)];
  if (!g) return;
  i = Math.max(0, Math.min(g.xs.length - 1, i));
  box.dataset.i = i;
  const data = g.xs[i];
  const cursor = box.querySelector(".cursor");
  cursor.setAttribute("x1", g.x(data)); cursor.setAttribute("x2", g.x(data)); cursor.setAttribute("visibility", "visible");
  const dica = box.querySelector(".dica");
  dica.replaceChildren();
  const t = document.createElement("div"); t.className = "dica-data"; t.textContent = dataBR(data); dica.append(t);
  g.series.forEach((s, k) => {
    const v = g.mapa[k].get(data);
    if (v == null) return;
    const linha = document.createElement("div"); linha.className = "dica-linha";
    const traco = document.createElement("i"); traco.style.setProperty("--cor", s.cor || `var(--serie-${k + 1})`);
    const valor = document.createElement("strong"); valor.textContent = g.formato(v);
    const nome = document.createElement("span"); nome.textContent = s.nome;
    linha.append(traco, valor, nome); dica.append(linha);
  });
  dica.hidden = false;
  const frac = g.x(data) / g.W;
  dica.style.left = frac > 0.6 ? "" : `calc(${(frac * 100).toFixed(1)}% + 12px)`;
  dica.style.right = frac > 0.6 ? `calc(${((1 - frac) * 100).toFixed(1)}% + 12px)` : "";
}
function esconderDica(box) {
  box.querySelector(".cursor")?.setAttribute("visibility", "hidden");
  const d = box.querySelector(".dica"); if (d) d.hidden = true;
}
document.addEventListener("pointermove", (e) => {
  const box = e.target.closest?.(".grafico-box");
  document.querySelectorAll(".grafico-box").forEach((b) => b !== box && esconderDica(b));
  if (!box) return;
  const g = GRAFICOS[Number(box.dataset.g)], r = box.getBoundingClientRect();
  const vx = ((e.clientX - r.left) / r.width) * g.W;
  let melhor = 0;
  g.xs.forEach((d, i) => { if (Math.abs(g.x(d) - vx) < Math.abs(g.x(g.xs[melhor]) - vx)) melhor = i; });
  mostrarDica(box, melhor);
});
document.addEventListener("focusin", (e) => { if (e.target.classList?.contains("grafico-box")) mostrarDica(e.target, GRAFICOS[Number(e.target.dataset.g)].xs.length - 1); });
document.addEventListener("focusout", (e) => { if (e.target.classList?.contains("grafico-box")) esconderDica(e.target); });
document.addEventListener("keydown", (e) => {
  const box = e.target.closest?.(".grafico-box");
  if (!box || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
  e.preventDefault();
  mostrarDica(box, Number(box.dataset.i || 0) + (e.key === "ArrowRight" ? 1 : -1));
});

// ------------------------------------------------------------------ peças
const kpi = (rot, val, det = "", cls = "") => `<div class="cartao kpi"><div class="rot">${rot}</div><div class="val ${cls}">${val}</div><div class="det">${det}</div></div>`;
const selo = (txt, cls) => `<span class="selo ${cls || ""}">${esc(txt)}</span>`;
const linkIssue = (i) => (i ? ` <a href="${esc(i.url)}">#${i.numero}</a>` : "");
const pilula = (nivel, txt) => `<span class="pilula ${nivel}"><b aria-hidden="true">${NIVEL[nivel].icone}</b>${esc(txt)}</span>`;
const externo = (href, txt, cls = "botao") => `<a class="${cls}" href="${esc(href)}" target="_blank" rel="noopener">${txt}</a>`;

function linhaTarefa(t, comCenario = true) {
  const n = NIVEL[t.nivel];
  return `<li class="tarefa ${t.nivel}">
    <span class="nivel"><b aria-hidden="true">${n.icone}</b>${n.rotulo}</span>
    <div class="corpo">
      <div class="tit">${esc(t.titulo)}</div>
      <div class="det">${comCenario && t.cenario ? `<a class="chip" href="#/${esc(t.cenario.id)}">${esc(t.cenario.nome)}</a>` : ""}${t.area ? `<span class="chip">${esc(NOME_AREA[t.area] || t.area)}</span>` : ""}${textoFala(t.detalhe || "")}</div>
    </div>
    ${t.link ? externo(t.link, `${esc(t.acao || "Abrir")} <span aria-hidden="true">↗</span>`, "botao pequeno") : ""}
  </li>`;
}

function areas(c) {
  const st = c.P?.status_areas;
  if (!st) return "";
  return `<div class="areas-st">${Object.entries(st).map(([a, s]) => `<a class="area-st ${s.nivel}" href="#/${esc(c.id)}/${ABA_DA_AREA[a]}"><span class="nome"><b aria-hidden="true">${NIVEL[s.nivel].icone}</b>${NOME_AREA[a]}</span><span class="det">${esc(s.texto)}</span></a>`).join("")}</div>`;
}

function botoesAvancar(c) {
  const ctl = controleDe(c);
  if (!ctl) return externo(`${GH}/actions/workflows/simulacao.yml`, c.P ? "Adiantar pelo Actions ↗" : "Começar a simulação ↗", c.P ? "botao leve" : "botao prim");
  return [5, 20].map((n) => `<button class="botao leve" type="button" data-copiar="/avancar${n > 1 ? ` ${n}` : ""}" data-abrir="${esc(ctl.url)}" title="Adianta a simulação sem esperar o ritmo automático">Adiantar ${n} dias</button>`).join("");
}

function botaoIntervir(c) {
  const dec = c.P?.decisao_proxima;
  if (!dec) return "";
  return decisaoPronta(c)
    ? externo(dec.link_ver, `✓ Diretriz de ${dataBR(dec.data)}`, "botao leve")
    : externo(dec.link_criar, "Intervir (opcional) ↗", "botao leve");
}

function acoesCenario(c) {
  const assistir = c.P ? `<a class="botao prim" href="#/${esc(c.id)}/aovivo">▶ Assistir às reuniões</a>` : "";
  if (c.modo === "diario") return `${assistir}${externo(`${GH}/actions/workflows/fechamento.yml`, "Rodar fechamento ↗", "botao leve")}${botaoIntervir(c)}`;
  return `${assistir}${botoesAvancar(c)}${botaoIntervir(c)}`;
}

// ------------------------------------------------------------------ central
function ultimaReuniao(c) {
  const falas = (c.P?.ata || []).filter((f) => f.tipo === "decisao" || f.tipo === "conselho");
  if (!c.P?.ata?.length) return "";
  const itens = falas.length ? falas.slice(-3).map((f) => `<li><b class="area-cor ${esc(f.area)}">${esc(f.quem)}</b> ${textoFala(f.texto)}</li>`).join("")
    : `<li>Ninguém mudou nada: os times mantiveram ações, estratégias e carteira.</li>`;
  return `<div class="reuniao-mini"><div class="det">Decisões dos times em ${dataBR(c.P.data_referencia)}${falas.length > 3 ? ` (últimas 3 de ${falas.length})` : ""}</div><ul>${itens}</ul></div>`;
}

function cartaoCenario(c) {
  const s = situacao(c);
  const P = c.P;
  const cab = `<div class="cen-cab"><div><h2 class="cen-nome"><a href="#/${esc(c.id)}">${esc(c.nome)}</a></h2><div class="det">${c.modo === "diario" ? "diário · roda sozinho seg–sex, 08h" : c.automatico ? "simulação · anda sozinha" : "simulação · anda quando você manda"}</div></div>${s.link ? `<a class="pilula-link" href="${esc(s.link)}" target="_blank" rel="noopener">${pilula(s.nivel, s.rotulo)}</a>` : pilula(s.nivel, s.rotulo)}</div>`;
  const prog = s.progresso != null ? `<div class="progresso" role="progressbar" aria-valuenow="${Math.round(s.progresso * 100)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${(s.progresso * 100).toFixed(1)}%"></span></div>` : "";
  if (!P) {
    return `<section class="cartao cen">${cab}<p class="det">${esc(s.texto)}</p><p>${esc(c.descricao || "")}</p><div class="acoes">${acoesCenario(c)}</div></section>`;
  }
  const r = P.resumo, h = P.historico, exc = r.retorno_total - r.cdi_total;
  return `<section class="cartao cen">
    ${cab}
    <p class="det">${esc(s.texto)} · fechamento de <strong>${dataBR(P.data_referencia)}</strong></p>${prog}
    <div class="mini-kpis">
      <div><span class="rot">Cota</span><strong>${num(r.cota, 4)}</strong><span class="det ${sinal(r.retorno_dia)}">dia ${pct(r.retorno_dia)}</span></div>
      <div><span class="rot">Desde o início</span><strong class="${sinal(r.retorno_total)}">${pct(r.retorno_total)}</strong><span class="det">CDI ${pct(r.cdi_total)} · <span class="${sinal(exc)}">${exc >= 0 ? "+" : "−"}${pctSimples(Math.abs(exc), 2)}</span></span></div>
      <div><span class="rot">Patrimônio</span><strong>${mi(r.pl)}</strong><span class="det">fluxo ${brl(r.fluxo_dia)}</span></div>
      <div><span class="rot">Caixa da gestora</span><strong class="${sinal(r.caixa_gestora)}">${mi(r.caixa_gestora)}</strong><span class="det">${r.alertas} alerta(s)</span></div>
    </div>
    ${grafico([
      { nome: "Fundo", pontos: h.map((x) => [x.data, (x.cota - 1) * 100]) },
      { nome: "CDI", pontos: h.map((x) => [x.data, (x.bench - 1) * 100]), tracejado: true, cor: "var(--ref)" },
    ], { altura: 120, compacto: true, formato: (v) => `${num(v, 1)}%` })}
    ${ultimaReuniao(c)}
    ${areas(c)}
    <div class="acoes">${acoesCenario(c)}<a class="botao leve" href="#/${esc(c.id)}/hoje">Painel →</a></div>
  </section>`;
}

function pipeline() {
  if (!VIVO) return `<p class="vazio">Consultando o GitHub…</p>`;
  if (VIVO.erro) return `<p class="vazio">O GitHub não respondeu agora (${esc(VIVO.erro)}). As situações acima são a foto do último fechamento.</p>`;
  const EVENTO = { schedule: "agenda", workflow_dispatch: "manual", issue_comment: "comentário", push: "push", pull_request: "PR" };
  return `<ul class="lista pipe">${Object.entries(WORKFLOWS).map(([nome, arq]) => {
    const r = VIVO.runs[nome];
    const st = !r ? pilula("info", "sem execuções") : r.status !== "completed" ? pilula("info", "rodando") : r.conclusion === "success" ? pilula("ok", "ok") : pilula("ruim", r.conclusion || "falhou");
    return `<li><div class="corpo"><a href="${GH}/actions/workflows/${arq}" target="_blank" rel="noopener"><strong>${esc(nome)}</strong></a><div class="det">${r ? `${esc(EVENTO[r.evento] || r.evento)} · ${haQuanto(r.quando)} · ${esc(r.titulo || "")}` : ""}</div></div>${r ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${st}</a>` : st}</li>`;
  }).join("")}</ul><p class="det" style="margin-top:8px">Consultado ${haQuanto(VIVO.em)}.</p>`;
}

function comparacao() {
  const com = CENARIOS.filter((c) => c.P && c.P.historico.length > 1);
  if (com.length < 2) return "";
  return `<section class="cartao"><h2>Cenários lado a lado: retorno acima do CDI desde a fundação</h2>
    ${grafico(com.map((c, k) => ({ nome: c.nome, cor: `var(--serie-${k + 1})`, pontos: c.P.historico.map((x) => [x.data, (x.cota / x.bench - 1) * 100]) })), { formato: (v) => `${num(v, 2)}%`, zero: true })}
    <p class="det">Cada linha começa na fundação do seu cenário. Acima de zero, o fundo bateu o CDI do período.</p></section>`;
}

function central() {
  const tarefas = todasTarefas();
  const filtradas = tarefas.filter((t) => FILTRO === "todos" || (t.cenario ? t.cenario.id === FILTRO : FILTRO === "github"));
  const urgentes = tarefas.filter((t) => t.nivel === "ruim").length, atencao = tarefas.filter((t) => t.nivel === "aviso").length;
  const filtros = [["todos", "Todas"], ...CENARIOS.map((c) => [c.id, c.nome]), ["github", "GitHub"]];
  return `
  <section class="resumo-central">
    <div><span class="grande">${tarefas.filter((t) => t.nivel !== "ok").length}</span> tarefa(s) em aberto</div>
    ${urgentes ? pilula("ruim", `${urgentes} urgente(s)`) : ""}${atencao ? pilula("aviso", `${atencao} pedem atenção`) : ""}${!urgentes && !atencao ? pilula("ok", "nada urgente") : ""}
  </section>
  <section class="grade-cen">${CENARIOS.map(cartaoCenario).join("")}</section>
  <section class="grade-2 larga">
    <div class="cartao"><h2>Tarefas</h2>
      <div class="filtros" role="group" aria-label="Filtrar tarefas">${filtros.map(([id, nome]) => `<button type="button" class="chip-filtro" data-filtro="${esc(id)}" aria-pressed="${FILTRO === id}">${esc(nome)}</button>`).join("")}</div>
      ${filtradas.length ? `<ul class="lista tarefas">${filtradas.map((t) => linhaTarefa(t)).join("")}</ul>` : `<p class="vazio">Nada por aqui.</p>`}
    </div>
    <div class="cartao"><h2>Automação no GitHub</h2>${pipeline()}</div>
  </section>
  ${comparacao()}
  <section class="cartao"><h2>Como funciona</h2>
    <ol class="passos">
      <li><strong>Quem decide são os times.</strong> Todo dia útil a Extração (Bia e Téo) faz a triagem dos incidentes, os Dashboards (Caio e Lia) decidem o que publicar quando falta dado e o Comitê (Helena, Rafael e Marta) mexe na carteira, na equipe e no orçamento olhando só os números do painel.</li>
      <li><strong>Ao vivo</strong> (aba de cada cenário): as reuniões tocam fala por fala, na ordem em que aconteceram. Quando chega um dia novo, a página percebe sozinha em até um minuto e continua.</li>
      <li><strong>Dia a dia</strong> fecha de segunda a sexta às 08h com os dados reais de ontem. <strong>Simulação 2026</strong> refaz o ano desde 1º de janeiro, um dia útil a cada 30 minutos, até alcançar o presente.</li>
      <li><strong>Você não precisa fazer nada.</strong> Se quiser intervir, "Intervir" abre uma diretriz do conselho já preenchida: o que estiver nela vale por cima dos times naquele dia, e a ata registra.</li>
    </ol>
  </section>`;
}

// ------------------------------------------------------------------ abas de um cenário
function hoje() {
  const r = P.resumo, h = P.historico;
  const excesso = r.retorno_total - r.cdi_total;
  const tarefas = tarefasDe(C);
  const eventos = P.dias.slice(0, 5).flatMap((d) => d.eventos.map((e) => ({ ...e, data: d.data })));
  const s = situacao(C);
  return `
  <section class="cartao faixa-st">${pilula(s.nivel, s.rotulo)}<span class="det">${esc(s.texto)}</span>${s.progresso != null ? `<div class="progresso"><span style="width:${(s.progresso * 100).toFixed(1)}%"></span></div>` : ""}</section>
  ${areas(C)}
  <section class="grade">
    ${kpi("Cota", num(r.cota, 6), `dia ${pct(r.retorno_dia)}`, sinal(r.retorno_dia))}
    ${kpi("Patrimônio", mi(r.pl), `fluxo ${brl(r.fluxo_dia)}`)}
    ${kpi("Desde o início", pct(r.retorno_total), `CDI ${pct(r.cdi_total)} · <span class="${sinal(excesso)}">${excesso >= 0 ? "acima" : "abaixo"} ${pctSimples(Math.abs(excesso), 2)}</span>`, sinal(r.retorno_total))}
    ${kpi("Incidentes abertos", r.incidentes_abertos, `dívida técnica ${num(r.divida_tecnica, 0)}/100`, r.incidentes_abertos ? "neg" : "pos")}
    ${kpi("Credibilidade dos painéis", pctSimples(r.credibilidade), `confiança hoje ${pctSimples(r.confianca_media)}`)}
    ${kpi("Caixa da gestora", mi(r.caixa_gestora), "receita de taxa − custos", sinal(r.caixa_gestora))}
  </section>
  <section class="cartao"><h2>Acompanhar</h2><div class="acoes">${acoesCenario(C)}</div>
    ${tarefas.length ? `<ul class="lista tarefas" style="margin-top:12px">${tarefas.map((t) => linhaTarefa(t, false)).join("")}</ul>` : ""}</section>
  <section class="cartao"><h2>Cota × CDI desde a fundação</h2>${grafico([
    { nome: "Fundo", pontos: h.map((x) => [x.data, (x.cota - 1) * 100]) },
    { nome: "CDI", pontos: h.map((x) => [x.data, (x.bench - 1) * 100]), tracejado: true, cor: "var(--ref)" },
  ], { formato: (v) => `${num(v, 1)}%` })}</section>
  <section class="cartao"><h2>O que aconteceu</h2>${eventos.length ? `<ul class="lista">${eventos.slice(0, 14).map((e) => `<li><span class="quando">${dataBR(e.data)}</span><div>${selo(NOME_AREA[e.area] || e.area, e.tipo === "aberto" || e.tipo === "alerta" ? "aviso" : e.tipo === "resolvido" ? "ok" : "")} ${esc(e.texto)}</div></li>`).join("")}</ul>` : `<p class="vazio">Sem eventos nos últimos dias úteis.</p>`}</section>`;
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
    ? `<div class="matriz" style="grid-template-columns: 110px repeat(${dias.length}, 1fr)">${ex.fontes.map((f) => `<div class="nome">${esc(f.nome.replace("BCB · ", "BCB "))}</div>${dias.map((d) => `<div class="cel ${d.fontes[f.id]}" title="${dataBR(d.data)}: ${d.fontes[f.id]}"></div>`).join("")}`).join("")}</div>
       <div class="legenda caixas"><span><i style="--cor:var(--ok)"></i>ok</span><span><i style="--cor:var(--aviso)"></i>atraso</span><span><i style="--cor:var(--ruim)"></i>fora do ar / falha real</span><span><i style="--cor:var(--formato)"></i>mudou formato</span></div>`
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
  <section class="cartao"><h2>Dívida técnica</h2>${grafico([{ nome: "Dívida técnica", pontos: P.historico.map((x) => [x.data, x.divida_tecnica]) }], { formato: (v) => num(v, 0) })}</section>
  <section class="cartao"><h2>Incidentes</h2>${incs}</section>`;
}

function dashboards() {
  const db = P.dashboards;
  const linhas = db.indicadores.map((i) => {
    const st = i.defasagem === 0 ? selo(i.via === "alternativa" ? "via alternativa" : "em dia", i.via === "alternativa" ? "info" : "ok") : selo(`${i.defasagem}d atrás · ${i.estrategia}`, i.estrategia === "suspender" ? "ruim" : "aviso");
    const varia = i.valor != null && i.valor_anterior ? i.valor / i.valor_anterior - 1 : null;
    return `<tr><td><strong>${esc(i.nome)}</strong></td><td class="num">${i.valor == null ? "—" : num(i.valor, i.valor > 1000 ? 0 : 4)}${varia ? `<div class="det ${sinal(varia)}">${pct(varia)}</div>` : ""}</td><td>${dataBR(i.data_ref)}</td><td>${st}</td><td><div class="barra" title="${pctSimples(i.confianca)}"><span style="width:${i.confianca * 100}%"></span></div><div class="det">${pctSimples(i.confianca)}</div></td></tr>`;
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
    : `<p class="vazio">O comitê ainda não mudou nada desde a fundação.</p>`;
  return `
  <section class="grade">
    ${kpi("Último ajuste do comitê", e.ultima_decisao ? dataBR(e.ultima_decisao) : "—", e.ultima_decisao ? "alocação, equipe ou orçamento" : "mantém a alocação inicial")}
    ${kpi("Receita do dia", brl(g.receita_dia), "taxa de administração")}
    ${kpi("Custo do dia", brl(g.custo_dia), "casa + equipe + orçamento")}
    ${kpi("Caixa da gestora", mi(g.caixa), "", sinal(g.caixa))}
  </section>
  <section class="cartao"><h2>Alocação: atual (barra) × alvo (traço) × limite (faixa)</h2><div style="display:grid;gap:10px">${aloc}</div>${e.congelados.length ? `<p class="vazio" style="margin-top:8px">❄ congelado: sem número confiável no painel, os executivos não mexem.</p>` : ""}<div class="acoes" style="margin-top:12px"><a class="botao" href="#/${esc(C.id)}/aovivo">▶ Ver o comitê decidindo</a>${botaoIntervir(C)}</div></section>
  <section class="cartao"><h2>Patrimônio</h2>${grafico([{ nome: "PL", pontos: P.historico.map((x) => [x.data, x.pl / 1e6]) }], { formato: (v) => `${num(v, 0)} mi` })}</section>
  <section class="cartao"><h2>Pesos ao longo do tempo</h2>${grafico(Object.keys(e.alvo).map((a) => ({ nome: P.nomes.ativos[a], pontos: P.historico.map((x) => [x.data, x.pesos[a] * 100]) })), { formato: (v) => `${num(v, 0)}%`, zero: true })}</section>
  <section class="cartao"><h2>Ajustes recentes do comitê</h2>${decs}</section>`;
}

function processos() {
  const abertas = P.processos.issues_abertas;
  const ctl = controleDe(C);
  const pasta = P.decisao_proxima.link_pasta;
  return `
  <section class="cartao"><h2>Onde as coisas acontecem</h2><div class="acoes">
    ${ctl ? externo(ctl.url, `Issue de controle #${ctl.numero} ↗`) : ""}
    ${externo(pasta, "Diretrizes do conselho ↗")}${externo(pasta.replace(/decisoes$/, "diario"), "Diário ↗")}
    ${externo(`${GH}/issues?q=is%3Aopen+label%3A${encodeURIComponent(C.id === "ao-vivo" ? "simulacao" : `cenario:${C.id}`)}`, "Issues do cenário ↗")}
    ${externo(`${GH}/actions/workflows/${C.modo === "diario" ? "fechamento.yml" : "simulacao.yml"}`, "Execuções ↗")}
  </div></section>
  <section class="cartao"><h2>Issues abertas</h2>${abertas.length ? `<ul class="lista">${abertas.map((i) => `<li><span class="quando">#${i.numero}</span><div><a href="${esc(i.url)}">${esc(i.titulo)}</a><div class="det">${i.rotulos.map((r) => esc(r)).join(" · ")}</div></div></li>`).join("")}</ul>` : `<p class="vazio">Nenhuma issue aberta no último fechamento.</p>`}</section>
  <section class="cartao"><h2>Dias simulados</h2><ul class="lista">${P.dias.map((d) => `<li><span class="quando">${dataBR(d.data)}</span><div>${d.decisao.intervencao ? selo("conselho + times", "aviso") : d.decisao.autor === "times" ? selo("times", "info") : d.decisao.existe ? selo(d.decisao.autor || "decisão", "info") : selo("piloto automático", "")} ${d.eventos.length} evento(s) · <a href="#/${esc(C.id)}/aovivo/${d.data}">assistir</a></div></li>`).join("")}</ul></section>
  <section class="cartao"><h2>Como este cenário funciona</h2>
    <p>${esc(C.descricao || P.cenario?.descricao || "")}</p>
    <ol>
      <li><strong>${C.modo === "diario" ? "Fechamento" : "Avanço"}</strong>: extrai BCB, Tesouro, Yahoo e B3; simula Extração → Dashboards → Executivos → fundo; abre e fecha issues.</li>
      <li><strong>Reuniões</strong>: Extração (08h) → Dashboards (09h) → Comitê (10h) decidem com o que a área anterior entregou; tudo vai para a ata do dia.</li>
      <li><strong>Diretriz do conselho</strong> (opcional): um arquivo em <code>${esc(P.decisao_proxima.caminho.replace(/[^/]+$/, ""))}</code> vale por cima dos times naquele dia.</li>
      <li>O que acontece hoje muda o amanhã: dívida técnica, credibilidade, caixa e carteira passam de um dia para o outro.</li>
    </ol>
  </section>`;
}

// ------------------------------------------------------------------ ao vivo: as reuniões dos times, fala por fala
const NOME_SALA = { extracao: "Extração", dashboards: "Dashboards", executivos: "Comitê", fundo: "Fechamento" };
const HORA_SALA = { extracao: "08:00", dashboards: "09:00", executivos: "10:00", fundo: "18:00" };
const ROTULO_TIPO = { decisao: "decisão", conselho: "conselho", alerta: "alerta", fechamento: "fechamento" };
const VELOCIDADES = [["1", "1×"], ["2", "2×"], ["5", "5×"], ["0", "tudo"]];
const PLAY = { cen: null, datas: [], i: -1, n: 0, dia: null, tocando: true, vel: 1, seguir: true, timer: null, fim: false };
const VISTO = (id) => `capivara-visto-${id}`;
const ler = (k, padrao) => { try { return localStorage.getItem(k) ?? padrao; } catch (_) { return padrao; } };
const gravar = (k, v) => { try { localStorage.setItem(k, v); } catch (_) { /* navegador sem storage: tudo bem */ } };
const textoFala = (t) => esc(t).replace(/`([^`]+)`/g, "<code>$1</code>");
const diaSemana = (iso) => new Date(`${iso}T12:00:00Z`).toLocaleDateString("pt-BR", { weekday: "long", timeZone: "UTC" });

function aovivo() {
  return `
  <section class="cartao palco">
    <div class="palco-cab">
      <div>
        <div class="det" id="pl-pos"></div>
        <h2 class="pl-dia" id="pl-dia">carregando…</h2>
      </div>
      <div class="relogio" id="pl-relogio" aria-hidden="true">--:--</div>
    </div>
    <div class="salas" id="pl-salas">${Object.entries(NOME_SALA).map(([a, n]) => `<div class="sala" data-sala="${a}"><b>${HORA_SALA[a]}</b>${n}</div>`).join("")}</div>
    <div class="controles" role="group" aria-label="Controles">
      <button class="botao leve" type="button" data-pl="ant" title="Dia anterior">⏮</button>
      <button class="botao prim" type="button" data-pl="play" id="pl-play">⏸ Pausar</button>
      <button class="botao leve" type="button" data-pl="prox" title="Próximo dia">⏭</button>
      <label class="det">Ritmo <select id="pl-vel">${VELOCIDADES.map(([v, n]) => `<option value="${v}">${n}</option>`).join("")}</select></label>
      <label class="det"><input type="checkbox" id="pl-seguir" checked> seguir para o próximo dia</label>
      <input type="range" id="pl-linha" min="0" max="0" value="0" aria-label="Escolher o dia">
    </div>
  </section>
  <section class="grade-palco">
    <div class="cartao"><h2>Ata do dia</h2><ol class="feed" id="pl-feed" role="log" aria-live="polite"></ol><div id="pl-digitando" class="digitando" hidden></div><div id="pl-espera" class="espera" hidden></div></div>
    <div class="cartao lateral"><h2>Resultado do dia</h2><div id="pl-resultado"><p class="vazio">Aparece no fechamento, às 18h.</p></div></div>
  </section>`;
}

function iniciarPlayer(c, data) {
  if (PLAY.timer) clearTimeout(PLAY.timer);
  PLAY.cen = c.id;
  PLAY.datas = c.P?.datas || [];
  PLAY.vel = Number(ler("capivara-vel", "1"));
  PLAY.seguir = ler("capivara-seguir", "1") === "1";
  $("#pl-vel").value = String(PLAY.vel);
  $("#pl-seguir").checked = PLAY.seguir;
  const linha = $("#pl-linha");
  linha.max = Math.max(0, PLAY.datas.length - 1);
  if (!PLAY.datas.length) { $("#pl-dia").textContent = "Ainda não há dias simulados"; return; }
  let i = data ? PLAY.datas.indexOf(data) : -1;
  if (i < 0) {
    // continua de onde parou; se já viu tudo (ou nunca viu), começa pelo dia mais recente
    const visto = PLAY.datas.indexOf(ler(VISTO(c.id), ""));
    i = visto >= 0 && visto < PLAY.datas.length - 1 ? visto + 1 : PLAY.datas.length - 1;
  }
  PLAY.tocando = true;
  irPara(i);
}

async function irPara(i) {
  const c = CENARIOS.find((x) => x.id === PLAY.cen);
  if (!c || i < 0 || i >= PLAY.datas.length) return;
  if (PLAY.timer) clearTimeout(PLAY.timer);
  PLAY.i = i; PLAY.n = 0; PLAY.fim = false;
  const data = PLAY.datas[i];
  $("#pl-linha").value = i;
  $("#pl-pos").textContent = `Dia ${i + 1} de ${PLAY.datas.length} · ${c.nome}`;
  $("#pl-dia").textContent = `${diaSemana(data)}, ${dataBR(data)}`;
  $("#pl-feed").innerHTML = "";
  $("#pl-espera").hidden = true;
  $("#pl-resultado").innerHTML = `<p class="vazio">Aparece no fechamento, às 18h.</p>`;
  marcarSala(null);
  let dia = null;
  for (const url of [`${c.dias || `cenarios/${c.id}/dias/`}${data}.json`, `../${c.id === "ao-vivo" ? "dados" : `cenarios/${c.id}/dados`}/dias/${data}.json`]) {
    try { dia = await json(url, false); break; } catch (_) { /* tenta o próximo */ }
  }
  if (PLAY.datas[PLAY.i] !== data) return; // trocou de dia enquanto carregava
  PLAY.dia = dia || { data, ata: [], eventos: [], resumo: null };
  if (!PLAY.dia.ata?.length) {
    // dia anterior aos times: só os acontecimentos
    PLAY.dia.ata = (PLAY.dia.eventos || []).map((e) => ({ hora: "", area: e.area, quem: NOME_AREA[e.area] || e.area, papel: "", texto: e.texto, tipo: e.tipo === "aberto" || e.tipo === "alerta" ? "alerta" : "evento" }));
    PLAY.dia.ata.unshift({ hora: "", area: "fundo", quem: "Arquivo", papel: "", texto: "Dia anterior aos times: não há ata das reuniões, só os acontecimentos.", tipo: "evento" });
  }
  atualizarBotaoPlay();
  passo();
}

function marcarSala(area) {
  const ordem = Object.keys(NOME_SALA);
  const k = ordem.indexOf(area);
  document.querySelectorAll(".sala").forEach((el) => {
    const j = ordem.indexOf(el.dataset.sala);
    el.classList.toggle("ativa", j === k);
    el.classList.toggle("feita", k >= 0 && j < k);
  });
}

function mostrarFala(f) {
  const li = document.createElement("li");
  li.className = `fala ${f.area} ${f.tipo}`;
  li.innerHTML = `<span class="hora">${esc(f.hora)}</span><div class="balao"><div class="quem"><b class="area-cor ${esc(f.area)}">${esc(f.quem)}</b>${f.papel ? ` · ${esc(f.papel)}` : ""}${ROTULO_TIPO[f.tipo] ? ` <span class="selo ${f.tipo === "decisao" ? "info" : f.tipo === "alerta" ? "aviso" : f.tipo === "conselho" ? "ruim" : "ok"}">${ROTULO_TIPO[f.tipo]}</span>` : ""}</div><div class="txt">${textoFala(f.texto)}</div></div>`;
  $("#pl-feed").append(li);
  if (f.hora) $("#pl-relogio").textContent = f.hora;
  marcarSala(f.area);
  const box = li.getBoundingClientRect();
  if (box.bottom > window.innerHeight || box.top < 0) li.scrollIntoView({ block: "nearest", behavior: PLAY.vel ? "smooth" : "auto" });
}

function passo() {
  if (PLAY.timer) clearTimeout(PLAY.timer);
  const ata = PLAY.dia?.ata || [];
  const digitando = $("#pl-digitando");
  if (!digitando) return; // saiu da tela do ao vivo
  if (PLAY.vel === 0) {
    while (PLAY.n < ata.length) mostrarFala(ata[PLAY.n++]);
  }
  if (PLAY.n >= ata.length) { digitando.hidden = true; return terminarDia(); }
  if (!PLAY.tocando) { digitando.hidden = true; return; }
  const f = ata[PLAY.n];
  digitando.hidden = false;
  digitando.textContent = `${f.quem} está ${f.tipo === "fechamento" || f.tipo === "evento" || f.tipo === "alerta" ? "registrando" : "falando"}…`;
  const espera = (700 + Math.min(2600, f.texto.length * 22)) / PLAY.vel;
  PLAY.timer = setTimeout(() => { mostrarFala(f); PLAY.n++; passo(); }, espera);
}

function terminarDia() {
  PLAY.fim = true;
  marcarSala("fim");
  const c = CENARIOS.find((x) => x.id === PLAY.cen);
  const data = PLAY.datas[PLAY.i];
  if (PLAY.datas.indexOf(ler(VISTO(c.id), "")) < PLAY.i) gravar(VISTO(c.id), data);
  $("#pl-resultado").innerHTML = resultadoDia(PLAY.dia, c);
  const ultimo = PLAY.i >= PLAY.datas.length - 1;
  if (!ultimo && PLAY.seguir && PLAY.tocando) {
    mostrarEspera(`Próximo dia em instantes: ${dataBR(PLAY.datas[PLAY.i + 1])}.`);
    PLAY.timer = setTimeout(() => irPara(PLAY.i + 1), 2500 / (PLAY.vel || 4));
  } else if (ultimo) {
    mostrarEspera(proximoDiaTexto(c));
  } else {
    mostrarEspera(`Fim de ${dataBR(data)}. ⏭ para o próximo dia.`);
  }
  atualizarBotaoPlay();
}

function mostrarEspera(texto) {
  const e = $("#pl-espera");
  if (!e) return;
  e.hidden = false;
  e.innerHTML = `<span class="pulso" aria-hidden="true"></span>${esc(texto)}`;
}

function proximoDiaTexto(c) {
  const s = situacao(c);
  if (c.modo === "diario") return `Você está em dia. Próximo fechamento: ${c.P?.proximo_fechamento_em ? `${dataBR(c.P.proximo_fechamento_em)} às 08h` : "no próximo dia útil"}. A página confere sozinha e toca a reunião nova quando ela chegar.`;
  if (s.rotulo === "Rodando agora") return "Os times estão reunidos agora: o próximo dia aparece aqui em instantes.";
  if (s.progresso === 1) return "A simulação alcançou o presente. Um dia novo por dia útil; a página confere sozinha.";
  if (c.automatico) return `Você está em dia. A simulação anda sozinha (${c.automatico.dias_por_execucao || 1} dia útil a cada ${c.automatico.intervalo || "30 min"}): o próximo dia aparece aqui sem recarregar.`;
  return "Você está em dia. O próximo dia aparece quando a simulação avançar.";
}

function resultadoDia(dia, c) {
  const r = dia?.resumo;
  if (!r) return `<p class="vazio">Sem resultado registrado.</p>`;
  const anterior = PLAY.i > 0 ? (c.P.historico || []).find((h) => h.data === PLAY.datas[PLAY.i - 1]) : null;
  const vsCdi = anterior ? (r.retorno_dia - (r.bench / anterior.bench - 1)) : null;
  const decididas = (dia.ata || []).filter((f) => f.tipo === "decisao" || f.tipo === "conselho");
  const pesos = Object.entries(r.pesos || {});
  return `
    <div class="mini-kpis">
      <div><span class="rot">Cota</span><strong>${num(r.cota, 6)}</strong><span class="det ${sinal(r.retorno_dia)}">dia ${pct(r.retorno_dia)}</span></div>
      <div><span class="rot">Contra o CDI no dia</span><strong class="${sinal(vsCdi)}">${pct(vsCdi, 3)}</strong><span class="det">desde o início ${pct(r.cota - 1)} vs ${pct(r.bench - 1)}</span></div>
      <div><span class="rot">Patrimônio</span><strong>${mi(r.pl)}</strong><span class="det">fluxo ${brl(r.fluxo)}</span></div>
      <div><span class="rot">Caixa da gestora</span><strong class="${sinal(r.caixa_gestora)}">${mi(r.caixa_gestora)}</strong><span class="det">${r.incidentes_abertos} incidente(s) · cred. ${pctSimples(r.credibilidade)}</span></div>
    </div>
    <div class="pesos">${pesos.map(([a, w], k) => `<span style="width:${(w * 100).toFixed(2)}%;--cor:var(--serie-${k + 1})" title="${esc(c.P.nomes?.ativos?.[a] || a)} ${pctSimples(w, 1)}"></span>`).join("")}</div>
    <div class="legenda caixas">${pesos.map(([a, w], k) => `<span><i style="--cor:var(--serie-${k + 1})"></i>${esc(c.P.nomes?.ativos?.[a] || a)} ${pctSimples(w)}</span>`).join("")}</div>
    <h3 style="margin-top:14px">${decididas.length ? `${decididas.length} decisão(ões) no dia` : "Ninguém mudou nada"}</h3>
    ${decididas.length ? `<ul class="lista decididas">${decididas.map((f) => `<li><span class="quando">${esc(f.hora)}</span><div><b class="area-cor ${esc(f.area)}">${esc(f.quem)}</b> ${textoFala(f.texto)}</div></li>`).join("")}</ul>` : `<p class="vazio">Os times mantiveram ações, estratégias e carteira.</p>`}`;
}

function atualizarBotaoPlay() {
  const b = $("#pl-play");
  if (!b) return;
  if (PLAY.fim && PLAY.i >= PLAY.datas.length - 1) b.textContent = "↺ Rever o dia";
  else b.textContent = PLAY.tocando ? "⏸ Pausar" : "▶ Continuar";
}

function controlePlayer(acao) {
  if (acao === "ant") return irPara(PLAY.i - 1);
  if (acao === "prox") return irPara(PLAY.i + 1);
  if (acao === "play") {
    if (PLAY.fim) { PLAY.tocando = true; return PLAY.i >= PLAY.datas.length - 1 ? irPara(PLAY.i) : irPara(PLAY.i + 1); }
    PLAY.tocando = !PLAY.tocando;
    atualizarBotaoPlay();
    passo();
  }
}

// chegou dia novo enquanto a página estava aberta: o player continua sozinho se estava esperando
function novosDias(c) {
  if (PLAY.cen !== c.id || !$("#pl-feed")) return;
  const antes = PLAY.datas.length;
  PLAY.datas = c.P?.datas || PLAY.datas;
  $("#pl-linha").max = Math.max(0, PLAY.datas.length - 1);
  $("#pl-pos").textContent = `Dia ${PLAY.i + 1} de ${PLAY.datas.length} · ${c.nome}`;
  if (PLAY.datas.length > antes && PLAY.fim && PLAY.seguir && PLAY.tocando) {
    mostrarEspera(`Chegou ${dataBR(PLAY.datas[PLAY.i + 1])}: os times estão entrando na sala…`);
    PLAY.timer = setTimeout(() => irPara(PLAY.i + 1), 2500);
  } else if (PLAY.fim && PLAY.i >= PLAY.datas.length - 1) {
    mostrarEspera(proximoDiaTexto(c));
  }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-pl]");
  if (b) controlePlayer(b.dataset.pl);
});
document.addEventListener("change", (e) => {
  if (e.target.id === "pl-vel") { PLAY.vel = Number(e.target.value); gravar("capivara-vel", e.target.value); passo(); }
  if (e.target.id === "pl-seguir") { PLAY.seguir = e.target.checked; gravar("capivara-seguir", PLAY.seguir ? "1" : "0"); if (PLAY.fim) terminarDia(); }
  if (e.target.id === "pl-linha") { PLAY.tocando = true; irPara(Number(e.target.value)); }
});

const VISOES = { aovivo, hoje, extracao, dashboards, executivos, processos };

// ------------------------------------------------------------------ navegação
function rota() {
  const h = location.hash.replace(/^#\/?/, "");
  if (VISOES[h]) return { cenario: "ao-vivo", aba: h }; // links antigos (#extracao)
  const [cen, aba, data] = h.split("/");
  if (!cen || cen === "central" || !CENARIOS.some((c) => c.id === cen)) return { cenario: null };
  return { cenario: cen, aba: VISOES[aba] ? aba : "aovivo", data: /^\d{4}-\d{2}-\d{2}$/.test(data || "") ? data : null };
}

function nav(r) {
  const nivelDe = (c) => pior([situacao(c).nivel, ...Object.values(c.P?.status_areas || {}).map((s) => s.nivel)]);
  $("#nav-cenarios").innerHTML = `<a href="#/" aria-current="${r.cenario ? "false" : "page"}">Central</a>` + CENARIOS.map((c) => {
    const n = nivelDe(c);
    return `<a href="#/${esc(c.id)}" aria-current="${r.cenario === c.id ? "page" : "false"}"><b class="ponto ${n}" title="${NIVEL[n].rotulo}" aria-label="${NIVEL[n].rotulo}">${NIVEL[n].icone}</b>${esc(c.nome)}</a>`;
  }).join("");
  const abas = $("#nav-abas");
  abas.hidden = !r.cenario || !C?.P;
  if (!abas.hidden) abas.innerHTML = ABAS.map(([id, nome]) => `<a href="#/${esc(r.cenario)}/${id}" aria-current="${r.aba === id ? "page" : "false"}">${id === "aovivo" ? `<span class="pulso" aria-hidden="true"></span>` : ""}${nome}</a>`).join("");
}

let MONTADO = null; // a tela do ao vivo não é redesenhada quando os dados mudam: o player continua tocando
function render(forcar = false) {
  const r = rota();
  C = r.cenario ? CENARIOS.find((c) => c.id === r.cenario) : null;
  P = C?.P || null;
  nav(r);
  const chave = `${r.cenario}/${r.aba}/${r.data || ""}`;
  if (C && P && r.aba === "aovivo") {
    $("#sub").textContent = `${C.nome} · reuniões dos times`;
    if (MONTADO === chave && !forcar && $("#pl-feed")) return novosDias(C);
    MONTADO = chave;
    $("#conteudo").innerHTML = aovivo();
    iniciarPlayer(C, r.data);
    return;
  }
  MONTADO = chave;
  if (PLAY.timer) clearTimeout(PLAY.timer);
  GRAFICOS = [];
  if (!C) {
    $("#sub").textContent = "Central · todos os cenários";
    $("#conteudo").innerHTML = central();
  } else if (!P) {
    $("#sub").textContent = `${C.nome} · ainda não começou`;
    $("#conteudo").innerHTML = cartaoCenario(C);
  } else {
    $("#sub").textContent = `${C.nome} · fechamento de ${dataBR(P.data_referencia)}`;
    $("#conteudo").innerHTML = VISOES[r.aba]();
  }
}

function avisar(texto) {
  const t = $("#aviso-copia");
  t.textContent = texto; t.hidden = false;
  clearTimeout(avisar.t); avisar.t = setTimeout(() => { t.hidden = true; }, 4000);
}

document.addEventListener("click", async (e) => {
  const filtro = e.target.closest("[data-filtro]");
  if (filtro) { FILTRO = filtro.dataset.filtro; render(); return; }
  const copiar = e.target.closest("[data-copiar]");
  if (copiar) {
    const texto = copiar.dataset.copiar;
    try { await navigator.clipboard.writeText(texto); avisar(`"${texto}" copiado: cole como comentário na issue de controle.`); } catch (_) { avisar(`Comente "${texto}" na issue de controle.`); }
    window.open(copiar.dataset.abrir, "_blank", "noopener");
  }
});
window.addEventListener("hashchange", () => CENARIOS.length && render());
let redim;
window.addEventListener("resize", () => { clearTimeout(redim); redim = setTimeout(() => CENARIOS.length && rota().aba !== "aovivo" && render(), 150); });

// ------------------------------------------------------------------ atualização sozinha (adeus, Shift+F5)
// versao.json muda a cada fechamento/avanço publicado. Dado novo: recarrega só os JSONs e redesenha.
// Código novo (`codigo`): abre a página de novo por um endereço inédito, o que fura o cache do navegador.
const ESTADO = { conferido: null, paineis: null, erro: false };
function frescor() {
  const el = $("#frescor");
  if (!el) return;
  const quando = ESTADO.conferido ? haQuanto(ESTADO.conferido.toISOString()) : "";
  el.className = `frescor ${ESTADO.erro ? "erro" : ""}`;
  el.innerHTML = ESTADO.erro ? "sem conexão" : `<span class="pulso" aria-hidden="true"></span>${quando === "agora" ? "atualizado agora" : `conferido ${quando}`}`;
}

async function conferirVersao() {
  if (String(window.VERSAO || "").startsWith("__")) return; // aberto direto do repositório (desenvolvimento)
  let v;
  try { v = await json("versao.json"); ESTADO.erro = false; } catch (_) { ESTADO.erro = true; frescor(); return; }
  ESTADO.conferido = new Date();
  if (v.codigo && v.codigo !== window.CODIGO) {
    let tentou = null;
    try { tentou = sessionStorage.getItem("capivara-codigo"); sessionStorage.setItem("capivara-codigo", v.codigo); } catch (_) { /* tudo bem */ }
    if (tentou !== v.codigo) { location.replace(`${location.pathname}?v=${v.codigo}${location.hash}`); return; }
  }
  const mudou = JSON.stringify(v.paineis) !== JSON.stringify(ESTADO.paineis);
  if (ESTADO.paineis && mudou) {
    CENARIOS = await carregarCenarios();
    VIVO = await consultarGitHub(true);
    render();
    avisar("Dados novos chegaram.");
  }
  ESTADO.paineis = v.paineis;
  frescor();
}

carregarCenarios().then(async (lista) => {
  CENARIOS = lista;
  const algum = lista.find((c) => c.P);
  $("#aviso").textContent = algum?.P.aviso || "";
  render();
  conferirVersao();
  VIVO = await consultarGitHub();
  if (rota().aba !== "aovivo") render();
  setInterval(() => { if (!document.hidden) conferirVersao(); }, 60000);
  setInterval(frescor, 15000);
  setInterval(async () => {
    if (document.hidden) return;
    VIVO = await consultarGitHub(true);
    if (rota().aba !== "aovivo") render(); else nav(rota());
  }, 180000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) conferirVersao(); });
}).catch((e) => {
  $("#sub").textContent = "sem dados";
  $("#conteudo").innerHTML = `<div class="cartao"><p class="vazio">Não foi possível carregar os painéis: ${esc(e.message)}</p></div>`;
});
