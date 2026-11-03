// Renders docs/manual/build_manual.html?video=1 to MP4 (no audio) by seeking window.__seek frame by frame.
// npm i puppeteer; needs ffmpeg.   node tools/render_manual_video.mjs docs/manual/build_manual.html docs/manual/build_manual.mp4 24
import puppeteer from 'puppeteer';
import { spawn } from 'node:child_process';
import path from 'node:path';

const SRC = path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3]);
const FPS = Number(process.argv[4] || 24), W = 1920, H = 1080;
const CHROME = process.env.CHROME;   // optional: path to a Chrome; default = the one puppeteer downloads

const browser = await puppeteer.launch({
  ...(CHROME ? { executablePath: CHROME } : {}), headless: true,
  args: CHROME ? ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] : ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'],
});
try {
  const page = await browser.newPage();
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto('file:///' + SRC.replace(/\\/g, '/') + '?video=1', { waitUntil: 'load', timeout: 180000 });
  await page.waitForFunction('window.__ready && typeof window.__seek === "function" && window.__duration > 0', { timeout: 120000 });
  await page.evaluate(() => document.fonts.ready);
  const dur = await page.evaluate(() => window.__duration);
  const frames = Math.ceil(dur * FPS);
  console.log(`duration ${dur.toFixed(1)} s, ${frames} frames`);
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT],
    { stdio: ['pipe', 'ignore', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => new Promise(r => { window.__seek(t); requestAnimationFrame(() => requestAnimationFrame(r)); }), f / FPS);
    const img = await page.screenshot({ type: 'jpeg', quality: 92, optimizeForSpeed: true });
    if (!ff.stdin.write(img)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 240 === 0) console.log(`frame ${f}/${frames}`);
  }
  ff.stdin.end();
  await done;
} finally {
  await browser.close();
}
console.log('done', OUT);
