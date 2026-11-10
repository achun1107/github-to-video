#!/usr/bin/env node
/**
 * recipe.mjs — recipe.json → recipe.js
 *
 *   node tools/recipe.mjs [工程目录]
 *
 * recipe.json 是 cangjie 蒸馏产物（skill/）落地成的版式常量：
 * 卡框、标题、说明条、底色网格、关键词、切镜表。film.js 只读 window.RECIPE。
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const root = resolve(process.argv[2] || join(HERE, '..'));
const recipe = JSON.parse(readFileSync(join(root, 'recipe.json'), 'utf8'));

const need = ['hook', 'card', 'chip', 'bg'];
const missing = need.filter(k => !recipe[k]);
if (missing.length) {
  console.error('recipe.json 缺字段:', missing.join(', '));
  process.exit(1);
}

writeFileSync(
  join(root, 'recipe.js'),
  '/* 自动生成，勿手改：node tools/recipe.mjs（读 recipe.json，来自 cangjie 蒸馏包 skill/） */\n' +
  'window.RECIPE = ' + JSON.stringify(recipe, null, 2) + ';\n',
  'utf8'
);
console.log('recipe.js ←', recipe.hook.line1, '| 卡', recipe.card.w + '×' + recipe.card.h, '| 说明条 y', recipe.chip.y);
