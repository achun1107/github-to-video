/* 批量模板：一条仓库数据 → 一支 34.8s 竖屏短片（参考片版式，内容由数据驱动）
 *
 * 版式常量来自 recipe.js（cangjie 蒸馏：卡 943×1075@(68,515)、标题 y296、说明条 y1520）
 * 卡片顺序：证据卡 → 数字卡 → 标签卡 → 结论卡；每张卡的内容都来自 CONTENT。
 */
(function () {
'use strict';
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const R = window.RECIPE || {};
const RHOOK = R.hook || {}, RCARD = R.card || {}, RCHIP = R.chip || {}, RBG = R.bg || {}, RC = R.colors || {};
const SHIFT = R.contentShiftY == null ? 0 : R.contentShiftY;

const HOOK = '__HOOK__';
const SUB = '__SUB__';
const DAYS = __DAYS__;
const STARS = '__STAR__';
const FORKS = '__FORKS__';
const REPO_NAME = '__NAME__';
const OWNER = '__OWNER__';
const LANG = '__LANG__';
const CREATED = '__CREATED__';
const TAGLINE = '__DESC__';

const C = {
  bg: RBG.color || '#0D0D0D',
  card: RC.card || '#F4EEE0',
  card2: RC.card2 || '#FBF6EC',
  ink: RC.ink || '#26262B',
  ink2: RC.ink2 || '#4A4A52',
  mute: RC.mute || '#8A8A93',
  line: RC.line || '#D9D0C2',
  stroke: RC.stroke || '#E8613C',
  green: RC.green || '#5BE06A',
  gold: RC.gold || '#D9A24B',
  blue: '#6E8BD8',
  white: RC.white || '#FFFFFF',
};

const DUR = 18.0;
const T = { head: 0.15, c1: 1.15, c2: 4.05, c3: 8.30, c4: 12.60, c5: 16.6, outro: 16.8 };

const SUBS = [
  { a: 0.70,  b: 2.13,  zh: HOOK },
  { a: 2.08,  b: 4.05,  zh: 'GitHub 上 ' + STARS + ' 个 Star' },
  { a: 4.00,  b: 8.28,  zh: CREATED.slice(5) + ' 才上线 · ' + LANG },
  { a: 8.22,  b: 12.58, zh: '拿走就能用' },
  { a: 12.52, b: 16.55, zh: REPO_NAME + ' GitHub 搜得到' },
  
];

const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60), ms = Math.floor((s % 1) * 1000);
  return pad2(m) + ':' + pad2(s2) + '.' + String(ms).padStart(3, '0');
}

function cardBox(fr, k, o) {
  o = o || {};
  const a = o.a == null ? 1 : o.a;
  if (a <= 0.002) return;
  const x = o.x == null ? (RCARD.x || 68) : o.x;
  const w = o.w == null ? (RCARD.w || 943) : o.w;
  const y = o.y == null ? ((RCARD.y || 515) - SHIFT) : o.y;
  const h = o.h == null ? (RCARD.h || 1075) : o.h;
  const r = o.r == null ? (RCARD.r || 44) : o.r;
  const bw = o.bw == null ? (RCARD.border || 5) : o.bw;
  fr.g({ a }, () => {
    fr.rect(x + 8, y + 26, w, h, { r, fill: '#000000', a: 0.5 });
    fr.rect(x, y, w, h, { r, fill: C.card });
    fr.rect(x, y, w, h, { r, color: RCARD.borderColor || '#F79450', w: bw, a: 0.98 });
    fr.rect(x + 2, y + 2, w - 4, 120, { r: r - 2, fill: C.card2, a: 0.5 });
  });
}

function vw(str, size) {
  return Array.from(str).reduce((n, ch) => n + (/[\u4e00-\u9fff]/.test(ch) ? 1 : (ch === ' ' ? 0.3 : 0.56)), 0) * size;
}
function header(fr, t, main, sub) {
  const ka = ss(t, T.head, T.head + 0.18);
  if (ka <= 0) return;
  const maxW = RHOOK.maxWidth || 940;
  const size = Math.min(RHOOK.size1 || 84, Math.floor(maxW / (vw(main, 1) || 1)));
  fr.text(main, W / 2, (RHOOK.y1 || 296) + (1 - ka) * 16, {
    font: 'sans', size, color: C.white, a: ka,
    glow: 26, glowColor: '#FFFFFF', glowA: 0.22, shadow: 0.45, shadowBlur: 14,
  });
  const ks = ss(t, T.head + 0.1, T.head + 0.3);
  fr.text(sub, W / 2, (RHOOK.y2 || 423) + (1 - ks) * 12, {
    font: 'sans', size: RHOOK.size2 || 56, color: C.green, a: ks,
    glow: 24, glowColor: C.green, glowA: 0.48,
  });
}

function seriesBadge(fr, t) {
  const a = ss(t, 0.9, 1.5) * (1 - ss(t, DUR - 0.6, DUR));
  if (a <= 0.004) return;
  const txt = STARS + ' ★';
  const size = 28;
  const tw = fr.measure(txt, { font: 'mono', size });
  const w = tw + 56, h = 52, x = W - 64 - w, y = 64;
  fr.rect(x, y, w, h, { r: 26, fill: C.stroke, a: a * 0.18 });
  fr.rect(x, y, w, h, { r: 26, stroke: C.stroke, strokeW: 2, a: a * 0.9 });
  fr.text(txt, x + w / 2, y + h / 2, { font: 'mono', size, color: C.stroke, a });
}

const FLASH = [[0.15, 0.44, STARS, C.stroke], [0.44, 0.72, '★', C.green], [0.72, 1.12, 'FORK ' + FORKS, C.gold]];
function flashNum(fr, t) {
  for (let i = 0; i < FLASH.length; i++) {
    const a = FLASH[i][0], b = FLASH[i][1], txt = FLASH[i][2], col = FLASH[i][3];
    if (t < a - 0.02 || t > b + 0.02) continue;
    const k = ss(t, a, a + 0.05) * (1 - ss(t, b - 0.05, b));
    if (k <= 0.004) return;
    const size = Math.min(380, Math.floor(900 / (vw(txt, 1) || 1)));
    fr.text(txt, W / 2, 820, { font: 'sans', size, color: col, a: k, glow: 60, glowColor: col, glowA: 0.45 * k });
    return;
  }
}

function ringMark(fr, cx, cy, rx, ry, k, color, lw) {
  if (k <= 0.004) return;
  const ctx = fr.x;
  const start = -Math.PI * 0.62;
  const sweep = Math.PI * 2.12 * k;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = lw || 5;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, start, start + sweep);
  ctx.stroke();
  ctx.restore();
}

/* 仓库页截图（batch-shot 拍的），缺图时用占位 */
const REPO_IMG = new Image();
REPO_IMG.src = 'assets/repo.png';
window.__IMAGES = [REPO_IMG];

function shot(fr, img, x, y, w, o) {
  o = o || {};
  if (!img || !img.complete || !img.naturalWidth) {
    fr.rect(x, y, w, w * 0.56, { r: 14, fill: '#E7E0D2', a: 0.85 });
    return w * 0.56;
  }
  const h = w * img.naturalHeight / img.naturalWidth;
  const ctx = fr.x;
  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, o.r || 14); else ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.drawImage(img, x, y, w, h);
  ctx.restore();
  if (o.ring) fr.rect(x, y, w, h, { r: o.r || 14, stroke: o.ring, strokeW: 2, a: o.ringA || 0.6 });
  return h;
}

const KEYWORDS = (R.keywords && R.keywords.length) ? R.keywords : [STARS, FORKS, 'Star', 'Fork'];
const KEY_RE = new RegExp('(' + KEYWORDS.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')', 'g');

function captionChip(fr, str, a) {
  const size = RCHIP.size || 56;
  const padX = RCHIP.padX || 32;
  const parts = [];
  let last = 0, m;
  KEY_RE.lastIndex = 0;
  while ((m = KEY_RE.exec(str))) {
    if (m.index > last) parts.push([str.slice(last, m.index), false]);
    parts.push([m[0], true]);
    last = m.index + m[0].length;
  }
  if (last < str.length) parts.push([str.slice(last), false]);
  if (!parts.length) parts.push([str, false]);
  let s2 = size;
  const width = sz => parts.reduce((n, p) => n + fr.measure(p[0], { font: 'sans', size: sz }), 0);
  let total = width(s2);
  while (total > (RCHIP.maxWidth || 880) && s2 > 34) { s2 -= 2; total = width(s2); }
  const w = total + padX * 2, h = RCHIP.h || 100;
  const y = RCHIP.y || 1520;
  fr.rect(W / 2 - w / 2, y - h / 2, w, h, { r: RCHIP.radius || 14, fill: RCHIP.bg || 'rgba(18,18,22,0.80)', a: 0.92 * a });
  let cx = W / 2 - total / 2;
  parts.forEach(p => {
    const sw = fr.measure(p[0], { font: 'sans', size: s2 });
    fr.text(p[0], cx + sw / 2, y, {
      font: 'sans', size: s2, a,
      color: p[1] ? (RCHIP.keyColor || C.stroke) : (RCHIP.text || C.white),
      shadow: 0.35, shadowBlur: 8, shadowY: 2,
    });
    cx += sw;
  });
}

function subtitles(fr, t) {
  const cand = SUBS.filter(x => t >= x.a - 0.05 && t <= x.b + 0.25);
  const s = cand.length ? cand[cand.length - 1] : null;
  if (!s) return;
  const a = ss(t, s.a, s.a + 0.18) * (1 - ss(t, s.b, s.b + 0.1));
  if (a <= 0.003) return;
  captionChip(fr, s.zh, a);
}

/* ================= 卡片 ================= */

function card1(fr, lt) {
  cardBox(fr, 1);
  const bx = RCARD.x || 68, by = (RCARD.y || 515) - SHIFT;
  const bw = RCARD.w || 943, bh = RCARD.h || 1075;
  const ratio = REPO_IMG.naturalWidth ? REPO_IMG.naturalHeight / REPO_IMG.naturalWidth : 0.78;
  /* 截图占卡片上部 70%，剩下 30% 留给仓库名和说明条 */
  const maxH = bh * 0.70;
  const drawW = Math.min(bw, maxH / ratio);
  const ih = drawW * ratio;
  const ix = bx + (bw - drawW) / 2;
  const ctx = fr.x;
  const a0 = ss(lt, -0.12, 0.30);
  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(bx, by, bw, bh, (RCARD.r || 44) - 2); else ctx.rect(bx, by, bw, bh);
  ctx.clip();
  ctx.globalAlpha *= a0;
  if (REPO_IMG.complete && REPO_IMG.naturalWidth) {
    ctx.drawImage(REPO_IMG, ix, by, drawW, ih);
  } else {
    ctx.fillStyle = '#EDE6D6'; ctx.fillRect(bx, by, bw, bh);
  }
  const g = ctx.createLinearGradient(0, by + ih - 160, 0, by + ih);
  g.addColorStop(0, 'rgba(244,238,224,0)');
  g.addColorStop(1, 'rgba(244,238,224,0.98)');
  ctx.fillStyle = g; ctx.fillRect(bx, by + ih - 160, bw, 160);
  ctx.restore();

  const pa = ss(lt, 0.10, 0.34);
  if (pa > 0.004) {
    const pw = 640, ph = 140, px = W / 2 - pw / 2, py = 930;
    const sc = 0.90 + 0.10 * E.out3(pa);
    const cx = px + pw / 2, cy = py + ph / 2;
    fr.g({ a: pa }, () => {
      const c2 = fr.x;
      c2.save();
      c2.translate(cx, cy); c2.scale(sc, sc); c2.translate(-cx, -cy);
      fr.rect(px + 4, py + 12, pw, ph, { r: 44, fill: '#000000', a: 0.42 });
      fr.rect(px, py, pw, ph, { r: 44, fill: '#F8F7F5' });
      fr.rect(px, py, pw, ph, { r: 44, color: '#D8D4CE', w: 2, a: 0.95 });
      fr.text('★', px + 78, cy - 2, { font: 'sans', size: 64, color: '#8A8A93' });
      fr.text('Star', px + 132, cy, { font: 'sans', size: 56, color: '#2B2B30', align: 'l' });
      fr.text(STARS, px + pw - 48, cy, { font: 'sans', size: 72, color: C.stroke, align: 'r' });
      c2.restore();
    });
  }
  const a6 = ss(lt, 0.18, 0.40);
  if (a6 > 0.004) {
    fr.text(REPO_NAME, W / 2, by + ih + 70, { font: 'sans', size: 40, color: C.ink2, a: a6 * 0.95 });
    fr.text(OWNER + ' · ' + (LANG || 'Multi') + ' · Open Source', W / 2, by + ih + 122,
            { font: 'mono', size: 24, color: C.mute, a: a6 * 0.8 });
  }
}

function card2(fr, lt) {
  cardBox(fr, 1);
  fr.text('这个项目有多热', W / 2, 610, { font: 'sans', size: 44, color: C.ink, a: ss(lt, -0.06, 0.18) });
  fr.text('GitHub 上的真实数字', W / 2, 666, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.0, 0.22) });

  const cells = [[STARS, 'Star', C.stroke], [FORKS, 'Fork', C.blue], [CREATED.slice(5), 'Created', C.gold]];
  const cw = 260, gap = 40;
  const x0 = (W - (cw * 3 + gap * 2)) / 2;
  cells.forEach((c, i) => {
    const a = ss(lt, 0.02 + i * 0.05, 0.24 + i * 0.05);
    const x = x0 + i * (cw + gap), y = 762;
    fr.rect(x, y, cw, 250, { r: 26, fill: c[2], a: a * 0.10 });
    fr.rect(x, y, cw, 250, { r: 26, stroke: c[2], strokeW: 2, a: a * 0.55 });
    fr.text(c[0], x + cw / 2, y + 106, { font: 'sans', size: 68, color: c[2], a, align: 'c' });
    fr.text(c[1], x + cw / 2, y + 186, { font: 'sans', size: 26, color: C.mute, a, align: 'c' });
  });

  const tags = [LANG || 'Multi', 'Open Source', CREATED.slice(0, 7)].filter(Boolean);
  const tSize = 22, tGap = 14, tPad = 34;
  const widths = tags.map(t => fr.measure(t, { font: 'mono', size: tSize }) + tPad);
  const totalW = widths.reduce((a, b) => a + b, 0) + tGap * (tags.length - 1);
  let tx = (W - totalW) / 2;
  tags.forEach((t, i) => {
    const a = ss(lt, 0.16 + i * 0.05, 0.38 + i * 0.05);
    const tw = widths[i];
    fr.rect(tx, 1090, tw, 56, { r: 28, fill: '#EFE7D8', a: a * 0.9 });
    fr.text(t, tx + tw / 2, 1118, { font: 'mono', size: tSize, color: C.ink2, a });
    tx += tw + tGap;
  });
  fr.text('开源 · 可读 · 能跑', W / 2, 1250, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.3, 0.52) });
}

/* 按宽度折行：中文 1 字宽，拉丁 0.56；最多 maxLines 行 */
function wrapText(fr, str, maxW, size, maxLines) {
  const lines = [];
  let cur = '';
  for (const ch of Array.from(str)) {
    const w = /[\u4e00-\u9fff]/.test(ch) ? size : (ch === ' ' ? size * 0.3 : size * 0.56);
    if (fr.measure(cur + ch, { font: 'sans', size }) > maxW && cur) {
      lines.push(cur); cur = ch;
      if (lines.length >= maxLines - 1) { cur += ''; }
    } else {
      cur += ch;
    }
  }
  if (cur) lines.push(cur);
  const outl = lines.slice(0, maxLines);
  if (lines.length > maxLines) outl[maxLines - 1] = outl[maxLines - 1].slice(0, -1) + '…';
  return outl;
}

function card3(fr, lt) {
  cardBox(fr, 1);
  fr.text('它到底是干什么的', W / 2, 600, { font: 'sans', size: 44, color: C.ink, a: ss(lt, -0.06, 0.18) });
  const dl = wrapText(fr, TAGLINE, 830, 26, 2);
  dl.forEach((line, i) => {
    fr.text(line, W / 2, 672 + i * 42, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.0 + i * 0.05, 0.2) });
  });

  const a = ss(lt, 0.05, 0.28);
  const w1 = 700, x1 = (W - w1) / 2, y1 = 800;
  if (a > 0.003) {
    fr.g({ a }, () => shot(fr, REPO_IMG, x1, y1, w1, { r: 14, ring: C.stroke, ringA: 0.4 }));
  }
  const rk = ss(lt, 0.20, 0.6);
  if (rk > 0.004) ringMark(fr, x1 + w1 * 0.5, y1 + w1 * 0.22, 120, 34, rk, C.stroke, 4);
  fr.text('README 里写得清清楚楚', W / 2, 1310, { font: 'sans', size: 26, color: C.ink2, a: ss(lt, 0.4, 0.62) });
}

function card4(fr, lt) {
  cardBox(fr, 1);
  fr.text('上线才一个月', W / 2, 610, { font: 'sans', size: 46, color: C.ink, a: ss(lt, -0.06, 0.18) });
  fr.text('从 0 到 ' + STARS + ' Star 的速度', W / 2, 666, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.0, 0.22) });

  const ka = ss(lt, -0.06, 0.38);
  fr.text(STARS, W / 2, 850, { font: 'sans', size: 200, color: C.stroke, a: ka, glow: 30, glowColor: C.stroke, glowA: 0.3 });
  fr.text('Star', W / 2, 990, { font: 'sans', size: 32, color: C.ink2, a: ss(lt, 0.1, 0.3) });
  fr.text(CREATED + ' 上线', W / 2, 1070, { font: 'mono', size: 28, color: C.mute, a: ss(lt, 0.15, 0.35) });

  const rows = [['最早提交', CREATED], ['最近更新', (CT.pushed || CREATED)], ['语言', LANG || 'Multi']];
  rows.forEach((r, i) => {
    const a = ss(lt, 0.2 + i * 0.06, 0.44 + i * 0.06);
    const y = 1170 + i * 78;
    fr.rect(122, y - 30, 836, 66, { r: 16, fill: C.stroke, a: a * 0.09 });
    fr.text(r[0], 158, y, { font: 'sans', size: 24, color: C.mute, a, align: 'l' });
    fr.text(r[1], 922, y, { font: 'mono', size: 24, color: C.ink2, a, align: 'r' });
  });
}

function card5(fr, lt) {
  cardBox(fr, 1);
  fr.text('全是真代码', W / 2, 610, { font: 'sans', size: 46, color: C.ink, a: ss(lt, -0.06, 0.18) });
  fr.text(LANG + ' 写的 · 开源 MIT · 可以直接 fork', W / 2, 666, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.0, 0.22) });

  const topics = (CT.topics && CT.topics.length) ? CT.topics : ['open-source', LANG.toLowerCase(), 'tool'];
  const cols = 2, bw = 400, bh = 88, gx = 40, gy = 22;
  const x0 = (W - (cols * bw + gx)) / 2;
  topics.slice(0, 8).forEach((t, i) => {
    const a = ss(lt, 0.04 + i * 0.045, 0.26 + i * 0.045);
    const x = x0 + (i % cols) * (bw + gx), y = 760 + Math.floor(i / cols) * (bh + gy);
    fr.rect(x, y, bw, bh, { r: 20, fill: '#EFE7D8', a: a * 0.9 });
    fr.rect(x, y, bw, bh, { r: 20, stroke: C.stroke, strokeW: 2, a: a * 0.45 });
    fr.text('#' + t, x + bw / 2, y + bh / 2, { font: 'mono', size: 24, color: C.ink2, a, align: 'c' });
  });
  fr.text('标签写什么，它就是干什么的', W / 2, 1290, { font: 'sans', size: 26, color: C.ink2, a: ss(lt, 0.4, 0.62) });
}

function card6(fr, lt) {
  cardBox(fr, 1);
  fr.text('为什么值得看', W / 2, 610, { font: 'sans', size: 46, color: C.ink, a: ss(lt, -0.06, 0.18) });

  const pts = [
    ['1', STARS + ' Star · ' + FORKS + ' Fork', '一个月内攒出来的热度'],
    ['2', 'MIT 许可 · 全开源', '复制、改造、商用都行'],
    ['3', LANG + ' 单一语言栈', '看得懂，改得动'],
  ];
  pts.forEach((p, i) => {
    const a = ss(lt, 0.05 + i * 0.09, 0.28 + i * 0.09);
    const y = 760 + i * 178;
    fr.circle(196, y + 34, 34, { fill: C.stroke, a: a * 0.16 });
    fr.text(p[0], 196, y + 34, { font: 'mono', size: 30, color: C.stroke, a, align: 'c' });
    fr.text(p[1], 268, y + 16, { font: 'sans', size: 30, color: C.ink, a, align: 'l' });
    fr.text(p[2], 268, y + 62, { font: 'sans', size: 24, color: C.mute, a: a * 0.95, align: 'l' });
  });
  fr.text('不是概念，是能 clone 下来跑的仓库', W / 2, 1300, { font: 'sans', size: 26, color: C.ink2, a: ss(lt, 0.4, 0.62) });
}

function card7(fr, lt) {
  cardBox(fr, 1);
  fr.text('一行 clone 到本地', W / 2, 610, { font: 'sans', size: 44, color: C.ink, a: ss(lt, -0.06, 0.18) });

  const a1 = ss(lt, 0.02, 0.24);
  fr.rect(122, 672, 836, 200, { r: 20, fill: '#1E1F24', a: a1 * 0.95 });
  ['#FF6058', '#FFBD2E', '#28C840'].forEach((c, i) => fr.circle(158 + i * 26, 706, 8, { fill: c, a: a1 }));
  fr.text('$ git clone ' + (CT.url || ''), 156, 772, { font: 'mono', size: 22, color: C.green, a: a1, align: 'l' });
  fr.text('$ cd ' + REPO_NAME, 156, 820, { font: 'mono', size: 22, color: '#9AA0A8', a: a1, align: 'l' });

  const lines = [['完全开源', C.stroke], ['本地可跑', C.green], ['随便改', C.gold]];
  lines.forEach((l, i) => {
    const a = ss(lt, 0.1 + i * 0.09, 0.34 + i * 0.09);
    fr.text(l[0], W / 2, 960 + i * 100, { font: 'sans', size: 68, color: l[1], a });
  });
  fr.text('仓库名 ' + REPO_NAME + '，GitHub 搜得到', W / 2, 1300, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.4, 0.62) });
}

/* 结论卡：长镜 */
function card8(fr, lt) {
  cardBox(fr, 1);
  fr.text(HOOK, W / 2, 640, { font: 'sans', size: 56, color: C.ink, a: ss(lt, -0.06, 0.2) });
  fr.line(300, 760, 780, 760, { w: 2, color: C.line, a: ss(lt, 0.06, 0.3) });

  const lines = [[STARS + ' ★', C.stroke], [LANG || 'Multi', C.green], [CREATED.slice(0, 7) + ' 上线', C.gold]];
  lines.forEach((l, i) => {
    const a = ss(lt, 0.1 + i * 0.1, 0.36 + i * 0.1);
    fr.text(l[0], W / 2, 850 + i * 108, { font: 'sans', size: 78, color: l[1], a });
  });
  fr.text(CT.repo || (OWNER + '/' + REPO_NAME), W / 2, 1200, { font: 'mono', size: 30, color: C.ink2, a: ss(lt, 0.42, 0.64) });
  fr.text('MIT · 开源 · 可商用', W / 2, 1268, { font: 'sans', size: 26, color: C.mute, a: ss(lt, 0.5, 0.72) });
}

const CUES = [
  [T.c1, 'chord', { root: 0 }], [T.c2, 'chord', { root: 5 }],
  [T.c3, 'chord', { root: 3 }], [T.c4, 'chord', { root: 7 }],
  [T.c5, 'chord', { root: 5 }], [T.c6, 'chord', { root: 0 }],
  [T.c7, 'chord', { root: 3 }], [T.c8, 'chord', { root: 7 }],
  [0.15, 'tick'], [0.44, 'tick'], [0.72, 'tick'],
];

VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.55 },
  draw(fr, t) {
    fr.look.bgo = { color: C.bg };
    fr.look.bloom = 0.10;
    fr.look.grain = 0.04;
    fr.look.under = (ctx, tt) => {
      const P = RBG.plus || { gap: 96, arm: 9, alpha: 0.075, accent: 0.16 };
      const gap = P.gap, arm = P.arm;
      ctx.save();
      const dx = (tt * 0.6) % gap, dy = (tt * 0.35) % gap;
      for (let gy = -gap; gy < H + gap; gy += gap) {
        for (let gx = -gap; gx < W + gap; gx += gap) {
          const i = Math.round((gx + 2000) / gap) * 131 + Math.round((gy + 2000) / gap) * 17;
          const acc = hash(i) > 0.90;
          const a = acc ? P.accent : P.alpha;
          const scl = acc ? 1.25 : 1;
          const x = gx + dx + (hash(i + 7) - 0.5) * 14;
          const y = gy + dy + (hash(i + 11) - 0.5) * 14;
          ctx.fillStyle = 'rgba(255,255,255,' + a + ')';
          ctx.fillRect(x - arm * scl, y - 0.9, arm * 2 * scl, 1.8);
          ctx.fillRect(x - 0.9, y - arm * scl, 1.8, arm * 2 * scl);
        }
      }
      const g = ctx.createRadialGradient(W / 2, H * 0.42, W * 0.34, W / 2, H * 0.42, W * 1.10);
      g.addColorStop(0, 'rgba(0,0,0,0)');
      g.addColorStop(1, 'rgba(0,0,0,0.38)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      ctx.restore();
    };

    header(fr, t, HOOK, SUB);
    seriesBadge(fr, t);
    flashNum(fr, t);

    const segs = [
      [T.c1, T.c2, card1], [T.c2, T.c3, card2],
      [T.c3, T.c4, card7], [T.c4, T.c5, card8],
    ];
    segs.forEach(s => {
      const a = s[0], b = s[1], fn = s[2];
      if (t < a || t >= b) return;
      const kk = 1 - seg(t, b - 0.05, b);
      if (kk <= 0.002) return;
      const ctx = fr.x;
      fr.g({ a: kk }, () => { ctx.save(); ctx.translate(0, SHIFT); fn(fr, t - a); ctx.restore(); });
    });

    subtitles(fr, t);
    for (const s of SUBS) if (Math.abs(t - s.a) < 0.02) fr.sfx(s.a, 'tick');
    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }
    const ta = ss(t, 0.5, 1.2) * 0.85;
    fr.text(timecode(t), 74, H - 74, { font: 'mono', size: 22, color: '#6A6A75', a: ta, align: 'l' });
    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.04, '#000000');
  },
});
})();
