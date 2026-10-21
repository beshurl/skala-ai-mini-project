import type { Citation } from './types';

/** Backend offsets count Unicode code points, not JavaScript UTF-16 units. */
export function quoteParts(text:string, citation:Citation) {
  const points=Array.from(text), {start,end,quote}=citation;
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>points.length)return null;
  if(points.slice(start,end).join('')!==quote)return null;
  return {before:points.slice(0,start).join(''),quote,after:points.slice(end).join('')};
}
