import sharp from 'sharp';
import assert from 'node:assert/strict';
const dir=process.argv[2] ?? 'dist/depth-lighting';
const decode=async name=>sharp(`${dir}/${name}.png`).removeAlpha().raw().toBuffer({resolveWithObject:true});
const base=await decode('baseline');
for(const name of ['back','middle','front','end']){
  const im=await decode(name);
  assert.deepEqual(im.info,base.info);
  let changed=0,darkened=0,total=0,max=0;
  for(let i=0;i<base.data.length;i+=3){
    let delta=0;
    for(let c=0;c<3;c++){
      const d=im.data[i+c]-base.data[i+c];
      if(d < -2) darkened++;
      delta+=Math.abs(d)/3;
      max=Math.max(max,Math.abs(d));
    }
    total+=delta;
    if(delta>8)changed++;
  }
  const pixels=im.info.width*im.info.height;
  console.log({name,changedPixels:changed,meanDifference:total/pixels,maxChannelDifference:max,darkenedChannels:darkened});
  if(name==='end') assert.equal(max,0,'Last frame must exactly match baseline');
  else{
    assert.ok(changed>500,`${name} light change too weak`);
    assert.ok(changed/pixels<0.25,'Do not flash the whole scene');
    assert.equal(darkened,0,'Screen lighting must not dim the source');
  }
}

// Paired scenes must visibly change the emitter, with a weaker synchronized reflection.
const {readFile} = await import('node:fs/promises');
const {profile} = JSON.parse(await readFile(`${dir}/props.json`, 'utf8'));
if (profile.pairs) {
  const meanDelta = (im, roi) => {
    const scaleX=im.info.width/profile.source.width, scaleY=im.info.height/profile.source.height;
    let total=0,count=0;
    for(let y=Math.floor(roi[1]*scaleY);y<Math.ceil(roi[3]*scaleY);y++)
      for(let x=Math.floor(roi[0]*scaleX);x<Math.ceil(roi[2]*scaleX);x++) {
        const i=(y*im.info.width+x)*3;
        total+=(im.data[i]-base.data[i]+im.data[i+1]-base.data[i+1]+im.data[i+2]-base.data[i+2])/3;count++;
      }
    return total/count;
  };
  for (const emitter of profile.emitters ?? []) {
    const im = await decode(emitter.depth);
    const delta = meanDelta(im, emitter.sourceRoi);
    console.log({windows: emitter.id, meanIncrease: delta});
    assert.ok(delta > 8, 'Selected window light must visibly brighten');
  }
  for(const pair of profile.pairs) {
    const im=await decode(pair.depth);
    const emitter=meanDelta(im,pair.sourceRoi),reflection=meanDelta(im,pair.reflectionRoi);
    console.log({pair:pair.id,emitterMeanIncrease:emitter,reflectionMeanIncrease:reflection});
    assert.ok(emitter>8, 'Emitter itself must visibly brighten');
    if (profile.disableReflections) {
      assert.ok(Math.abs(reflection)<1, 'Disabled water reflection must not brighten (sub-level tolerance for nearby emitter bloom)');
    } else {
      assert.ok(reflection>0.2 && reflection<emitter*.5, 'Reflection must remain weaker than emitter');
    }
    for(const other of profile.pairs.filter(p=>p.id!==pair.id)) {
      assert.equal(meanDelta(im,other.sourceRoi),0,'Inactive emitter must remain unchanged');
      assert.equal(meanDelta(im,other.reflectionRoi),0,'No orphan reflection pulse');
    }
    assert.equal(meanDelta(im,[1050,700,1110,815]),0,'Unverified right-hand white reflection must remain unchanged');
  }
}
