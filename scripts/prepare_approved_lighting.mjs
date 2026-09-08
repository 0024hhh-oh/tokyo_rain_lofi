import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {prepareProfile} from '../experiments/depth-lighting/prepare-profile.mjs';

const profilesDir = new URL('../experiments/depth-lighting/profiles/', import.meta.url);
export async function prepareApprovedLighting(assetDir, publicDir, propsPath) {
  await fs.rm(propsPath, {force:true});
  for (const name of ['background.png','background.jpg','background.jpeg']) {
    const source=path.join(assetDir,name);
    let image;
    try { image=await fs.readFile(source); } catch(e) { if(e.code==='ENOENT') continue; throw e; }
    if (!image.length) continue;
    const hash=createHash('sha256').update(image).digest('hex');
    for(const filename of ['tokyo-approved.json','river-night.json','street-night.json']) {
      const profilePath=new URL(filename,profilesDir);
      const profile=JSON.parse(await fs.readFile(profilePath,'utf8'));
      if(profile.source.sha256!==hash) continue;
      await prepareProfile(profilePath,source,publicDir,propsPath);
      return true;
    }
    console.log('No approved lighting mask for this image; keeping the original background.');
    return false;
  }
  throw new Error('No background image found');
}
if(process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
  const [assetDir,publicDir,propsPath]=process.argv.slice(2);
  if(!assetDir || !publicDir || !propsPath) throw new Error('Expected ASSET_DIR PUBLIC_DIR PROPS_PATH');
  await prepareApprovedLighting(assetDir,publicDir,propsPath);
}
