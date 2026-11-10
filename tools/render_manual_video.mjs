// Renders docs/manual/build_manual.html?video=1 to MP4 (no audio) by seeking window.__seek frame by frame.
// npm i puppeteer; needs ffmpeg.   node tools/render_manual_video.mjs docs/manual/build_manual.html docs/manual/build_manual.mp4 24 [startSec] [endSec]
// startSec/endSec (optional) render only that time range, e.g. to shard the render over several processes and join the parts with ffmpeg's concat demuxer.
// If the CDN (cdn.jsdelivr.net) is unreachable, three.js is served from node_modules/three (npm i three@0.160.0) via request interception.
import puppeteer from 'puppeteer';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const SRC = path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3]);
const FPS = Number(process.argv[4] || 24), W = 1920, H = 1080;
const T0 = Number(process.argv[5] || 0), T1 = process.argv[6] ? Number(process.argv[6]) : Infinity;
const CHROME = process.env.CHROME;   // optional: path to a Chrome; default = the one puppeteer downloads

const browser = await puppeteer.launch({
  ...(CHROME ? { executablePath: CHROME } : {}), headless: true,
  args: CHROME ? ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] : ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'],
});
try {
  const page = await browser.newPage();
  const pageErrors = [];
  page.on('pageerror', e => { console.error('PAGE ERROR', e.message); pageErrors.push(e.message); });
  // Serve three.js locally when a copy is installed (the CDN may be blocked, e.g. in a sandbox).
  const THREE_DIR = path.resolve(process.env.THREE_DIR || 'node_modules/three');
  if (fs.existsSync(path.join(THREE_DIR, 'build/three.module.js'))) {
    await page.setRequestInterception(true);
    page.on('request', req => {
      const m = req.url().match(/^https:\/\/cdn\.jsdelivr\.net\/npm\/three@[^/]+\/(.+)$/);
      const f = m && path.join(THREE_DIR, m[1]);
      if (f && fs.existsSync(f)) req.respond({ status: 200, contentType: 'text/javascript', headers: { 'access-control-allow-origin': '*' }, body: fs.readFileSync(f) });
      else req.continue();
    });
  }
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto('file:///' + SRC.replace(/\\/g, '/') + '?video=1', { waitUntil: 'load', timeout: 180000 });
  await page.waitForFunction('window.__ready && typeof window.__seek === "function" && window.__duration > 0', { timeout: 120000 });
  await page.evaluate(() => document.fonts.ready);
  const dur = await page.evaluate(() => window.__duration);
  const fStart = Math.round(T0 * FPS), fEnd = Math.min(Math.ceil(dur * FPS), Math.ceil(T1 * FPS));
  const frames = fEnd;
  console.log(`duration ${dur.toFixed(1)} s, frames ${fStart}..${fEnd}`);
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT],
    { stdio: ['pipe', 'ignore', 'inherit'] });
  const done = new Promise((res, rej) => {
    ff.on('error', rej);
    ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)));
  });
  ff.stdin.on('error', () => {}); // surfaced via the 'close'/'error' handlers above, not here
  for (let f = fStart; f < fEnd; f++) {
    await page.evaluate(t => new Promise(r => { window.__seek(t); requestAnimationFrame(() => requestAnimationFrame(r)); }), f / FPS);
    const img = await page.screenshot({ type: 'jpeg', quality: 92, optimizeForSpeed: true });
    if (!ff.stdin.write(img)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 240 === 0) console.log(`frame ${f}/${frames}`);
  }
  ff.stdin.end();
  await done;
  if (pageErrors.length) throw new Error(`${pageErrors.length} page error(s) during render; output may be corrupt`);
} finally {
  await browser.close();
}
console.log('done', OUT);
