import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {intensity, layers, type Depth} from './timing';

import approvedProfile from './profiles/tokyo-approved.json';

type LightPair = {id: string; depth: Depth; sourceMask: string; reflectionMask: string; reflectionGain: number};
export type LightingProfile = typeof approvedProfile & {pairs?: LightPair[]; emitters?: {id: string; depth: Depth; sourceMask: string}[]; timing?: {windows: Record<Depth, [number, number][]>; fadeFrames: number}};
const mask = (profile: LightingProfile, shape: string, blur: number) => `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="${profile.source.width}" height="${profile.source.height}" viewBox="0 0 ${profile.source.width} ${profile.source.height}"><defs><filter id="b" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="${blur}"/></filter></defs><g fill="white" filter="url(#b)">${shape}</g></svg>`)}")`;

export const Scene: React.FC<{baseline?: boolean; profile?: LightingProfile}> = ({baseline = false, profile = approvedProfile as LightingProfile}) => {
  const frame = useCurrentFrame();
  const units: LightPair[] = [...(profile.pairs ?? layers.map(depth => ({id:depth,depth,sourceMask:profile.layers[depth],reflectionMask:'',reflectionGain:0}))), ...(profile.emitters ?? []).map(e => ({...e, reflectionMask:'', reflectionGain:0}))];
  const source = staticFile(profile.source.file);
  return <AbsoluteFill style={{background: '#07121d', overflow: 'hidden', isolation:'isolate'}}>
    {/* A single common plane preserves EXACT registration of image and masks. */}
    <div style={{position:'absolute', width:'100%', aspectRatio:`${profile.source.width} / ${profile.source.height}`, top:'50%', transform:'translateY(-50%)'}}>
      <Img src={source} style={{display:'block',width:'100%'}}/>
      {!baseline && units.map(unit => {
        const pulse = intensity(frame,unit.depth,profile.timing?.windows,profile.timing?.fadeFrames);
        const core = mask(profile,unit.sourceMask,profile.style.coreBlur);
        const halo = mask(profile,unit.sourceMask,profile.style.haloBlur);
        const reflection = mask(profile,unit.reflectionMask,3);
        return <React.Fragment key={unit.id}>
          <AbsoluteFill style={{mixBlendMode:'screen',opacity:pulse*profile.style.coreOpacity,maskImage:core,WebkitMaskImage:core,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
            <Img src={source} style={{width:'100%',filter:`brightness(${profile.style.coreBrightness})`}}/>
          </AbsoluteFill>
          <AbsoluteFill style={{mixBlendMode:'screen',opacity:pulse*profile.style.haloOpacity,maskImage:halo,WebkitMaskImage:halo,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
            <Img src={source} style={{width:'100%',filter:`brightness(${profile.style.haloBrightness}) blur(${profile.style.imageBlur}px)`}}/>
          </AbsoluteFill>
          {unit.reflectionMask && <AbsoluteFill style={{mixBlendMode:'screen',opacity:pulse*unit.reflectionGain,maskImage:reflection,WebkitMaskImage:reflection,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
            <Img src={source} style={{width:'100%'}}/>
          </AbsoluteFill>}
        </React.Fragment>;
      })}
    </div>
  </AbsoluteFill>;
};

export const Comparison: React.FC<{profile?: LightingProfile}> = ({profile = approvedProfile as LightingProfile}) => {
  const frame=useCurrentFrame();
  const active=layers.filter(d=>intensity(frame,d,profile.timing?.windows,profile.timing?.fadeFrames)>0.01).join(' + ') || 'baseline';
  return <AbsoluteFill style={{background:'#07121d',color:'white',fontFamily:'Arial'}}>
    <div style={{position:'absolute',top:180,left:0,width:960,height:540}}><Scene baseline profile={profile}/></div>
    <div style={{position:'absolute',top:180,left:960,width:960,height:540}}><Scene profile={profile}/></div>
    <div style={{position:'absolute',top:90,left:60,fontSize:42}}>ORIGINAL</div>
    <div style={{position:'absolute',top:90,left:1020,fontSize:42}}>LIGHTING TEST</div>
    <div style={{position:'absolute',top:780,left:60,fontSize:38}}>{(frame/30).toFixed(1)}s / active: {active}</div>
    <div style={{position:'absolute',top:855,left:60,fontSize:28,color:'#a9bdcf'}}>BACK / MIDDLE / FRONT: image-specific light masks</div>
  </AbsoluteFill>;
};
