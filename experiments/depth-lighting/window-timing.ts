import {type Depth} from './timing';

type Group = {id: string; depth: Depth; sourceMask: string};
export function splitWindows(groups: Group[]) {
  return groups.flatMap((group, groupIndex) => {
    const shapes = group.sourceMask.match(/<path\s[^>]+\/>/g) ?? [];
    const spacing = [60, 99, 129][groupIndex];
    const offset = [18, 47, 76][groupIndex];
    return shapes.map((sourceMask, index) => {
      // Coprime permutations visit each window once without a visual scan order.
      const slot = (index * [5, 3, 5][groupIndex]) % shapes.length;
      const start = offset + slot * spacing + [0, 7, -4, 3][slot % 4];
      const end = start + [36, 42, 39][slot % 3];
      return {id: `${group.id}-${index}`, group: group.id, depth:group.depth,
        sourceMask, reflectionMask:'', reflectionGain:0,
        pulseWindow: [start, end] as [number, number]};
    });
  });
}
export function windowIntensity(frame: number, [start,end]: readonly [number,number], fade=9) {
  const f=((frame%900)+900)%900;
  const smooth=(n:number)=>{const x=Math.max(0,Math.min(1,n));return x*x*(3-2*x);};
  return smooth((f-start)/fade)*smooth((end-f)/fade);
}
