import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {intensity, layers, type Depth} from './timing';

// Hand-selected existing lamps/windows in the supplied 1536 x 869 image.
// These are light masks, NOT horizontal bands or complete building cutouts.
const shapes: Record<Depth, string> = {
  back: `<path d="M0 121 L890 121 L890 161 L0 164Z"/>
    <path d="M281 38 L349 38 L349 50 L281 50Z"/>
    <path d="M660 32 L688 32 L686 107 L659 106Z"/>
    <path d="M1210 28 L1239 28 L1240 161 L1210 161Z"/>
    <path d="M1395 130 L1520 120 L1520 163 L1395 164Z"/>
    <path d="M891 139 L1111 143 L1111 164 L891 161Z"/>`,
  middle: `<path d="M970 176 L1056 190 L1056 205 L970 192Z"/>
    <path d="M1135 207 L1344 244 L1344 265 L1135 225Z"/>
    <path d="M1370 254 L1535 284 L1535 306 L1370 275Z"/>
    <ellipse cx="922" cy="267" rx="5" ry="7"/>
    <ellipse cx="1013" cy="177" rx="4" ry="6"/>
    <ellipse cx="1489" cy="267" rx="4" ry="6"/>
    <ellipse cx="895" cy="244" rx="4" ry="5"/>
    <ellipse cx="724" cy="205" rx="4" ry="4"/>
    <ellipse cx="615" cy="241" rx="4" ry="5"/>
    <ellipse cx="512" cy="204" rx="4" ry="4"/>
    <path d="M906 328 L947 334 L942 346 L906 338Z"/>`,
  front: `<path d="M497 310 L550 295 L550 319 L497 333Z"/>
    <path d="M502 357 L552 340 L552 362 L502 380Z"/>
    <path d="M83 505 L124 508 L124 534 L83 530Z"/>
    <path d="M661 573 L677 563 L677 598 L661 610Z"/>
    <path d="M782 532 L808 514 L808 541 L782 559Z"/>
    <ellipse cx="194" cy="575" rx="6" ry="6"/>
    <ellipse cx="867" cy="412" rx="5" ry="5"/>
    <path d="M283 600 L310 593 L310 616 L283 624Z"/>
    <path d="M550 397 L574 384 L574 404 L550 416Z"/>
    <path d="M837 494 L862 490 L861 557 L845 573 L835 553Z" opacity=".32"/>
    <path d="M184 646 L211 650 L223 692 L182 703 L177 673Z" opacity=".28"/>
    <path d="M284 665 L318 659 L329 699 L291 726 L275 701Z" opacity=".26"/>`,
};
const mask = (depth: Depth, blur: number) => `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="869" viewBox="0 0 1536 869"><defs><filter id="b" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="${blur}"/></filter></defs><g fill="white" filter="url(#b)">${shapes[depth]}</g></svg>`)}")`;
const masks = Object.fromEntries(layers.map(d => [d, {core: mask(d, 1), halo: mask(d, 8)}])) as Record<Depth, {core:string;halo:string}>;

export const Scene: React.FC<{baseline?: boolean}> = ({baseline = false}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: '#07121d', overflow: 'hidden', isolation:'isolate'}}>
    {/* A single common plane preserves EXACT registration of image and masks. */}
    <div style={{position:'absolute', width:'100%', aspectRatio:'1536 / 869', top:'50%', transform:'translateY(-50%)'}}>
      <Img src={staticFile('depth-lighting/source.jpg')} style={{display:'block',width:'100%'}}/>
      {!baseline && layers.map(depth => <React.Fragment key={depth}>
        <AbsoluteFill style={{mixBlendMode:'screen',opacity:intensity(frame,depth)*0.9,maskImage:masks[depth].core,WebkitMaskImage:masks[depth].core,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
          <Img src={staticFile('depth-lighting/source.jpg')} style={{width:'100%',filter:'brightness(2.8)'}}/>
        </AbsoluteFill>
        <AbsoluteFill style={{mixBlendMode:'screen',opacity:intensity(frame,depth)*0.55,maskImage:masks[depth].halo,WebkitMaskImage:masks[depth].halo,maskSize:'100% 100%',WebkitMaskSize:'100% 100%'}}>
          <Img src={staticFile('depth-lighting/source.jpg')} style={{width:'100%',filter:'brightness(3.6) blur(4px)'}}/>
        </AbsoluteFill>
      </React.Fragment>)}
    </div>
  </AbsoluteFill>;
};

export const Comparison: React.FC = () => {
  const frame=useCurrentFrame();
  const active=layers.filter(d=>intensity(frame,d)>0.01).join(' + ') || 'baseline';
  return <AbsoluteFill style={{background:'#07121d',color:'white',fontFamily:'Arial'}}>
    <div style={{position:'absolute',top:180,left:0,width:960,height:540}}><Scene baseline/></div>
    <div style={{position:'absolute',top:180,left:960,width:960,height:540}}><Scene/></div>
    <div style={{position:'absolute',top:90,left:60,fontSize:42}}>ORIGINAL</div>
    <div style={{position:'absolute',top:90,left:1020,fontSize:42}}>LIGHTING TEST</div>
    <div style={{position:'absolute',top:780,left:60,fontSize:38}}>{(frame/30).toFixed(1)}s / active: {active}</div>
    <div style={{position:'absolute',top:855,left:60,fontSize:28,color:'#a9bdcf'}}>BACK: station / MIDDLE: trains + signals / FRONT: house lights</div>
  </AbsoluteFill>;
};
