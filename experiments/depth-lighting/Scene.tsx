import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {intensity, layers, type Depth} from './timing';

import approvedProfile from './profiles/tokyo-approved.json';

export type LightingProfile = typeof approvedProfile;
const mask = (profile: LightingProfile, depth: Depth, blur: number) => `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="${profile.source.width}" height="${profile.source.height}" viewBox="0 0 ${profile.source.width} ${profile.source.height}"><defs><filter id="b" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="${blur}"/></filter></defs><g fill="white" filter="url(#b)">${profile.layers[depth]}</g></svg>`)}")`;

export const Scene: React.FC<{baseline?: boolean; profile?: LightingProfile}> = ({baseline = false, profile = approvedProfile}) => {
  const frame = useCurrentFrame();
  const masks = Object.fromEntries(layers.map(d => [d, {core: mask(profile, d, profile.style.coreBlur), halo: mask(profile, d, profile.style.haloBlur)}])) as Record<Depth, {core:string;halo:string}>;
  const source = staticFile(profile.source.file);
  return <AbsoluteFill style={{background: '#07121d', overflow: 'hidden', isolation:'isolate'}}>
    {/* A single common plane preserves EXACT registration of image and masks. */}
    <div style={{position:'absolute', width:'100%', aspectRatio:`${profile.source.width} / ${profile.source.height}`, top:'50%', transform:'translateY(-50%)'}}>
      <Img src={source} style={{display:'block',width:'100%'}}/>
      {!baseline && layers.map(depth => <React.Fragment key={depth}>
        <AbsoluteFill style={{mixBlendMode:'screen',opacity:intensity(frame,depth)*profile.style.coreOpacity,maskImage:masks[depth].core,WebkitMaskImage:masks[depth].core,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
          <Img src={source} style={{width:'100%',filter:`brightness(${profile.style.coreBrightness})`}}/>
        </AbsoluteFill>
        <AbsoluteFill style={{mixBlendMode:'screen',opacity:intensity(frame,depth)*profile.style.haloOpacity,maskImage:masks[depth].halo,WebkitMaskImage:masks[depth].halo,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
          <Img src={source} style={{width:'100%',filter:`brightness(${profile.style.haloBrightness}) blur(${profile.style.imageBlur}px)`}}/>
        </AbsoluteFill>
      </React.Fragment>)}
    </div>
  </AbsoluteFill>;
};

export const Comparison: React.FC<{profile?: LightingProfile}> = ({profile = approvedProfile}) => {
  const frame=useCurrentFrame();
  const active=layers.filter(d=>intensity(frame,d)>0.01).join(' + ') || 'baseline';
  return <AbsoluteFill style={{background:'#07121d',color:'white',fontFamily:'Arial'}}>
    <div style={{position:'absolute',top:180,left:0,width:960,height:540}}><Scene baseline profile={profile}/></div>
    <div style={{position:'absolute',top:180,left:960,width:960,height:540}}><Scene profile={profile}/></div>
    <div style={{position:'absolute',top:90,left:60,fontSize:42}}>ORIGINAL</div>
    <div style={{position:'absolute',top:90,left:1020,fontSize:42}}>LIGHTING TEST</div>
    <div style={{position:'absolute',top:780,left:60,fontSize:38}}>{(frame/30).toFixed(1)}s / active: {active}</div>
    <div style={{position:'absolute',top:855,left:60,fontSize:28,color:'#a9bdcf'}}>BACK: station / MIDDLE: trains + signals / FRONT: house lights</div>
  </AbsoluteFill>;
};
