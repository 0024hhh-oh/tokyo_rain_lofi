import sharp from 'sharp';
import assert from 'node:assert/strict';
const dir='dist/depth-lighting';
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
