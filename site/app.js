"use strict";
// Capivara Asset · painéis. Duas coisas separadas, com o mesmo motor:
// - Experimento: a empresa funcionando no presente, um dia útil por vez (fechamento.yml, seg–sex 08h);
// - Simulação: a mesma empresa refazendo 2026, um dia por clique, para testar o experimento.
// Cada dia é lido de dias/AAAA-MM-DD.json: o rastro (o que cada etapa recebeu, a regra, a conta e a origem de cada
// número) e a ata (as falas, cada uma apontando para o bloco do rastro que a sustenta).
const REPO = "GloedenJoao/profissional";
const GH = `https://github.com/${REPO}`;
const API = `https://api.github.com/repos/${REPO}`;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, casas = 2) => (v == null || Number.isNaN(v) ? "—" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }).replace(/^-/, "−"));
const pct = (v, casas = 2, sinal = false) => (v == null ? "—" : `${sinal && v > 0.0000001 ? "+" : ""}${fmt(v * 100, casas)}%`.replace(/^\+?−0,0+%$/, "0,00%"));
const pp = (v, casas = 2) => (v == null ? "—" : `${v > 0.0000001 ? "+" : ""}${fmt(v * 100, casas)} p.p.`);
const mi = (v, casas = 1) => (v == null ? "—" : `R$ ${fmt(v / 1e6, casas)} mi`.replace("R$ −", "−R$ "));
const brl = (v) => (v == null ? "—" : `R$ ${fmt(v, 0)}`.replace("R$ −", "−R$ "));
const dataBR = (iso) => (iso ? String(iso).slice(0, 10).split("-").reverse().join("/") : "—");
const dm = (iso) => dataBR(iso).slice(0, 5);
const mesAno = (iso) => (iso ? `${["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][Number(iso.slice(5, 7)) - 1]}/${iso.slice(2, 4)}` : "—");
const cls = (v) => (v == null ? "" : v >= 0 ? "pos" : "neg");
const SEMANA = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];
const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const porExtenso = (iso) => { const d = new Date(`${iso}T12:00:00Z`); return `${SEMANA[d.getUTCDay()]}, ${d.getUTCDate()} de ${MESES[d.getUTCMonth()]} de ${d.getUTCFullYear()}`; };

const ORIGEM = {
  real: ["real", "dado público, com fonte e data"],
  derivado: ["derivado", "conta feita só com dados reais"],
  simulado: ["simulado", "modelo ou sorteio da empresa fictícia"],
  decisao: ["decisão", "escolha de um time, pela regra mostrada"],
  conselho: ["conselho", "diretriz humana, por cima do time"],
  regra: ["regra", "parâmetro da política ou do motor"],
};
const ETAPAS = [
  ["heranca", "07:00", "Herança", "De onde partimos hoje?", "o fechamento de ontem: carteira, incidentes, equipe, caixa"],
  ["extracao", "08:00", "Extração", "Que dados chegaram e quais a empresa pode usar?", "Bia e Téo conferem as 6 fontes reais, tratam incidentes e liberam as séries"],
  ["dashboards", "09:00", "Dashboards", "Que números vão para o comitê, e com que confiança?", "Caio e Lia montam o painel e decidem o que fazer com o dado que faltou"],
  ["comite", "10:00", "Comitê", "Mexemos na carteira, na equipe ou no orçamento?", "Helena, Rafael e Marta decidem só com o painel"],
  ["fundo", "18:00", "Fundo", "Quanto o fundo ganhou ou perdeu, e por quê?", "o administrador marca a carteira com os preços oficiais do dia"],
  ["empresa", "18:30", "Empresa", "A gestora se paga?", "taxa de administração contra os custos da casa"],
  ["verificacoes", "19:00", "Verificações", "O motor fez tudo certo?", "8 conferências de integridade, todo dia"],
];
const NOME_ETAPA = Object.fromEntries(ETAPAS.map((e) => [e[0], e[2]]));
const ROTULO_ST = { ok: "ok", aviso: "atenção", ruim: "problema", info: "início" };
const PRODUTOS_INFO = {
  experimento: { nome: "Experimento", cls: "exp", papel: "A empresa funcionando de verdade, no presente. Fecha sozinha de segunda a sexta às 08h com os dados reais do dia útil anterior." },
  simulacao: { nome: "Simulação", cls: "sim", papel: "A mesma empresa refazendo 2026 desde 1º de janeiro, um dia por clique. Serve para testar o experimento: ver cada etapa, conferir cada conta e comparar com quem não decide nada." },
};
const SECOES = [["dia", "Dia"], ["fundo", "Fundo"], ["dados", "Dados"], ["empresa", "Empresa"], ["validacao", "Validação"], ["regras", "Regras"]];

let PRODUTOS = {}; // {experimento: {id, nome, painel, dias, P}, simulacao: {...}}
const DIAS = new Map(); // cache dos dias: `${produto}:${data}` → registro
let ROTA = { produto: "inicio", secao: null, data: null };
let DIA_ATUAL = null; // o dia aberto na tela Dia

// ------------------------------------------------------------------ armazenamento local (só conveniências)
function ler(chave, padrao) { try { const v = localStorage.getItem(chave); return v == null ? padrao : v; } catch (_) { return padrao; } }
function gravar(chave, valor) { try { localStorage.setItem(chave, valor); } catch (_) { /* sem armazenamento: tudo bem */ } }
function lerSessao(chave) { try { return JSON.parse(sessionStorage.getItem(chave) || "null"); } catch (_) { return null; } }
function gravarSessao(chave, v) { try { sessionStorage.setItem(chave, JSON.stringify(v)); } catch (_) { /* tudo bem */ } }

function avisar(msg) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(avisar.t); avisar.t = setTimeout(() => { t.hidden = true; }, 4500);
}

// ------------------------------------------------------------------ carga
async function json(url, fresco = true) {
  const sep = url.includes("?") ? "&" : "?";
  const r = await fetch(fresco ? `${url}${sep}t=${Date.now()}` : url, { cache: fresco ? "no-store" : "default" });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function carregarProdutos() {
  let indice;
  try {
    indice = (await json("cenarios.json")).cenarios;
  } catch (_) {
    // site aberto direto do repositório (sem `python -m gestora site`)
    indice = [
      { id: "ao-vivo", modo: "diario", painel: "../dados/painel.json", dias: "../dados/dias/" },
      { id: "2026", modo: "simulacao", painel: "../cenarios/2026/dados/painel.json", dias: "../cenarios/2026/dados/dias/" },
    ];
  }
  const out = {};
  await Promise.all(indice.map(async (c) => {
    const produto = c.modo === "diario" ? "experimento" : "simulacao";
    if (out[produto]) return; // por enquanto, uma simulação só
    let P = null;
    if (c.painel) { try { P = await json(c.painel); } catch (_) { P = null; } }
    out[produto] = { ...c, produto, P };
  }));
  return out;
}

async function carregarDia(prod, data) {
  const chave = `${prod.produto}:${data}`;
  if (DIAS.has(chave)) return DIAS.get(chave);
  const reg = await json(`${prod.dias}${data}.json?v=${encodeURIComponent(window.VERSAO || "")}`, false).catch(() => json(`${prod.dias}${data}.json`));
  DIAS.set(chave, reg);
  return reg;
}

// ------------------------------------------------------------------ rotas
function lerRota() {
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  const p = h.split("/").filter(Boolean);
  // rotas antigas: #/ao-vivo/..., #/2026/aovivo/AAAA-MM-DD, #hoje
  if (p[0] === "ao-vivo") p[0] = "experimento";
  if (p[0] && /^\d{4}$/.test(p[0])) p[0] = "simulacao";
  if (p[1] === "aovivo" || p[1] === "hoje") p[1] = "dia";
  if (!["experimento", "simulacao"].includes(p[0])) return { produto: "inicio", secao: null, data: null };
  const secao = SECOES.some(([s]) => s === p[1]) ? p[1] : "dia";
  const data = /^\d{4}-\d{2}-\d{2}$/.test(p[2] || "") ? p[2] : null;
  return { produto: p[0], secao, data };
}

function navegar(hash) { if (location.hash !== hash) location.hash = hash; else render(); }

function marcarNavegacao() {
  document.body.dataset.produto = ROTA.produto;
  $$(".produtos a").forEach((a) => (a.dataset.produto === ROTA.produto ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  const nav = $("#secoes");
  if (ROTA.produto === "inicio") { nav.hidden = true; nav.innerHTML = ""; return; }
  nav.hidden = false;
  nav.innerHTML = SECOES.map(([s, n]) => `<a href="#/${ROTA.produto}/${s}" ${s === ROTA.secao ? 'aria-current="page"' : ""}>${n}</a>`).join("");
}

// ------------------------------------------------------------------ peças
const fmtTexto = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");
function celula(c) {
  if (c == null) return "";
  if (typeof c !== "object") return fmtTexto(c);
  const [nome, desc] = ORIGEM[c.o] || ["", ""];
  const dica = [nome && `${nome}: ${desc}`, c.dica].filter(Boolean).join(" · ");
  return `<span class="${c.o ? `o o-${c.o}` : ""}" ${dica ? `title="${esc(dica)}"` : ""}>${fmtTexto(c.v)}</span>`;
}
function bloco(b) {
  let corpo = "";
  if (b.tipo === "tabela") {
    // no celular cada linha vira um cartão (a coluna vai como rótulo de cada célula)
    corpo = `<div class="rolagem"><table class="empilha"><thead><tr>${b.colunas.map((c) => `<th scope="col">${esc(c)}</th>`).join("")}</tr></thead><tbody>${b.linhas.map((l) => `<tr>${l.map((c, k) => `<td data-rot="${esc(b.colunas[k] || "")}">${celula(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  } else if (b.tipo === "contas") {
    corpo = `<div class="contas">${b.linhas.map((l) => `<div><span>${esc(l.rot)}</span><span class="expr">${fmtTexto(l.expr || "")}</span><span class="valor">${celula({ v: l.valor, o: l.o })}</span></div>`).join("")}</div>`;
  } else if (b.tipo === "regras") {
    corpo = `<ul class="regras">${b.itens.map((i) => `<li>${fmtTexto(i)}</li>`).join("")}</ul>`;
  } else {
    corpo = `<p>${fmtTexto(b.texto)}</p>`;
  }
  return `<section class="bloco" data-bloco="${esc(b.id)}"><h4>${esc(b.titulo)}</h4>${corpo}${b.nota ? `<p class="nota">${fmtTexto(b.nota)}</p>` : ""}</section>`;
}
const kpi = (rot, val, det = "", c = "") => `<div class="cartao kpi"><div class="rot">${rot}</div><div class="val ${c}">${val}</div><div class="det">${det}</div></div>`;
const selo = (txt, c = "") => `<span class="selo ${c}">${esc(txt)}</span>`;
const externo = (href, txt, c = "botao") => `<a class="${c}" href="${esc(href)}" target="_blank" rel="noopener">${txt}</a>`;
const legendaOrigem = () => `<div class="legenda-origem">${Object.entries(ORIGEM).map(([k, [n, d]]) => `<span><span class="o o-${k}">${n}</span> <span class="d">${d}</span></span>`).join("")}</div>`;
const iniciais = (nome) => nome.split(" ").map((x) => x[0]).join("").slice(0, 2).toUpperCase();
function piorStatus(st) {
  const ordem = { ruim: 3, aviso: 2, ok: 1, info: 0 };
  return Object.entries(st || {}).filter(([k]) => k !== "heranca").reduce((a, [, v]) => (ordem[v] > ordem[a] ? v : a), "ok");
}

// ------------------------------------------------------------------ gráficos (SVG, com cursor e dica)
let GRAFICOS = [];
function grafico(series, { altura = 190, formato = (v) => fmt(v), zero = false, marcas = [] } = {}) {
  const W = Math.max(300, Math.min(1080, ($("#conteudo").clientWidth || 640) - 36)), H = altura;
  const m = { t: 12, r: 12, b: 24, l: 56 };
  const pts = series.flatMap((s) => s.pontos.filter((p) => p[1] != null));
  if (pts.length < 2) return `<p class="vazio">Histórico ainda curto para o gráfico.</p>`;
  const xs = [...new Set(pts.map((p) => p[0]))].sort();
  let lo = Math.min(...pts.map((p) => p[1])), hi = Math.max(...pts.map((p) => p[1]));
  if (zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  if (hi === lo) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const ix = new Map(xs.map((d, i) => [d, i]));
  const x = (d) => m.l + (ix.get(d) / Math.max(1, xs.length - 1)) * (W - m.l - m.r);
  const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const ticks = [lo + pad, (lo + hi) / 2, hi - pad];
  let svg = `<svg class="grafico" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map((s) => s.nome).join(", "))}">`;
  for (const t of ticks) svg += `<line class="eixo" x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${m.l - 6}" y="${y(t) + 4}" text-anchor="end">${esc(formato(t))}</text>`;
  if (zero && lo < 0 && hi > 0) svg += `<line class="zero" x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}"/>`;
  for (const i of [...new Set([0, Math.floor((xs.length - 1) / 2), xs.length - 1])]) {
    svg += `<text x="${x(xs[i])}" y="${H - 6}" text-anchor="${i === 0 ? "start" : i === xs.length - 1 ? "end" : "middle"}">${dm(xs[i])}${xs.length > 180 ? `/${xs[i].slice(2, 4)}` : ""}</text>`;
  }
  for (const d of marcas) if (ix.has(d)) svg += `<circle class="marca-dec" cx="${x(d)}" cy="${H - m.b + 1}" r="3.5"><title>${dataBR(d)}: o comitê mudou o alvo</title></circle>`;
  series.forEach((s, k) => {
    const cor = s.cor || `var(--serie-${k + 1})`;
    const d = s.pontos.filter((p) => p[1] != null).map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
    svg += `<path d="${d}" fill="none" stroke="${cor}" stroke-width="2" ${s.tracejado ? 'stroke-dasharray="5 4"' : ""} stroke-linejoin="round" stroke-linecap="round"/>`;
    const u = s.pontos.filter((p) => p[1] != null).at(-1);
    if (u) svg += `<circle cx="${x(u[0])}" cy="${y(u[1])}" r="3.5" fill="${cor}" stroke="var(--cartao)" stroke-width="2"/>`;
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
  const d = g.xs[i], cursor = box.querySelector(".cursor");
  cursor.setAttribute("x1", g.x(d)); cursor.setAttribute("x2", g.x(d)); cursor.setAttribute("visibility", "visible");
  const dica = box.querySelector(".dica");
  dica.innerHTML = `<div class="dica-data">${dataBR(d)}</div>` + g.series.map((s, k) => {
    const v = g.mapa[k].get(d);
    return v == null ? "" : `<div class="dica-linha"><i style="--cor:${s.cor || `var(--serie-${k + 1})`}"></i><strong>${esc(g.formato(v))}</strong><span>${esc(s.nome)}</span></div>`;
  }).join("");
  dica.hidden = false;
  const frac = g.x(d) / g.W;
  dica.style.left = frac > 0.6 ? "" : `calc(${(frac * 100).toFixed(1)}% + 12px)`;
  dica.style.right = frac > 0.6 ? `calc(${((1 - frac) * 100).toFixed(1)}% + 12px)` : "";
}
function esconderDica(box) { box.querySelector(".cursor")?.setAttribute("visibility", "hidden"); const d = box.querySelector(".dica"); if (d) d.hidden = true; }
document.addEventListener("pointermove", (e) => {
  const box = e.target.closest?.(".grafico-box");
  $$(".grafico-box").forEach((b) => b !== box && esconderDica(b));
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

// ------------------------------------------------------------------ início
function cartaoProduto(prod) {
  const info = PRODUTOS_INFO[prod.produto];
  const P = prod.P;
  const base = `<span class="etiqueta"><i class="ponto ${info.cls}"></i>${info.nome}</span><h2>${prod.produto === "experimento" ? "A empresa, ao vivo" : "Laboratório: 2026 de novo"}</h2><p class="papel">${info.papel}</p>`;
  if (!P) {
    return `<section class="cartao produto ${info.cls}">${base}<p class="vazio">Ainda não começou.</p>${prod.produto === "simulacao" ? `<div class="acoes" data-sim-slot>${botaoSimular()}</div>` : ""}</section>`;
  }
  const r = P.resumo, ref = P.referencia || {};
  const st = P.calendario?.at(-1);
  const verif = P.metricas ? `${P.metricas.verificacoes_ok}/${P.metricas.verificacoes_ok + P.metricas.verificacoes_falha}` : "—";
  let estado = "";
  if (prod.produto === "experimento") {
    estado = `<p class="det">Último dia processado: <b>${dataBR(P.data_referencia)}</b>. Próximo fechamento ${P.proximo_fechamento_em ? `em ${dataBR(P.proximo_fechamento_em)} às 08h` : "no próximo dia útil"}, sozinho.</p>`;
  } else {
    const prog = progressoSimulacao(P);
    estado = `<p class="det">Está em <b>${dataBR(P.data_referencia)}</b> · ${prog.feitos} de ${prog.total} dias úteis de 2026 até ontem.</p><div class="progresso" role="progressbar" aria-valuenow="${Math.round(prog.frac * 100)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${(prog.frac * 100).toFixed(1)}%"></span></div>`;
  }
  return `<section class="cartao produto ${info.cls}">${base}${estado}
    <div class="mini-kpis">
      <div><b class="${cls(r.retorno_total)}">${pct(r.retorno_total, 2, true)}</b><span>fundo desde o início</span></div>
      <div><b>${pct(r.cdi_total, 2, true)}</b><span>CDI no mesmo período</span></div>
      <div><b class="${cls(ref.valor_decisoes)}">${pct(ref.valor_decisoes, 2, true)}</b><span>valor das decisões</span></div>
      <div><b>${verif}</b><span>verificações ok</span></div>
    </div>
    <div class="acoes"><a class="botao prim" style="--acento:var(--${info.cls})" href="#/${prod.produto}/dia">Ver o último dia${st ? ` (${dm(st.data)})` : ""}</a>${prod.produto === "simulacao" ? `<span data-sim-slot>${botaoSimular()}</span>` : ""}<a class="botao leve" href="#/${prod.produto}/validacao">Validação</a></div>
    ${prod.produto === "experimento" ? "<div data-fech></div>" : ""}
  </section>`;
}

function telaInicio() {
  const e = PRODUTOS.experimento, s = PRODUTOS.simulacao;
  return `
  <section class="cartao hero">
    <h1>Uma gestora fictícia, dados reais, cada passo à vista.</h1>
    <p>A Capivara Asset roda só no GitHub. Todo dia útil a Extração traz os dados públicos (Banco Central, Tesouro Direto, B3, Yahoo), os Dashboards montam o painel, o Comitê decide com esse painel e o fundo sente o resultado no preço de mercado. Cada etapa registra o que recebeu, a regra que aplicou e a conta que fez: nenhuma fala sem número por trás.</p>
  </section>
  <div class="grade-2">${e ? cartaoProduto(e) : ""}${s ? cartaoProduto(s) : ""}</div>
  ${execucaoHTML()}
  <section class="cartao"><h2>Como um dia acontece</h2>
    <div class="etapas-mapa">${ETAPAS.map(([id, h, n, q, d]) => `<div data-e="${id}" style="--ec:var(--e-${id})"><span class="h">${h}</span><b>${n}</b><p><em>${q}</em> ${d}.</p></div>`).join("")}</div>
    <p class="det" style="margin-top:10px">As reuniões da manhã só conhecem o que estava publicado às 08h (o motor corta cada série pelo calendário real de publicação). O fundo é marcado às 18h com os preços de fechamento.</p>
  </section>
  <section class="cartao"><h2>De onde vem cada número</h2>${legendaOrigem()}
    <p class="det" style="margin-top:10px">Real é real: cotações, taxas e índices vêm das fontes públicas. O que é simulado (a empresa, os cotistas e o teste de estresse que sorteia falhas nas fontes) aparece como simulado, com a conta ou o sorteio à vista.</p>
  </section>
  <section class="cartao"><h2>Experimento × Simulação</h2>
    <div class="rolagem"><table><thead><tr><th></th><th>Experimento</th><th>Simulação</th></tr></thead><tbody>
      <tr><td><b>O que é</b></td><td>a empresa no presente</td><td>a mesma empresa refazendo 2026</td></tr>
      <tr><td><b>Para que serve</b></td><td>descobrir se uma gestora tocada por regras sobre dados reais se sustenta</td><td>testar o experimento antes de confiar nele</td></tr>
      <tr><td><b>Quem faz andar</b></td><td>sozinha, seg–sex 08h</td><td>você: "Simular próximo dia"</td></tr>
      <tr><td><b>Motor</b></td><td colspan="2">o mesmo (<code>gestora/</code>), as mesmas regras (<code>politicas.json</code>)</td></tr>
    </tbody></table></div>
  </section>`;
}

function progressoSimulacao(P) {
  const fer = new Set(P.feriados || []);
  const util = (iso) => { const w = new Date(`${iso}T12:00:00Z`).getUTCDay(); return w !== 0 && w !== 6 && !fer.has(iso); };
  const soma = (iso, n) => { const d = new Date(`${iso}T12:00:00Z`); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const hoje = new Date().toLocaleString("sv-SE", { timeZone: "America/Sao_Paulo" }).slice(0, 10);
  let ontem = soma(hoje, -1); while (!util(ontem)) ontem = soma(ontem, -1);
  const contar = (a, b) => { let n = 0; for (let d = soma(a, 1); d <= b; d = soma(d, 1)) if (util(d)) n++; return n; };
  const total = contar(P.cenario.inicio, ontem), feitos = contar(P.cenario.inicio, P.data_referencia);
  return { total, feitos, frac: total ? Math.min(1, feitos / total) : 1, fim: feitos >= total };
}

// ------------------------------------------------------------------ dia
function cabecalhoProduto(prod, titulo, sub = "") {
  const info = PRODUTOS_INFO[prod.produto];
  return `<div class="titulo-pag"><div><span class="etiqueta"><i class="ponto ${info.cls}"></i>${info.nome}</span><h1>${titulo}</h1>${sub ? `<p>${sub}</p>` : ""}</div></div>`;
}

async function telaDia(prod) {
  const P = prod.P;
  if (!P) return semDados(prod);
  const datas = (P.calendario || []).map((c) => c.data);
  if (!datas.length) return semDados(prod);
  const data = ROTA.data && datas.includes(ROTA.data) ? ROTA.data : datas.at(-1);
  let dia;
  try { dia = await carregarDia(prod, data); DIA_ATUAL = dia; } catch (e) { return `<div class="cartao"><p class="vazio">Não consegui carregar o dia ${dataBR(data)}: ${esc(e.message)}</p></div>`; }
  const i = datas.indexOf(data), ant = datas[i - 1], prox = datas[i + 1];
  const ultimo = !prox;
  const r = dia.resumo || {};
  const st = r.status || {};
  const fita = (P.calendario || []).map((c) => `<a href="#/${prod.produto}/dia/${c.data}" class="${piorStatus(c.status)} ${c.alocacao ? "dec" : ""}" ${c.data === data ? 'aria-current="true"' : ""} title="${dataBR(c.data)} · cota ${pct(c.retorno, 2, true)}${c.alocacao ? " · comitê mudou o alvo" : ""}${c.verif?.[0] !== c.verif?.[1] ? " · verificação falhou" : ""}" aria-label="${dataBR(c.data)}"></a>`).join("");
  const trilho = ETAPAS.map(([id, h, n]) => `<a href="#etapa-${id}" data-e="${id}" data-ir="${id}"><span class="h">${h}</span><b>${n}</b><span class="st ${st[id] || "info"}">${ROTULO_ST[st[id]] || "—"}</span></a>`).join("");
  const antigo = !dia.rastro;
  const valorDec = r.cota_ref ? r.cota / r.cota_ref - 1 : null;
  let html = `
  <section class="cab-dia">
    ${cabecalhoProduto(prod, "")}
    <div class="navdia">
      <h1>${porExtenso(data)}<small>dia útil nº ${dia.dia_numero ?? i + 1} desde a fundação em ${dataBR(P.cenario?.inicio)}${dia.decisao?.intervencao ? " · com diretriz do conselho" : ""}</small></h1>
      <div class="acoes">
        ${ant ? `<a class="botao pequeno" href="#/${prod.produto}/dia/${ant}" aria-label="Dia anterior">‹ ${dm(ant)}</a>` : ""}
        ${prox ? `<a class="botao pequeno" href="#/${prod.produto}/dia/${prox}" aria-label="Próximo dia">${dm(prox)} ›</a>` : ""}
        ${!ultimo ? `<a class="botao pequeno" href="#/${prod.produto}/dia">Último ⇥</a>` : ""}
      </div>
    </div>
    <div class="fita" aria-label="Todos os dias: cor = pior etapa do dia; traço = o comitê mudou o alvo">${fita}</div>
    ${antigo ? "" : `<div class="trilho" aria-label="Etapas do dia">${trilho}</div>`}
    ${antigo ? "" : `<div class="player">
      <button class="botao prim" type="button" data-play>▶ Assistir o dia</button>
      <button class="botao leve" type="button" data-pular hidden>⏭ Mostrar tudo</button>
      <span class="vel" role="group" aria-label="Velocidade">${[1, 2, 4].map((v) => `<button type="button" data-vel="${v}" aria-pressed="${String(v === velocidade())}">${v}×</button>`).join("")}</span>
      <span class="det">ou role a página: tudo já está aqui, com as contas de cada fala.</span>
    </div>`}
  </section>
  <section class="resumo-dia">
    ${kpi("Cota no fechamento", fmt(r.cota, 6), `<span class="${cls(r.retorno_dia)}">${pct(r.retorno_dia, 2, true)} no dia</span>`)}
    ${kpi("Patrimônio", mi(r.pl), `fluxo de cotistas ${mi(r.fluxo, 2)}`)}
    ${kpi("Fundo × referência", `<span class="${cls(valorDec)}">${pct(valorDec, 2, true)}</span>`, "o que as decisões acrescentaram até este dia")}
    ${kpi("Verificações", r.verificacoes_total ? `${r.verificacoes_ok}/${r.verificacoes_total}` : "—", r.verificacoes_ok === r.verificacoes_total ? "o motor conferiu tudo" : "<span class=neg>alguma conta não fechou</span>", r.verificacoes_ok === r.verificacoes_total ? "pos" : "neg")}
  </section>`;
  if (prod.produto === "experimento" && ultimo) html += `<section class="cartao" data-proximo><h2>Próximo dia</h2><p>O dia útil seguinte (${dataBR(P.proximo_dia_util)}) é processado sozinho ${P.proximo_fechamento_em ? `em ${dataBR(P.proximo_fechamento_em)} às 08h` : "na manhã seguinte"}, quando os dados reais dele já saíram. Esta página confere a cada minuto e mostra o dia novo assim que ele chega.</p><div class="acoes" style="margin-top:8px">${externo(`${GH}/actions/workflows/fechamento.yml`, "Execuções do fechamento ↗", "botao leve pequeno")}</div><div data-fech></div></section>`;
  if (prod.produto === "simulacao" && ultimo) html += `<section class="cartao" data-proximo><h2>Próximo dia</h2><div class="acoes" data-sim-slot>${botaoSimular()}</div><p class="det" style="margin-top:8px">${textoProximo(P)}</p>${execucaoHTML(true)}</section>`;
  if (antigo) {
    html += `<section class="cartao aviso-motor"><p>Este dia foi simulado por uma versão antiga do motor, sem o rastro das contas. O próximo fechamento (ou o workflow de publicação) refaz o histórico com o motor atual.</p></section>`;
    html += `<section class="cartao"><h2>Ata</h2><ol class="conversa">${(dia.ata || []).map((f) => falaHTML(f, {})).join("")}</ol></section>`;
    return html;
  }
  const blocos = Object.fromEntries(dia.rastro.flatMap((e) => e.blocos.map((b) => [b.id, b])));
  for (const et of dia.rastro) {
    const falas = (dia.ata || []).filter((f) => f.etapa === et.id);
    const ordem = ETAPAS.find((x) => x[0] === et.id);
    const sec = ordem ? ordem[4] : "";
    const todos = et.blocos.map(bloco).join("");
    html += `<section class="cartao etapa" id="etapa-${et.id}" data-e="${et.id}" data-etapa="${et.id}">
      <header><div><div class="h">${et.hora} · ${esc(et.titulo)}${sec ? ` · <span class="det">${esc(sec)}</span>` : ""}</div><h2>${esc(et.pergunta)}</h2></div>
        <div class="resumo"><span class="selo ${et.status}">${ROTULO_ST[et.status] || et.status}</span><div class="det">${esc(et.resumo)}</div></div></header>
      ${falas.length ? `<ol class="conversa">${falas.map((f) => falaHTML(f, blocos)).join("")}</ol>
      <details class="dados" ${et.id === "verificacoes" ? "open" : ""}><summary>Todos os dados e contas desta etapa (${et.blocos.length})</summary>${todos}</details>` : todos}
    </section>`;
  }
  html += `<section class="cartao"><h2>Como ler</h2>${legendaOrigem()}<p class="det" style="margin-top:8px">Passe o dedo (ou o mouse) sobre um número para ver de onde ele vem. Cada fala tem o botão "Ver as contas" com a tabela que a sustenta.</p></section>`;
  return html;
}

function falaHTML(f, blocos) {
  const b = f.bloco && blocos[f.bloco];
  return `<li class="fala ${esc(f.tipo)}" data-fala>
    <span class="avatar ${esc(f.area)} ${f.tipo === "conselho" ? "conselho" : ""}" aria-hidden="true">${esc(iniciais(f.quem))}</span>
    <div class="balao"><div class="quem"><b>${esc(f.quem)}</b><span>${esc(f.papel)}</span><span>· ${esc(f.hora)}</span>${f.tipo === "decisao" ? selo("decisão", "info") : f.tipo === "alerta" ? selo("alerta", "aviso") : f.tipo === "conselho" ? selo("conselho") : ""}</div>
      <div class="txt">${fmtTexto(f.texto)}</div>
      ${b ? `<button class="ver-contas" type="button" aria-expanded="false" data-ver="${esc(b.id)}">Ver as contas: ${esc(b.titulo)}</button><div class="contas-inline" hidden></div>` : ""}
    </div></li>`;
}

document.addEventListener("click", async (e) => {
  const v = e.target.closest("[data-ver]");
  if (v) {
    const caixa = v.nextElementSibling;
    const aberto = v.getAttribute("aria-expanded") === "true";
    if (!aberto && !caixa.innerHTML) {
      const b = DIA_ATUAL?.rastro?.flatMap((et) => et.blocos).find((x) => x.id === v.dataset.ver);
      if (b) caixa.innerHTML = bloco(b);
    }
    caixa.hidden = aberto;
    v.setAttribute("aria-expanded", String(!aberto));
  }
  const ir = e.target.closest("[data-ir]");
  if (ir) {
    e.preventDefault();
    const alvo = $(`#etapa-${ir.dataset.ir}`);
    if (alvo && !alvo.classList.contains("escondida")) alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

function semDados(prod) {
  const sim = prod.produto === "simulacao";
  return `${cabecalhoProduto(prod, sim ? "A simulação ainda não começou" : "Sem dados ainda")}
  <section class="cartao"><p>${sim ? "O primeiro clique funda a empresa em 1º de janeiro de 2026 e simula o primeiro dia útil." : "O primeiro fechamento ainda não rodou."}</p>
  ${sim ? `<div class="acoes" data-sim-slot>${botaoSimular()}</div>${execucaoHTML(true)}` : ""}</section>`;
}

// ------------------------------------------------------------------ modo Assistir (toca o dia etapa por etapa)
const velocidade = () => Number(ler("capivara-vel", "1")) || 1;
let PLAY = null;
function prepararPlayer() {
  const play = $("[data-play]");
  if (!play) return;
  play.addEventListener("click", () => (PLAY && !PLAY.pausado ? pausar() : PLAY ? continuar() : assistir()));
  $("[data-pular]").addEventListener("click", mostrarTudo);
  $$("[data-vel]").forEach((b) => b.addEventListener("click", () => {
    gravar("capivara-vel", b.dataset.vel);
    $$("[data-vel]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  }));
  if (lerSessao("capivara-autoplay") === `${ROTA.produto}:${ROTA.data || "ultimo"}`) { gravarSessao("capivara-autoplay", null); assistir(); }
}
function assistir() {
  const falas = $$("[data-fala]");
  const etapas = $$("[data-etapa]");
  PLAY = { falas, i: 0, pausado: false };
  falas.forEach((f) => f.classList.add("escondida"));
  etapas.forEach((et, k) => et.classList.toggle("escondida", k > 0));
  $$(".trilho a").forEach((a, k) => a.classList.toggle("esperando", k > 0));
  $("[data-play]").textContent = "❚❚ Pausar";
  $("[data-pular]").hidden = false;
  etapas[0]?.scrollIntoView({ behavior: "smooth", block: "start" });
  PLAY.t = setTimeout(passo, 400);
}
function passo() {
  if (!PLAY || PLAY.pausado) return;
  const f = PLAY.falas[PLAY.i];
  if (!f) return terminar();
  const et = f.closest("[data-etapa]");
  if (et.classList.contains("escondida")) {
    et.classList.remove("escondida");
    $$(".trilho a").forEach((a) => { if (a.dataset.ir === et.dataset.etapa) { a.classList.remove("esperando"); a.classList.add("ativa"); } else a.classList.remove("ativa"); });
    // etapas sem fala (Herança) aparecem junto com a seguinte
  }
  const lista = f.parentElement;
  const dig = document.createElement("li");
  dig.className = "fala"; dig.innerHTML = `<span class="avatar ${f.querySelector(".avatar").className.split(" ").slice(1).join(" ")}">${f.querySelector(".avatar").textContent}</span><div class="balao digitando" aria-label="digitando"><i></i><i></i><i></i></div>`;
  lista.insertBefore(dig, f);
  dig.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const texto = f.querySelector(".txt").textContent.length;
  const espera = Math.min(2600, 500 + texto * 8) / velocidade();
  PLAY.t = setTimeout(() => {
    dig.remove();
    f.classList.remove("escondida"); f.classList.add("nova");
    f.scrollIntoView({ behavior: "smooth", block: "nearest" });
    PLAY.i += 1;
    PLAY.t = setTimeout(passo, 350 / velocidade());
  }, espera);
}
function pausar() { if (!PLAY) return; PLAY.pausado = true; clearTimeout(PLAY.t); $$(".digitando").forEach((d) => d.closest("li").remove()); $("[data-play]").textContent = "▶ Continuar"; }
function continuar() { if (!PLAY) return; PLAY.pausado = false; $("[data-play]").textContent = "❚❚ Pausar"; passo(); }
function mostrarTudo() {
  if (PLAY) clearTimeout(PLAY.t);
  $$(".digitando").forEach((d) => d.closest("li").remove());
  $$("[data-fala]").forEach((f) => f.classList.remove("escondida"));
  $$("[data-etapa]").forEach((et) => et.classList.remove("escondida"));
  $$(".trilho a").forEach((a) => a.classList.remove("esperando", "ativa"));
  terminar(false);
}
function terminar(aviso = true) {
  PLAY = null;
  const b = $("[data-play]"); if (b) b.textContent = "▶ Assistir de novo";
  const p = $("[data-pular]"); if (p) p.hidden = true;
  $$(".trilho a").forEach((a) => a.classList.remove("ativa", "esperando"));
  if (aviso) {
    avisar("Fim do dia: cota fechada e verificações feitas.");
    const prox = $("[data-proximo]");
    if (prox) prox.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

// ------------------------------------------------------------------ fundo
function serieRebase(h, campo) { const b = h[0]?.[campo]; return h.map((x) => [x.data, x[campo] != null && b ? (x[campo] / b - 1) * 100 : null]); }
function telaFundo(prod) {
  const P = prod.P;
  if (!P) return semDados(prod);
  const h = P.historico || [], r = P.resumo, e = P.executivos, ref = P.referencia || {};
  const base = [{ data: P.fundacao?.data || P.cenario?.inicio, cota: 1, bench: 1, cota_ref: 1 }, ...h];
  const marcas = (P.calendario || []).filter((c) => c.alocacao).map((c) => c.data);
  const neutro = Object.fromEntries((P.fundacao?.posicoes || []).map((p) => [p.ativo, p.peso]));
  const aloc = Object.keys(e.alvo).map((a) => {
    const [mn, mx] = e.limites[a];
    return `<div class="aloc"><span>${esc(P.nomes.ativos[a])}${e.congelados.includes(a) ? " ❄" : ""}</span>
      <div class="faixa" title="faixa verde: limite ${pct(mn, 0)}–${pct(mx, 0)} · barra: peso atual · traço: alvo · tracejado: neutro">
        <span class="lim" style="left:${mn * 100}%;width:${(mx - mn) * 100}%"></span><span class="atual" style="width:${e.pesos[a] * 100}%"></span>
        ${neutro[a] != null ? `<span class="neutro" style="left:${neutro[a] * 100}%"></span>` : ""}<span class="alvo" style="left:${e.alvo[a] * 100}%"></span></div>
      <span class="det" style="text-align:right">${pct(e.pesos[a], 1)} → ${pct(e.alvo[a], 1)}</span></div>`;
  }).join("");
  const decs = (e.decisoes_recentes || []).filter((d) => d.alvo_antes);
  const tabelaDec = decs.length ? `<div class="rolagem"><table><thead><tr><th>Dia</th><th>Quem</th><th>Mudança no alvo</th></tr></thead><tbody>${decs.map((d) => {
    const mud = Object.keys(d.alvo).filter((a) => Math.abs(d.alvo[a] - d.alvo_antes[a]) > 1e-6).map((a) => `${esc(P.nomes.ativos[a].split(" (")[0])} ${pct(d.alvo_antes[a], 1)}→${pct(d.alvo[a], 1)}`).join("; ");
    return `<tr><td><a href="#/${prod.produto}/dia/${d.data}">${dataBR(d.data)}</a></td><td>${selo(d.autor, d.autor === "conselho" ? "" : "info")}</td><td>${mud || esc(d.resumo || "equipe/orçamento")}</td></tr>`;
  }).join("")}</tbody></table></div>` : `<p class="vazio">O comitê ainda não mudou o alvo.</p>`;
  return `${cabecalhoProduto(prod, "Fundo", `${esc(P.fundo)} · fechamento de ${dataBR(P.data_referencia)}`)}
  <section class="grade">
    ${kpi("Cota", fmt(r.cota, 6), `<span class="${cls(r.retorno_dia)}">${pct(r.retorno_dia, 2, true)} no último dia</span>`)}
    ${kpi("Patrimônio", mi(r.pl), `fluxo no dia ${mi(r.fluxo_dia, 2)}`)}
    ${kpi("Desde o início", `<span class="${cls(r.retorno_total)}">${pct(r.retorno_total, 2, true)}</span>`, `CDI ${pct(r.cdi_total, 2, true)}`)}
    ${kpi("Valor das decisões", `<span class="${cls(ref.valor_decisoes)}">${pct(ref.valor_decisoes, 2, true)}</span>`, `fundo × carteira de referência (${fmt(ref.cota, 6)})`)}
  </section>
  <section class="cartao"><h2>Cota × CDI × carteira de referência</h2>${grafico([
    { nome: "Fundo", pontos: serieRebase(base, "cota"), cor: "var(--serie-1)" },
    { nome: "Referência (sem o comitê)", pontos: serieRebase(base, "cota_ref"), cor: "var(--serie-3)", tracejado: true },
    { nome: "CDI", pontos: serieRebase(base, "bench"), cor: "var(--serie-2)", tracejado: true },
  ], { formato: (v) => `${fmt(v, 2)}%`, marcas })}<p class="det">Rentabilidade acumulada desde a fundação. Bolinhas roxas: dias em que o comitê mudou o alvo. A referência começa igual ao fundo, fica na alocação neutra e paga a mesma taxa.</p></section>
  <section class="cartao"><h2>Valor das decisões ao longo do tempo</h2>${grafico([{ nome: "Fundo ÷ referência − 1", pontos: h.map((x) => [x.data, x.cota_ref ? (x.cota / x.cota_ref - 1) * 100 : null]), cor: "var(--o-decisao)" }], { formato: (v) => `${fmt(v, 2)}%`, zero: true, marcas })}</section>
  <section class="cartao"><h2>Alocação: peso atual (barra) · alvo (traço) · neutro (tracejado) · limite (faixa)</h2>${aloc}${e.congelados.length ? `<p class="det" style="margin-top:8px">❄ congelado: sem número confiável no painel, o comitê não mexe.</p>` : ""}</section>
  <section class="cartao"><h2>Pesos ao longo do tempo</h2>${grafico(Object.keys(e.alvo).map((a) => ({ nome: P.nomes.ativos[a], pontos: h.map((x) => [x.data, x.pesos[a] * 100]) })), { formato: (v) => `${fmt(v, 0)}%`, marcas })}</section>
  <section class="cartao"><h2>Decisões de alocação</h2>${tabelaDec}</section>`;
}

// ------------------------------------------------------------------ dados (o pipeline)
function telaDados(prod) {
  const P = prod.P;
  if (!P) return semDados(prod);
  const ex = P.extracao, db = P.dashboards;
  const series = P.series || {};
  const fontes = ex.fontes.map((f) => `<div class="no ${f.incidente ? "ruim" : f.real === "erro" ? "ruim" : ""}"><b>${esc(f.nome)}</b><small>${f.incidente ? `incidente ${esc(f.incidente)}` : f.real === "erro" ? "conector falhou" : "no ar"}${f.alternativa_ligada ? " · alternativa ligada" : ""}</small></div>`).join("");
  const ser = ex.fontes.flatMap((f) => f.series.map((s) => `<div class="no ${f.incidente ? "aviso" : ""}"><b>${esc(series[s]?.nome || s)}</b><small>liberada até ${s === "ipca" ? mesAno(f.liberado_ate[s]) : dataBR(f.liberado_ate[s])} · ${esc(series[s]?.publicacao || "")}</small></div>`)).join("");
  const inds = db.indicadores.map((i) => `<div class="no ${i.valor == null ? "ruim" : i.defasagem ? "aviso" : ""}"><b>${esc(i.nome)}</b><small>${i.valor == null ? "não publicado" : esc(fmtIndicador(i))} · confiança ${pct(i.confianca, 0)}</small></div>`).join("");
  const ativos = Object.keys(P.executivos.alvo).map((a) => `<div class="no ${P.executivos.congelados.includes(a) ? "ruim" : ""}"><b>${esc(P.nomes.ativos[a])}</b><small>${P.executivos.congelados.includes(a) ? "congelado" : "o comitê pode mexer"}</small></div>`).join("");
  const disp = ex.disponibilidade || [];
  const matriz = disp.length ? `<div class="rolagem"><div class="matriz" style="grid-template-columns: 120px repeat(${disp.length}, minmax(10px, 1fr)); min-width:${120 + disp.length * 13}px">${ex.fontes.map((f) => `<div class="nome">${esc(f.nome)}</div>${disp.map((d) => `<div class="cel ${d.fontes[f.id]}" title="${dataBR(d.data)}: ${d.fontes[f.id]}"></div>`).join("")}`).join("")}</div></div>
    <div class="legenda"><span><i style="--cor:var(--ok)"></i>ok</span><span><i style="--cor:var(--aviso)"></i>atraso</span><span><i style="--cor:var(--ruim)"></i>fora do ar / falha real</span><span><i style="--cor:var(--o-decisao)"></i>mudou o formato</span></div>` : `<p class="vazio">Sem histórico.</p>`;
  const incs = ex.incidentes.length ? ex.incidentes.map((i) => `<details class="inc" ${i.estado === "aberto" ? "open" : ""}><summary>${selo(i.estado === "aberto" ? "aberto" : "resolvido", i.estado === "aberto" ? "ruim" : "ok")} <b>${esc(i.id)}</b> ${esc(ex.fontes.find((f) => f.id === i.fonte)?.nome || i.fonte)} · ${esc(i.tipo)} ${selo(i.origem === "real" || i.tipo === "falha_real" ? "real" : "simulado", i.origem === "real" || i.tipo === "falha_real" ? "ruim" : "aviso")} <span class="det">${dataBR(i.aberto_em)}${i.resolvido_em ? ` → ${dataBR(i.resolvido_em)}` : ""} · ação <code>${esc(i.acao)}</code>${i.issue ? ` · <a href="${esc(i.issue.url)}">#${i.issue.numero}</a>` : ""}</span></summary><p class="det">${esc(i.detalhe)}</p>${i.historico?.length ? `<ul>${i.historico.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</details>`).join("") : `<p class="vazio">Nenhum incidente nos últimos 30 dias.</p>`;
  const real = prod.produto === "experimento"
    ? `<p>Última extração real: <b>${P.gerado_em ? new Date(P.gerado_em).toLocaleString("pt-BR") : "—"}</b>.</p><ul class="lista">${ex.fontes.map((f) => `<li>${selo(f.real === "ok" ? "ok" : f.real === "erro" ? "falhou" : "?", f.real === "ok" ? "ok" : f.real === "erro" ? "ruim" : "")}<div><b>${esc(f.nome)}</b>${f.erro_real ? `<div class="det neg">${esc(f.erro_real)}</div>` : ""}</div></li>`).join("")}</ul>`
    : `<p>Na simulação, as séries de 2026 foram baixadas das fontes reais pelo workflow (última extração em ${P.gerado_em ? new Date(P.gerado_em).toLocaleString("pt-BR") : "—"}). O motor corta cada série no que estava publicado às 08h do dia simulado.</p>`;
  return `${cabecalhoProduto(prod, "Dados", `o pipeline em ${dataBR(P.data_referencia)}: fontes → séries → indicadores → decisões`)}
  <section class="cartao"><h2>Pipeline</h2><div class="pipeline">
    <div class="col"><h3>Fontes reais</h3>${fontes}</div><div class="col"><h3>Séries (portão)</h3>${ser}</div>
    <div class="col"><h3>Painel das 09h</h3>${inds}</div><div class="col"><h3>Ativos do fundo</h3>${ativos}</div></div>
    <p class="det">Fonte com incidente aberto não passa do portão: a série fica parada na última data liberada, mesmo que o dado real exista. Indicador sem número confiável congela o ativo ligado a ele.</p></section>
  <section class="grade">
    ${kpi("Dívida técnica", `${fmt(ex.divida_tecnica, 1)}/100`, "mais dívida, mais falhas no teste de estresse", ex.divida_tecnica > 50 ? "neg" : "")}
    ${kpi("Equipe de Extração", ex.equipe, `orçamento ${brl(ex.orcamento_dia)}/dia`)}
    ${kpi("Credibilidade dos painéis", pct(db.credibilidade, 1), `confiança média do último painel ${pct(db.confianca_media, 0)}`)}
    ${kpi("Estimativas a conferir", db.estimativas_pendentes.length, "conferidas quando o dado real chega")}
  </section>
  <section class="cartao"><h2>Extração real</h2>${real}</section>
  <section class="cartao"><h2>Disponibilidade por fonte (últimos dias)</h2>${matriz}</section>
  <section class="cartao"><h2>Incidentes</h2>${incs}</section>
  <section class="cartao"><h2>Painel do último dia</h2><div class="rolagem"><table><thead><tr><th>Indicador</th><th class="n">Valor</th><th>Referência</th><th>Situação</th><th>De onde vem</th><th class="n">Confiança</th></tr></thead><tbody>${db.indicadores.map((i) => `<tr><td><b>${esc(i.nome)}</b></td><td class="n">${i.valor == null ? "—" : esc(fmtIndicador(i))}</td><td>${dataBR(i.data_ref)}</td><td>${i.defasagem ? selo(`${i.defasagem}d · ${i.estrategia}`, i.estrategia === "suspender" ? "ruim" : "aviso") : selo(i.via === "alternativa" ? "via alternativa" : "em dia", "ok")}</td><td class="det">${fmtTexto(i.conta || "")}</td><td class="n">${pct(i.confianca, 0)}</td></tr>`).join("")}</tbody></table></div></section>`;
}
function fmtIndicador(i) {
  const v = i.valor;
  if (i.id === "dolar") return `R$ ${fmt(v, 4)}`;
  if (i.id === "bova11") return `R$ ${fmt(v, 2)}`;
  if (i.id === "ibov") return `${fmt(v, 0)} pts`;
  return `${fmt(v, 2)}%`;
}

// ------------------------------------------------------------------ empresa
function telaEmpresa(prod) {
  const P = prod.P;
  if (!P) return semDados(prod);
  const g = P.executivos.gestora, h = P.historico || [], ex = P.extracao;
  const folego = g.custo_dia ? g.caixa / g.custo_dia : null;
  return `${cabecalhoProduto(prod, "Empresa", "a gestora: receita de taxa, custos, equipe e a saúde da operação")}
  <section class="grade">
    ${kpi("Caixa da gestora", brl(g.caixa), folego ? `${fmt(folego, 0)} dias de custo` : "", cls(g.caixa))}
    ${kpi("Receita do último dia", brl(g.receita_dia), "taxa de administração (1% a.a.)")}
    ${kpi("Custo do último dia", brl(g.custo_dia), `casa + ${ex.equipe} pessoa(s) + orçamento`)}
    ${kpi("Resultado do dia", brl(g.receita_dia - g.custo_dia), g.receita_dia >= g.custo_dia ? "a casa se pagou" : "a casa não se pagou", cls(g.receita_dia - g.custo_dia))}
  </section>
  <section class="cartao"><h2>Caixa da gestora</h2>${grafico([{ nome: "Caixa", pontos: h.map((x) => [x.data, x.caixa_gestora / 1e6]) }], { formato: (v) => `R$ ${fmt(v, 2)} mi` })}</section>
  <div class="grade-2">
    <section class="cartao"><h2>Dívida técnica</h2>${grafico([{ nome: "Dívida", pontos: h.map((x) => [x.data, x.divida_tecnica]) }], { formato: (v) => fmt(v, 0), altura: 160 })}</section>
    <section class="cartao"><h2>Credibilidade e confiança</h2>${grafico([
      { nome: "Credibilidade", pontos: h.map((x) => [x.data, x.credibilidade * 100]) },
      { nome: "Confiança do painel", pontos: h.map((x) => [x.data, x.confianca_media * 100]), tracejado: true },
    ], { formato: (v) => `${fmt(v, 0)}%`, altura: 160 })}</section>
  </div>
  <section class="cartao"><h2>Equipe e orçamento da Extração</h2>${grafico([
    { nome: "Equipe (pessoas)", pontos: h.map((x) => [x.data, x.equipe]) },
    { nome: "Orçamento (R$ mil/dia)", pontos: h.map((x) => [x.data, x.orcamento_dia != null ? x.orcamento_dia / 1000 : null]), tracejado: true },
  ], { formato: (v) => fmt(v, 1), altura: 160 })}</section>
  <section class="cartao"><h2>Alertas ativos</h2>${P.alertas.length ? `<ul class="lista">${P.alertas.map((a) => `<li>${selo(a.sev, a.sev === "alta" ? "ruim" : a.sev === "media" ? "aviso" : "info")}<div><b>${esc(a.titulo)}</b>${a.issue ? ` <a href="${esc(a.issue.url)}">#${a.issue.numero}</a>` : ""}<div class="det">desde ${dataBR(a.aberto_em)}${a.detalhe ? ` · ${fmtTexto(a.detalhe)}` : ""}</div></div></li>`).join("")}</ul>` : `<p class="vazio">Nenhum alerta ativo.</p>`}
  ${prod.produto === "experimento" ? `<p class="det" style="margin-top:8px">No experimento, cada alerta vira uma <a href="${GH}/issues?q=label%3Asimulacao">issue</a> que abre e fecha sozinha.</p>` : ""}</section>`;
}

// ------------------------------------------------------------------ validação
function telaValidacao(prod) {
  const P = prod.P;
  if (!P) return semDados(prod);
  const m = P.metricas || {}, r = P.resumo, ref = P.referencia || {};
  const total = (m.verificacoes_ok || 0) + (m.verificacoes_falha || 0);
  const nivel = m.verificacoes_falha ? "ruim" : (ref.valor_decisoes ?? 0) < 0 ? "aviso" : "ok";
  const h = P.historico || [];
  const base = [{ data: P.fundacao?.data || P.cenario?.inicio, cota: 1, bench: 1, cota_ref: 1 }, ...h];
  const media = m.resolvidos ? m.dias_resolucao / m.resolvidos : null;
  const est = (m.estimativas_ok || 0) + (m.estimativas_erro || 0);
  const linhas = [
    ["Dias úteis processados", m.dias, ""],
    ["Dias com o painel completo e em dia", `${m.dias_em_dia} (${pct(m.dias ? m.dias_em_dia / m.dias : null, 0)})`, "os outros tiveram número atrasado, estimado ou suspenso"],
    ["Incidentes simulados (teste de estresse)", m.incidentes_simulados, "sorteados pela dívida técnica"],
    ["Incidentes reais", m.incidentes_reais, "fonte real não entregou o esperado ou conector falhou"],
    ["Tempo médio até resolver", media == null ? "—" : `${fmt(media, 1)} dia(s)`, `${m.resolvidos} resolvido(s)`],
    ["Estimativas conferidas", est ? `${m.estimativas_ok} acertos, ${m.estimativas_erro} erros` : "nenhuma", "erro além da tolerância derruba a credibilidade"],
    ["Reuniões de investimentos", m.reunioes, `${m.mudancas_alvo} mudaram o alvo`],
    ["Giro e custo de transação", `${mi(m.giro)} · ${brl(m.custo_giro)}`, "custo das decisões de girar a carteira"],
    ["Taxa de administração paga", brl(m.taxa), "receita da gestora"],
    ["Aplicações − resgates", mi(m.fluxo, 2), "modelo de cotistas, sem sorteio"],
  ];
  return `${cabecalhoProduto(prod, "Validação", prod.produto === "simulacao" ? "a simulação existe para responder: o experimento funciona?" : "o experimento confere o próprio trabalho todo dia")}
  <section class="cartao veredito ${nivel}">
    <div class="grande">${m.verificacoes_falha ? `${m.verificacoes_falha} verificação(ões) falharam em ${m.dias} dias` : `${m.dias} dias úteis, ${total} verificações, nenhuma falha`}</div>
    <p>O motor ${m.verificacoes_falha ? "errou alguma conta (veja abaixo)" : "fechou todas as contas, não usou dado do futuro e respeitou a política em todos os dias"}. As decisões do comitê somam <b class="${cls(ref.valor_decisoes)}">${pct(ref.valor_decisoes, 2, true)}</b> contra a carteira que nunca muda de ideia; o fundo rendeu <b class="${cls(r.retorno_total - r.cdi_total)}">${pct(r.retorno_total, 2, true)}</b> contra ${pct(r.cdi_total, 2, true)} do CDI.</p>
  </section>
  <section class="cartao"><h2>Verificações (todos os dias)</h2><ul class="checks">${(P.verificacoes || []).map((c) => `<li class="${c.falhas ? "falhou" : "ok"}"><span class="i">${c.falhas ? "✗" : "✓"}</span><div>${esc(c.nome)}${c.ultima_falha ? `<div class="det neg">última falha em <a href="#/${prod.produto}/dia/${c.ultima_falha.data}">${dataBR(c.ultima_falha.data)}</a>: ${esc(c.ultima_falha.detalhe)}</div>` : ""}</div><span class="det">${c.ok}/${c.ok + c.falhas}</span></li>`).join("")}</ul></section>
  <section class="cartao"><h2>Contrafactual: o fundo com e sem o comitê</h2>${grafico([
    { nome: "Fundo", pontos: serieRebase(base, "cota"), cor: "var(--serie-1)" },
    { nome: "Referência (sem o comitê)", pontos: serieRebase(base, "cota_ref"), cor: "var(--serie-3)", tracejado: true },
    { nome: "CDI", pontos: serieRebase(base, "bench"), cor: "var(--serie-2)", tracejado: true },
  ], { formato: (v) => `${fmt(v, 2)}%`, marcas: (P.calendario || []).filter((c) => c.alocacao).map((c) => c.data) })}</section>
  <section class="cartao"><h2>Saúde do processo</h2><div class="rolagem"><table><tbody>${linhas.map(([a, b, c]) => `<tr><td><b>${esc(a)}</b></td><td class="n">${esc(b)}</td><td class="det">${esc(c)}</td></tr>`).join("")}</tbody></table></div></section>
  ${prod.produto === "simulacao" ? `<section class="cartao"><h2>Testar outra regra</h2><p class="det">Mude <code>politicas.json</code> da simulação (ou uma regra em <code>gestora/</code>), recomece a simulação e compare: as verificações e o contrafactual dizem se a mudança melhorou o experimento.</p><div class="acoes">${externo(`${GH}/edit/main/cenarios/2026/empresa/politicas.json`, "Editar a política da simulação ↗", "botao leve")}<button class="botao leve" type="button" data-recomecar>Recomeçar do zero…</button></div></section>` : ""}`;
}

// ------------------------------------------------------------------ regras
function telaRegras(prod) {
  const P = prod.P;
  if (!P?.regras) return semDados(prod);
  const cor = { geral: "heranca" };
  return `${cabecalhoProduto(prod, "Regras", "o motor por dentro, com os parâmetros vigentes desta empresa (politicas.json)")}
  ${P.regras.map((s) => `<section class="cartao etapa" data-e="${cor[s.etapa] || s.etapa}"><header><div><div class="h">${esc(NOME_ETAPA[s.etapa] || "Geral")}</div><h2>${esc(s.titulo)}</h2></div></header>
    ${s.itens ? `<ul class="regras">${s.itens.map((i) => `<li>${fmtTexto(i)}</li>`).join("")}</ul>` : ""}
    ${s.tabela ? `<div class="rolagem" style="margin-top:10px"><table><thead><tr>${s.tabela.colunas.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${s.tabela.linhas.map((l) => `<tr>${l.map((c) => `<td>${fmtTexto(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : ""}
  </section>`).join("")}
  <section class="cartao"><p class="det">Código: ${externo(`${GH}/blob/main/gestora/simulacao.py`, "simulacao.py", "")} (etapas), ${externo(`${GH}/blob/main/gestora/times.py`, "times.py", "")} (decisões), ${externo(`${GH}/blob/main/gestora/verificacoes.py`, "verificacoes.py", "")} e ${externo(`${GH}/blob/main/${prod.produto === "simulacao" ? "cenarios/2026/empresa" : "empresa"}/politicas.json`, "politicas.json", "")}.</p></section>`;
}

// ------------------------------------------------------------------ simular pelo site (dispara o workflow e acompanha)
const CHAVE_TOKEN = "capivara-token";
const token = () => ler(CHAVE_TOKEN, "");
let SIM = lerSessao("capivara-sim2");
if (SIM && Date.now() - SIM.desde > 25 * 60000) SIM = null;
const guardarSim = () => gravarSessao("capivara-sim2", SIM);

function botaoSimular() {
  const P = PRODUTOS.simulacao?.P;
  if (SIM) return `<button class="botao" type="button" disabled><span class="pulso" aria-hidden="true"></span> ${SIM.recomecar ? "Recomeçando…" : "Simulando…"}</button>`;
  if (P && progressoSimulacao(P).fim) return `<span class="det">A simulação alcançou o presente.</span>`;
  return `<button class="botao prim" style="--acento:var(--sim)" type="button" data-simular>⏭ ${P ? "Simular próximo dia" : "Começar a simulação"}</button>`;
}
function textoProximo(P) {
  const prog = progressoSimulacao(P);
  return prog.fim ? "Não há mais dias úteis até ontem." : `O clique dispara o GitHub Actions: testes do motor, validação, simulação do próximo dia útil, gravação e publicação. Leva cerca de 2 minutos e você acompanha cada passo aqui. Faltam ${prog.total - prog.feitos} dias úteis até ontem.`;
}

function pedirToken(erro = "") {
  let d = $("#dlg-token");
  if (!d) { d = document.createElement("dialog"); d.id = "dlg-token"; d.className = "dialogo"; document.body.append(d); }
  const novo = `https://github.com/settings/personal-access-tokens/new?name=${encodeURIComponent("Capivara Asset · simular")}&description=${encodeURIComponent("Site da Capivara Asset dispara a simulação")}&target_name=GloedenJoao&expires_in=365&actions=write`;
  d.innerHTML = `<form method="dialog" class="dlg-corpo">
    <h2>Simular pelo site</h2>
    <p>O site é uma página estática: para mandar a simulação andar ele dispara o workflow pelo GitHub com um token seu, que fica <strong>só neste navegador</strong>. É uma vez só.</p>
    <ol><li>${externo(novo, "Criar o token no GitHub ↗", "")} (já abre preenchido).</li><li>Em <em>Repository access</em>: <strong>Only select repositories → profissional</strong>.</li><li>Em <em>Permissions → Repository</em>: só <strong>Actions: Read and write</strong>. Gere e copie.</li></ol>
    ${erro ? `<p class="neg">${esc(erro)}</p>` : ""}
    <label class="campo">Token <input id="dlg-token-valor" type="password" autocomplete="off" placeholder="github_pat_…" required></label>
    <div class="acoes"><button class="botao prim" value="ok" type="submit">Salvar e continuar</button><button class="botao leve" value="cancelar" type="button" data-fechar>Cancelar</button>${token() ? `<button class="botao leve" type="button" data-esquecer>Esquecer o token salvo</button>` : ""}</div>
  </form>`;
  d.showModal();
  return new Promise((ok) => { d.onclose = () => ok(d.returnValue === "ok" ? $("#dlg-token-valor").value.trim() : ""); });
}
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-fechar]")) $("#dlg-token")?.close("cancelar");
  if (e.target.closest("[data-esquecer]")) { try { localStorage.removeItem(CHAVE_TOKEN); } catch (_) { /* tudo bem */ } $("#dlg-token")?.close("cancelar"); avisar("Token esquecido."); }
  const b = e.target.closest("[data-simular]");
  if (b) { b.disabled = true; disparar({}).finally(() => { b.disabled = false; }); }
  if (e.target.closest("[data-recomecar]")) {
    if (confirm("Recomeçar a simulação do zero? O histórico atual da simulação sai do site (continua no histórico do git) e a empresa é fundada de novo em 1º de janeiro, com as regras de agora.")) disparar({ recomecar: "true" });
  }
});

async function api(caminho, opcoes = {}) {
  const t = token();
  return fetch(`${API}${caminho}`, { cache: "no-store", ...opcoes, headers: { Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", ...(t ? { Authorization: `Bearer ${t}` } : {}), ...(opcoes.headers || {}) } });
}

async function disparar(extra) {
  let t = token();
  if (!t) { t = await pedirToken(); if (!t) return; gravar(CHAVE_TOKEN, t); }
  const prod = PRODUTOS.simulacao;
  const r = await api("/actions/workflows/simulacao.yml/dispatches", { method: "POST", body: JSON.stringify({ ref: "main", inputs: { cenario: prod?.id || "2026", dias: "1", ...extra } }) }).catch((e) => ({ ok: false, status: 0, erro: e.message }));
  if (!r.ok) {
    const msg = r.status === 401 ? "O GitHub não aceitou o token (vencido ou digitado errado)." : r.status === 403 || r.status === 404 ? "O token não tem permissão de Actions (Read and write) no repositório profissional." : `O GitHub respondeu ${r.status || r.erro}.`;
    if ([401, 403, 404].includes(r.status)) { const novo = await pedirToken(msg); if (novo) { gravar(CHAVE_TOKEN, novo); return disparar(extra); } return; }
    avisar(msg); return;
  }
  SIM = { desde: Date.now(), base: prod?.P?.data_referencia || null, run: null, passos: [], recomecar: !!extra.recomecar };
  guardarSim();
  avisar(extra.recomecar ? "Recomeçando a simulação: acompanhe a execução aqui." : "Pedido enviado: acompanhe a execução aqui.");
  atualizarSimUI();
  acompanhar();
}

const ICONE_PASSO = { ok: "✓", falhou: "✗", rodando: "●", fila: "○", pulado: "–" };
function painelExecucao(ex, texto) {
  const passos = ex.passos?.length ? ex.passos : [{ nome: "Esperando o GitHub começar a execução…", st: "rodando" }];
  return `<section class="cartao execucao" style="margin-top:12px"><h2>Execução no GitHub Actions</h2>${ex.run ? `<p>${externo(ex.run.url, "Abrir a execução no GitHub ↗", "")}</p>` : ""}
    <p class="det">${texto} Começou há ${Math.max(0, Math.round((Date.now() - ex.desde) / 1000))} s.</p>
    <ol class="passos">${passos.map((p) => `<li class="${p.st}"><span class="i">${ICONE_PASSO[p.st] || "○"}</span><span>${esc(p.nome)}</span><span class="t">${p.seg != null ? `${p.seg} s` : ""}</span></li>`).join("")}</ol></section>`;
}
function execucaoHTML(soSim = false) {
  if (!SIM) return soSim ? `<div data-exec></div>` : "";
  const texto = SIM.fase === "publicando" ? "Simulado e gravado. Esperando o site publicar o dia novo…"
    : SIM.recomecar ? "Recomeçando a simulação do zero." : `Simulando o dia útil depois de ${dataBR(SIM.base)}.`;
  return `<div data-exec>${painelExecucao(SIM, texto)}</div>`;
}
function passosDe(jobs) {
  return jobs.flatMap((j) => (j.steps || []).filter((p) => !/^(Set up job|Complete job|Post |Run actions\/)/.test(p.name)).map((p) => ({
    nome: j.name === "site" ? `Publicar: ${p.name}` : p.name,
    st: p.status !== "completed" ? (p.status === "in_progress" ? "rodando" : "fila") : p.conclusion === "success" ? "ok" : p.conclusion === "skipped" ? "pulado" : "falhou",
    seg: p.started_at && p.completed_at ? Math.round((new Date(p.completed_at) - new Date(p.started_at)) / 1000) : null,
  })));
}

// o fechamento diário do experimento também aparece ao vivo, quando está rodando
let FECH = null;
async function conferirFechamento(forcar = false) {
  clearTimeout(conferirFechamento.t);
  if (ROTA.produto !== "experimento" && ROTA.produto !== "inicio") return;
  const agora = Date.now();
  if (!forcar && conferirFechamento.ultimo && agora - conferirFechamento.ultimo < 240000) return;
  conferirFechamento.ultimo = agora;
  try {
    const r = await api("/actions/workflows/fechamento.yml/runs?per_page=1");
    if (!r.ok) return;
    const run = (await r.json()).workflow_runs?.[0];
    if (!run || run.status === "completed") {
      if (FECH) { FECH = null; atualizarFechUI(); conferirVersao(); }
      return;
    }
    const rj = await api(`/actions/runs/${run.id}/jobs`);
    FECH = { run: { id: run.id, url: run.html_url }, passos: passosDe(rj.ok ? (await rj.json()).jobs : []), desde: new Date(run.run_started_at || run.created_at).getTime() };
    atualizarFechUI();
    conferirFechamento.t = setTimeout(() => conferirFechamento(true), 10000);
  } catch (_) { /* sem API: tudo bem, o versao.json traz o dia novo */ }
}
function atualizarFechUI() {
  $$("[data-fech]").forEach((el) => { el.innerHTML = FECH ? painelExecucao(FECH, "O fechamento do experimento está rodando agora: extração real, etapas do dia, verificações e publicação.") : ""; });
}

function atualizarSimUI() {
  $$("[data-sim-slot]").forEach((el) => { el.innerHTML = botaoSimular(); });
  $$("[data-exec]").forEach((el) => { el.outerHTML = execucaoHTML(true); });
}

async function acompanhar() {
  clearTimeout(acompanhar.t);
  if (!SIM) return;
  try {
    if (!SIM.run) {
      const r = await api("/actions/workflows/simulacao.yml/runs?event=workflow_dispatch&per_page=5");
      const run = r.ok ? (await r.json()).workflow_runs.find((x) => new Date(x.created_at).getTime() >= SIM.desde - 90000) : null;
      if (run) SIM.run = { id: run.id, url: run.html_url };
    }
    if (SIM.run) {
      const [rr, rj] = await Promise.all([api(`/actions/runs/${SIM.run.id}`), api(`/actions/runs/${SIM.run.id}/jobs`)]);
      const run = rr.ok ? await rr.json() : null;
      const jobs = rj.ok ? (await rj.json()).jobs : [];
      SIM.passos = passosDe(jobs);
      if (run?.status === "completed" && run.conclusion !== "success") {
        avisar("A execução falhou no GitHub: abra a execução para ver o erro.");
        SIM.falhou = true; SIM = null; guardarSim(); atualizarSimUI(); return;
      }
      if (run?.status === "completed") SIM.fase = "publicando";
    }
  } catch (_) { /* sem API agora: segue esperando pelo versao.json */ }
  const novo = await conferirVersao(true);
  const atual = PRODUTOS.simulacao?.P?.data_referencia || null;
  if ((novo || SIM.fase === "publicando") && atual && (atual !== SIM.base || SIM.recomecar && novo)) {
    const recomecou = SIM.recomecar;
    SIM = null; guardarSim();
    avisar(recomecou ? "A simulação recomeçou." : `Chegou: ${dataBR(atual)}. Tocando o dia.`);
    gravarSessao("capivara-autoplay", `simulacao:${atual}`);
    navegar(`#/simulacao/dia/${atual}`);
    return;
  }
  if (Date.now() - SIM.desde > 20 * 60000) { avisar("A execução demorou demais: veja no GitHub."); SIM = null; guardarSim(); atualizarSimUI(); return; }
  guardarSim();
  atualizarSimUI();
  acompanhar.t = setTimeout(acompanhar, 5000);
}

// ------------------------------------------------------------------ atualização sozinha (versao.json)
let VERSAO_ATUAL = null;
let ULTIMA_CONFERENCIA = null;
async function conferirVersao(silencioso = false) {
  let v;
  try { v = await json("versao.json"); } catch (_) { return false; }
  ULTIMA_CONFERENCIA = Date.now();
  mostrarFrescor();
  if (window.CODIGO && !window.CODIGO.startsWith("__") && v.codigo && v.codigo !== window.CODIGO) { location.reload(); return true; }
  if (!VERSAO_ATUAL) { VERSAO_ATUAL = v; return false; }
  const mudou = JSON.stringify(v.paineis) !== JSON.stringify(VERSAO_ATUAL.paineis) || v.versao !== VERSAO_ATUAL.versao;
  VERSAO_ATUAL = v;
  if (!mudou) return false;
  window.VERSAO = v.versao;
  DIAS.clear();
  PRODUTOS = await carregarProdutos();
  if (!silencioso && !PLAY) { avisar("Dados novos chegaram."); render(); }
  return true;
}
function mostrarFrescor() {
  const el = $("#frescor");
  if (!el || !ULTIMA_CONFERENCIA) return;
  const s = Math.round((Date.now() - ULTIMA_CONFERENCIA) / 1000);
  el.textContent = s < 60 ? "conferido agora" : `conferido há ${Math.round(s / 60)} min`;
}
setInterval(() => { if (!SIM) conferirVersao(); }, 60000);
setInterval(mostrarFrescor, 20000);

// ------------------------------------------------------------------ render
async function render() {
  ROTA = lerRota();
  marcarNavegacao();
  if (PLAY) { clearTimeout(PLAY.t); PLAY = null; }
  GRAFICOS = [];
  const main = $("#conteudo");
  const prod = PRODUTOS[ROTA.produto];
  let html;
  if (ROTA.produto === "inicio") html = telaInicio();
  else if (!prod) html = `<div class="cartao"><p class="vazio">Esse produto ainda não existe neste site.</p></div>`;
  else {
    const tela = { dia: telaDia, fundo: telaFundo, dados: telaDados, empresa: telaEmpresa, validacao: telaValidacao, regras: telaRegras }[ROTA.secao];
    html = await tela(prod);
  }
  main.innerHTML = html;
  document.title = ROTA.produto === "inicio" ? "Capivara Asset" : `${PRODUTOS_INFO[ROTA.produto].nome} · ${SECOES.find((s) => s[0] === ROTA.secao)[1]} · Capivara Asset`;
  prepararPlayer();
  if (SIM) atualizarSimUI();
  atualizarFechUI();
  conferirFechamento();
}

window.addEventListener("hashchange", () => { if (!location.hash.startsWith("#etapa-")) { render(); window.scrollTo(0, 0); } });
let redim;
let largura = window.innerWidth;
window.addEventListener("resize", () => { if (Math.abs(window.innerWidth - largura) < 40) return; largura = window.innerWidth; clearTimeout(redim); redim = setTimeout(() => { if (!PLAY) render(); }, 200); });

(async function iniciar() {
  $("#conteudo").innerHTML = `<p class="carregando">Carregando…</p>`;
  try {
    PRODUTOS = await carregarProdutos();
  } catch (e) {
    $("#conteudo").innerHTML = `<div class="cartao"><p class="vazio">Não foi possível carregar os painéis: ${esc(e.message)}</p></div>`;
    return;
  }
  await render();
  conferirVersao(true);
  if (SIM) acompanhar();
})();
