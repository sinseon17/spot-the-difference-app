#!/usr/bin/env node
/**
 * Capacitor에 넣을 웹 앱 사본을 www/ 로 복사합니다.
 * 저장소 루트는 그대로 정적 사이트로 배포할 수 있고(GitHub Pages·Vercel),
 * www/ 는 안드로이드 빌드용으로만 쓰이는 생성 폴더입니다.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'www');
const FILES = ['index.html', 'styles.css', 'app.js', 'stages.js', 'manifest.json', 'sw.js'];
const DIRS = ['images', 'icons'];

function rmrf(p) {
  if (!fs.existsSync(p)) return;
  fs.rmSync(p, { recursive: true, force: true });
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

rmrf(OUT);
fs.mkdirSync(OUT, { recursive: true });

let count = 0;
for (const f of FILES) {
  const src = path.join(ROOT, f);
  if (!fs.existsSync(src)) {
    console.error(`missing: ${f}`);
    process.exit(1);
  }
  fs.copyFileSync(src, path.join(OUT, f));
  count += 1;
}
for (const d of DIRS) copyDir(path.join(ROOT, d), path.join(OUT, d));

const total = DIRS.reduce((n, d) => n + fs.readdirSync(path.join(OUT, d), { recursive: true }).length, count);
console.log(`www/ ready — ${total} files copied from the project root`);
