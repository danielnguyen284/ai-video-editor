import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {ensureBrowser, renderMedia, selectComposition} from '@remotion/renderer';

const root = path.dirname(fileURLToPath(import.meta.url));
const candidates = [process.env.AI_EDITOR_BROWSER, 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'];
const browserExecutable = candidates.find((candidate) => candidate && fs.existsSync(candidate));

if (process.argv[2] === '--doctor') {
  console.log(JSON.stringify({remotion: '4.0.536', browser: browserExecutable ?? 'Remotion will download Chrome Headless Shell on first render'}));
} else {
  const [requestFile, output] = process.argv.slice(2);
  if (!requestFile || !output) throw new Error('Usage: node render.mjs request.json output.mov');
  const inputProps = JSON.parse(fs.readFileSync(requestFile, 'utf8').replace(/^\uFEFF/, ''));
  if (!browserExecutable) await ensureBrowser();
  console.log('Bundling Remotion composition...');
  const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.tsx'), outDir: path.join(root, '.cache/bundle'), enableCaching: true});
  console.log('Selecting composition with browser:', browserExecutable ?? 'headless-shell');
  const composition = await selectComposition({serveUrl, id: 'MotionAsset', inputProps, browserExecutable});
  console.log('Rendering transparent ProRes asset...');
  await renderMedia({
    composition, serveUrl, inputProps, browserExecutable, outputLocation: output,
    codec: 'prores', proResProfile: '4444', pixelFormat: 'yuva444p10le', imageFormat: 'png',
    concurrency: 2, logLevel: 'warn',
  });
  console.log(output);
}
