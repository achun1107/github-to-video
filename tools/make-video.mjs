#!/usr/bin/env node
/**
 * make-video.mjs — 一条命令：仓库 → 内容 → 渲染 → 混音
 *
 *   node tools/make-video.mjs --repo https://github.com/webkubor/xiaobai-kanban \
 *        --out ./video-xiaobai --jobs 3
 *
 *   node tools/make-video.mjs --repo ../_read/xiaobai-kanban --no-render   # 只抽内容
 *
 * 做的事：
 *   1. 仓库是 URL 就浅克隆到 <out>/_repos/<name>（已存在则 fetch）
 *   2. extract-content.mjs 抽 name/headline/chapters → content.json → content.js
 *   3. engine/render.py 渲画面（raw.mp4）
 *   4. engine/render.py --events + engine/audio.py --wav-only 出配乐
 *   5. tools/mix.py 混上 audio/vo*.mp3（若存在）
 *
 * 不自动做的事：文案创意（字幕 SUBS、标题、卡片内容）。那些是导演工作，
 * 改 film.js 即可——本脚本只保证「数据 + 流水线」自动。
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
import { join, basename, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : def;
}
const has = name => process.argv.includes(name);

const repoArg = arg('--repo');
if (!repoArg) {
  console.error('用法: node tools/make-video.mjs --repo <url|目录> [--out <工程目录>] [--jobs N] [--no-render]');
  process.exit(2);
}
const outDir = resolve(arg('--out', ROOT));
const jobs = arg('--jobs', '3');
const noRender = has('--no-render');

const run = (cmd, args, opts = {}) => {
  console.log(`\n$ ${cmd} ${args.join(' ')}`);
  execFileSync(cmd, args, { stdio: 'inherit', cwd: opts.cwd || outDir, ...opts });
};

/* 1 · 仓库就位 */
let repoDir;
if (/^https?:\/\//.test(repoArg) || repoArg.startsWith('git@')) {
  const name = basename(repoArg).replace(/\.git$/, '');
  repoDir = join(outDir, '_repos', name);
  mkdirSync(dirname(repoDir), { recursive: true });
  if (existsSync(join(repoDir, '.git'))) {
    try { run('git', ['-C', repoDir, 'fetch', '--depth', '1', 'origin'], { cwd: outDir }); }
    catch { console.warn('fetch 失败，用本地已有副本继续'); }
  } else {
    run('git', ['-c', 'credential.helper=', 'clone', '--depth', '1', repoArg, repoDir], { cwd: outDir });
  }
} else {
  repoDir = resolve(repoArg);
  if (!existsSync(repoDir)) { console.error(`仓库目录不存在: ${repoDir}`); process.exit(2); }
}

/* 2 · 抽内容 */
run(process.execPath, [join(HERE, 'extract-content.mjs'), repoDir, '-o', join(outDir, 'content.json')]);

const content = JSON.parse(readFileSync(join(outDir, 'content.json'), 'utf8'));
writeFileSync(join(outDir, 'content.js'),
  'window.CONTENT = ' + JSON.stringify(content, null, 2) + ';\n', 'utf8');
console.log(`content.js → ${join(outDir, 'content.js')}`);
console.log(`  站点 ${content.name} / 标题 ${content.headline} / 目录 ${content.chapters.length} 条`);

if (noRender) { console.log('\n--no-render：内容已更新，渲染跳过。'); process.exit(0); }

/* 2.5 · 版式参数：recipe.json → recipe.js（cangjie 蒸馏出的参考片常量） */
run(process.execPath, [join(HERE, 'recipe.mjs'), outDir]);

/* 3 · 渲染画面（并行失败自动回落串行：多开 Chrome 在机器压力大时会挂） */
const PY = process.env.PYTHON || 'python';
try {
  run(PY, [join(outDir, 'engine/render.py'), outDir, '--jobs', jobs]);
} catch (e) {
  if (Number(jobs) > 1) {
    console.warn(`\n并行渲染失败（${jobs} 路），回落串行重渲一次…`);
    run(PY, [join(outDir, 'engine/render.py'), outDir]);
  } else {
    throw e;
  }
}

/* 4 · 配乐 */
try {
  run(PY, [join(outDir, 'engine/render.py'), outDir, '--events']);
  run(PY, [join(outDir, 'engine/audio.py'), outDir, '--wav-only']);
} catch (e) {
  console.warn('配乐步骤失败（继续）：', e.message);
}

/* 5 · 混音 */
const hasVo = existsSync(join(outDir, 'audio/vo1.mp3')) || existsSync(join(outDir, 'audio/vo2.mp3'));
try {
  run(PY, [join(HERE, 'mix.py'), outDir, '--lufs', '-14', '--bg', '0.16', ...(hasVo ? [] : ['--no-vo'])]);
} catch (e) {
  console.warn('混音失败（保留无声版）：', e.message);
}

const finalMp4 = join(outDir, 'renders/final.mp4');
if (existsSync(finalMp4)) {
  console.log(`\n✓ 成片 → ${finalMp4}`);
} else {
  console.log(`\n完成画面 → ${join(outDir, 'renders/raw.mp4')}`);
}
