export type Level = 'Easy'|'Medium'|'Hard';
export interface Challenge {id:string; title:string; level:Level; topic:string; ordered:boolean; statement?:string; hints?:string[]}
export interface Table {name:string; columns:{name:string;type:string;nullable:boolean;primary_key:boolean}[]; foreign_keys:{column:string;table:string;target:string}[]; sample_rows:Cell[][]; row_count:number}
export type Cell = string|number|null;
export interface QueryResult {columns:string[];rows:Cell[][];row_count:number;elapsed_ms:number;correct?:boolean;kind?:string;message?:string}
export interface Attempt {id:string;at:string;correct:boolean}
export interface Progress {version:1;attempts:Attempt[]}
export const emptyProgress = ():Progress => ({version:1,attempts:[]});
export const STORAGE_KEY = 'sqlplay-progress-v1';
export function parseProgress(input:unknown):Progress {
  if (!input || typeof input!=='object') throw new Error('This is not a SQLPlay backup.');
  const p=input as Progress;
  if(p.version!==1 || !Array.isArray(p.attempts) || p.attempts.length>50000) throw new Error('Unsupported backup version or too many attempts (maximum 50,000).');
  const attempts=p.attempts.map(a=>{
    if(!a || typeof a.id!=='string' || !/^[a-z0-9-]{1,80}$/.test(a.id) || typeof a.correct!=='boolean' || typeof a.at!=='string' || !/^\d{4}-\d{2}-\d{2}T/.test(a.at) || !Number.isFinite(Date.parse(a.at)) || Date.parse(a.at)>Date.now()+86400000) throw new Error('An attempt in this backup is invalid. Your current progress has not changed.');
    return {id:a.id,at:new Date(a.at).toISOString(),correct:a.correct};
  });
  return {version:1,attempts};
}
export function record(p:Progress,id:string,correct:boolean,at=new Date().toISOString()):Progress {
  return {...p,attempts:[...p.attempts,{id,correct,at}].slice(-50000)};
}
export function solvedIds(p:Progress) {return new Set(p.attempts.filter(a=>a.correct).map(a=>a.id));}
export function dayKey(d:Date) {return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export function streak(p:Progress,now=new Date()) {
  const days=new Set(p.attempts.map(a=>dayKey(new Date(a.at))));
  const cursor=new Date(now.getFullYear(),now.getMonth(),now.getDate(),12);
  if(!days.has(dayKey(cursor))) cursor.setDate(cursor.getDate()-1);
  let n=0;
  while(days.has(dayKey(cursor))) {n++;cursor.setDate(cursor.getDate()-1);}
  return n;
}
export function filterChallenges(all:Challenge[],p:Progress,search:string,level:string,topic:string,status:string) {
  const solved=solvedIds(p), attempted=new Set(p.attempts.map(a=>a.id));
  return all.filter(c=>(!level||c.level===level)&&(!topic||c.topic===topic)&&(`${c.title} ${c.topic}`.toLowerCase().includes(search.toLowerCase()))&&(!status||(status==='Solved'?solved.has(c.id):status==='In progress'?attempted.has(c.id)&&!solved.has(c.id):!attempted.has(c.id))));
}
export const API = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/,'');
export async function api<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T> {
  try {
    const response=await fetch(API+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal:signal??AbortSignal.timeout(20000)});
    let json;
    try {json=await response.json()} catch {throw new Error('The practice server returned an unexpected response. Please try again in a moment.')}
    if(!response.ok) throw new Error(typeof json.detail==='string'?json.detail:'Something went wrong. Please try again.');
    return json;
  } catch(e) {
    if(e instanceof TypeError) throw new Error('We could not reach the practice server. Check your connection and try again. A cold start may take a moment.');
    if(e instanceof Error && e.name==='TimeoutError') throw new Error('The practice server is taking a little longer to wake up. Please try again.');
    throw e;
  }
}
