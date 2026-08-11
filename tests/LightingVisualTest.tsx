import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

const buildingWindows = Array.from({length: 30}, (_, index) => ({
  x: 126 + (index % 6) * 92,
  y: 250 + Math.floor(index / 6) * 108,
}));

const towerWindows = Array.from({length: 24}, (_, index) => ({
  x: 930 + (index % 4) * 82,
  y: 188 + Math.floor(index / 4) * 102,
}));

export const LightingVisualTest: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const lightsOn = frame >= fps * 4;
  const windowFill = lightsOn ? '#ffd57d' : '#101724';
  const windowOpacity = lightsOn ? 1 : 0.28;

  return (
    <AbsoluteFill style={{backgroundColor: '#050814'}}>
      <svg
        aria-label="High-resolution synchronized lighting test scene"
        height="1080"
        viewBox="0 0 1920 1080"
        width="1920"
      >
        <defs>
          <linearGradient id="sky" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#050818" />
            <stop offset="1" stopColor="#18263b" />
          </linearGradient>
          <linearGradient id="road" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#171c25" />
            <stop offset="1" stopColor="#080a0e" />
          </linearGradient>
          <radialGradient id="lampGlow">
            <stop offset="0" stopColor="#ffe2a1" stopOpacity="0.96" />
            <stop offset="0.28" stopColor="#ffbd58" stopOpacity="0.52" />
            <stop offset="1" stopColor="#ff9d2e" stopOpacity="0" />
          </radialGradient>
          <filter id="windowGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="12" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        <rect width="1920" height="1080" fill="url(#sky)" />
        <circle cx="1560" cy="142" r="58" fill="#dbe7f4" opacity="0.7" />
        <g fill="#a8bdd8" opacity="0.58">
          <circle cx="200" cy="130" r="3" /><circle cx="470" cy="92" r="4" />
          <circle cx="748" cy="164" r="3" /><circle cx="1360" cy="88" r="3" />
          <circle cx="1780" cy="230" r="4" />
        </g>

        <rect x="70" y="180" width="650" height="670" rx="8" fill="#111827" />
        <rect x="95" y="205" width="600" height="34" fill="#26364a" />
        <rect x="870" y="120" width="430" height="730" rx="8" fill="#0d1524" />
        <rect x="1360" y="300" width="470" height="550" rx="8" fill="#121925" />

        <g fill={windowFill} opacity={windowOpacity} filter={lightsOn ? 'url(#windowGlow)' : undefined}>
          {buildingWindows.map(({x, y}) => <rect key={`a-${x}-${y}`} x={x} y={y} width="52" height="44" rx="3" />)}
          {towerWindows.map(({x, y}) => <rect key={`b-${x}-${y}`} x={x} y={y} width="42" height="46" rx="3" />)}
          {Array.from({length: 18}, (_, index) => (
            <rect key={`c-${index}`} x={1415 + (index % 3) * 120} y={370 + Math.floor(index / 3) * 72} width="62" height="30" rx="3" />
          ))}
        </g>

        <rect x="0" y="850" width="1920" height="230" fill="url(#road)" />
        <path d="M0 940 H1920" stroke="#4c5668" strokeWidth="8" />
        <path d="M120 1010 H460 M680 1010 H1020 M1240 1010 H1580" stroke="#d9b75d" strokeWidth="12" opacity="0.7" />

        {[310, 790, 1310, 1720].map((x) => (
          <g key={x}>
            <rect x={x - 7} y="645" width="14" height="230" fill="#313b49" />
            <path d={`M${x} 658 Q${x + 42} 606 ${x + 86} 642`} fill="none" stroke="#313b49" strokeWidth="14" />
            <circle cx={x + 88} cy="642" r="18" fill={lightsOn ? '#fff0bd' : '#151c27'} />
            {lightsOn && <circle cx={x + 88} cy="642" r="105" fill="url(#lampGlow)" />}
          </g>
        ))}

        <rect x="1460" y="730" width="230" height="74" rx="8" fill={lightsOn ? '#e15d3f' : '#27171b'} />
        <text x="1575" y="780" textAnchor="middle" fontFamily="sans-serif" fontSize="32" letterSpacing="8" fill={lightsOn ? '#fff2cf' : '#493335'}>
          NIGHT
        </text>
      </svg>
    </AbsoluteFill>
  );
};
