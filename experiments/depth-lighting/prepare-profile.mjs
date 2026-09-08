import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import sharp from 'sharp';

export async function validateProfile(profile, image) {
  if (profile.version !== 1) throw new Error('Unsupported lighting profile version');
  if (profile.disableReflections !== undefined && typeof profile.disableReflections !== 'boolean') throw new Error('Invalid reflection disable flag');
  const {source, style, layers} = profile;
  if (!source || !/^[a-f0-9]{64}$/.test(source.sha256)) throw new Error('Missing source SHA-256');
  if (createHash('sha256').update(image).digest('hex') !== source.sha256)
    throw new Error('Image does not match lighting mask: prepare a profile for this image');
  const metadata = await sharp(image).metadata();
  if (metadata.width !== source.width || metadata.height !== source.height || (metadata.orientation ?? 1) !== 1)
    throw new Error('Source dimensions/orientation do not match profile');
  if (typeof source.file !== 'string' || !/^depth-lighting\/[a-zA-Z0-9_-]+\.(jpg|jpeg|png)$/.test(source.file))
    throw new Error('Source must be a local depth-lighting image');
  for (const d of ['back','middle','front']) if (!layers?.[d]) throw new Error('Missing source layer');
  const shapesToValidate = Object.entries(layers ?? {});
  if (profile.scheduledLights) {
    if (!profile.disableReflections || !Array.isArray(profile.scheduledLights) || !profile.scheduledLights.length) throw new Error('Scheduled sources require reflections disabled');
    for (const light of profile.scheduledLights) {
      const w = light.pulseWindow;
      if (!light.building || !['back','middle','front'].includes(light.depth) || light.reflectionMask !== '' || light.reflectionGain !== 0 || !Array.isArray(w) || w.length!==2 || !w.every(Number.isInteger) || w[0]<1 || w[1]>899 || w[1]-w[0]<30) throw new Error('Invalid scheduled source');
      shapesToValidate.push([light.id,light.sourceMask]);
    }
    for (let frame=0;frame<900;frame++) {
      const active=profile.scheduledLights.filter(l=>frame>l.pulseWindow[0] && frame<l.pulseWindow[1]);
      if(active.length>3 || new Set(active.map(l=>l.building)).size!==active.length) throw new Error('Too many simultaneous lights');
    }
  }
  if (profile.pairs) {
    if (!Array.isArray(profile.pairs) || profile.pairs.length !== 3 || new Set(profile.pairs.map(p=>p.depth)).size !== 3) throw new Error('Expected three unique source-reflection pairs');
    for (const pair of profile.pairs) {
      if (!['back','middle','front'].includes(pair.depth) || pair.sourceMask !== layers[pair.depth] || !Number.isFinite(pair.reflectionGain) || pair.reflectionGain <= 0 || pair.reflectionGain > .25) throw new Error('Invalid source-reflection pair');
      shapesToValidate.push([pair.id, pair.reflectionMask]);
    }
  }
  if (profile.emitters) {
    if (!Array.isArray(profile.emitters) || profile.emitters.length > 30) throw new Error('Invalid standalone emitters');
    for (const emitter of profile.emitters) {
      if (!['back','middle','front'].includes(emitter.depth) || !emitter.id || 'reflectionMask' in emitter || 'reflectionGain' in emitter) throw new Error('Standalone emitters cannot animate reflections');
      shapesToValidate.push([emitter.id, emitter.sourceMask]);
    }
  }
  for (const [depth, shapes] of shapesToValidate) {
    // Only inert numeric path/ellipse shapes: no scripts, URLs, styles or SVG filters.

    if (typeof shapes !== 'string' || !shapes.trim()) throw new Error(`Missing ${depth} mask`);
    const stripped = shapes.replace(/<(path|ellipse)\s+(?:(?:d|cx|cy|rx|ry|opacity)="[MmLlHhVvCcSsQqTtAaZz0-9.,\s+\-]+"\s*)+\/>/g, '').trim();
    if (stripped) throw new Error(`Invalid ${depth} mask`);
  }
  for (const [key, max] of Object.entries({coreOpacity:1,haloOpacity:1,coreBrightness:5,haloBrightness:5,coreBlur:30,haloBlur:30,imageBlur:30})) {
    if (!Number.isFinite(style?.[key]) || style[key] < 0 || style[key] > max)
      throw new Error(`Invalid lighting style: ${key}`);
  }
  if (profile.timing) {
    const {windows, fadeFrames} = profile.timing;
    if (!Number.isFinite(fadeFrames) || fadeFrames < 6 || fadeFrames > 60) throw new Error('Invalid fade');
    for (const depth of ['back','middle','front']) {
      if (!Array.isArray(windows?.[depth]) || !windows[depth].length) throw new Error('Missing pulse schedule');
      for (const pair of windows[depth]) {
        if (!Array.isArray(pair) || pair.length !== 2 || !pair.every(Number.isInteger) || pair[0] < 1 || pair[1] > 899 || pair[1]-pair[0] < fadeFrames*2) throw new Error('Invalid pulse window');
      }
    }
  }
  return profile;
}

export async function prepareProfile(profilePath, imagePath, publicDir, propsPath) {
  const profile = JSON.parse(await fs.readFile(profilePath, 'utf8'));
  const image = await fs.readFile(imagePath);
  await validateProfile(profile, image); // Validate everything before writing any outputs.
  const destination = path.join(publicDir, profile.source.file);
  await fs.mkdir(path.dirname(destination), {recursive:true});
  await fs.mkdir(path.dirname(propsPath), {recursive:true});
  await fs.writeFile(destination, image);
  await fs.writeFile(propsPath, JSON.stringify({profile}, null, 2) + '\n');
  console.log(`Validated image-specific lighting profile: ${profile.source.sha256}`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  if (args.length !== 4) throw new Error('Usage: node prepare-profile.mjs PROFILE IMAGE PUBLIC_DIR PROPS_JSON');
  await prepareProfile(...args);
}
