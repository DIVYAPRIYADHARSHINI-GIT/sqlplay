import {describe,it,expect} from 'vitest';
import {parseProgress,record,emptyProgress,solvedIds,streak,filterChallenges,dayKey,type Challenge} from './model';
const catalog:Challenge[]=[{id:'a',title:'First select',level:'Easy',topic:'SELECT',ordered:false},{id:'b',title:'Table joins',level:'Medium',topic:'Joins',ordered:false},{id:'c',title:'Window rank',level:'Hard',topic:'Windows',ordered:true}];
describe('progress validation',()=>{
 it('round trips a versioned export',()=>{const p=record(emptyProgress(),'first-select',true);expect(parseProgress(JSON.parse(JSON.stringify(p)))).toEqual(p)});
 for(const [name,input] of Object.entries({null:null,array:[],version:{version:2,attempts:[]},missing:{version:1},badId:{version:1,attempts:[{id:'<script>',at:'2024-01-01T12:00:00Z',correct:true}]},badDate:{version:1,attempts:[{id:'a',at:'nonsense',correct:true}]},dateType:{version:1,attempts:[{id:'a',at:123,correct:true}]},badBool:{version:1,attempts:[{id:'a',at:'2024-01-01T12:00:00Z',correct:1}]},future:{version:1,attempts:[{id:'a',at:'2999-01-01T12:00:00Z',correct:true}]}}))it(`rejects ${name}`,()=>expect(()=>parseProgress(input)).toThrow());
 it('rejects oversized attempt arrays',()=>expect(()=>parseProgress({version:1,attempts:Array(50001).fill({})})).toThrow());
 it('strips unexpected imported fields',()=>expect(parseProgress({version:1,attempts:[],secret:'discard'})).toEqual(emptyProgress()));
 it('normalises timestamps',()=>expect(parseProgress({version:1,attempts:[{id:'a',at:'2024-01-01T12:00:00+05:30',correct:true}]}).attempts[0].at).toBe('2024-01-01T06:30:00.000Z'));
});
describe('progress derivation',()=>{
 it('records without mutating',()=>{const p=emptyProgress(),next=record(p,'a',true);expect(p.attempts).toHaveLength(0);expect(next.attempts).toHaveLength(1)});
 it('wrong attempts are not solves',()=>expect(solvedIds(record(emptyProgress(),'a',false)).size).toBe(0));
 it('a solve stays solved after a wrong answer',()=>expect(solvedIds(record(record(emptyProgress(),'a',true),'a',false)).has('a')).toBe(true));
 it('repeated solves count once',()=>expect(solvedIds(record(record(emptyProgress(),'a',true),'a',true)).size).toBe(1));
 it('caps history',()=>expect(record({version:1,attempts:Array(50000).fill({id:'a',at:'2024-01-01T00:00:00Z',correct:false})},'b',true).attempts).toHaveLength(50000));
 it('has an empty streak',()=>expect(streak(emptyProgress())).toBe(0));
 it('keeps yesterday alive',()=>{const d=new Date(2024,0,2,12),p=record(emptyProgress(),'a',false,new Date(2024,0,1,12).toISOString());expect(streak(p,d)).toBe(1)});
 it('counts consecutive local days including leap day',()=>{let p=emptyProgress();for(const d of [new Date(2024,1,28,12),new Date(2024,1,29,12),new Date(2024,2,1,12)])p=record(p,'a',true,d.toISOString());expect(streak(p,new Date(2024,2,1,14))).toBe(3)});
 it('stops after a missed day',()=>expect(streak(record(emptyProgress(),'a',true,new Date(2024,0,1,12).toISOString()),new Date(2024,0,3,12))).toBe(0));
 it('counts a day only once',()=>{let p=emptyProgress();for(let i=0;i<3;i++)p=record(p,'a',true,new Date(2024,0,1,12).toISOString());expect(streak(p,new Date(2024,0,1,13))).toBe(1)});
 it('formats local day keys',()=>expect(dayKey(new Date(2024,1,29,23))).toBe('2024-02-29'));
});
describe('challenge search and filters',()=>{
 const p=record(record(emptyProgress(),'a',true),'b',false);
 for(const [name,q,l,t,s,ids] of [
 ['all','','','','',['a','b','c']],['search','FIRST','','','',['a']],['level','','Hard','','',['c']],['topic','','','Joins','',['b']],['solved','','','','Solved',['a']],['started','','','','In progress',['b']],['unstarted','','','','Not started',['c']],['intersection','Table','Medium','Joins','In progress',['b']],['empty','not found','','','',[]]
 ] as [string,string,string,string,string,string[]][])it(name,()=>expect(filterChallenges(catalog,p,q,l,t,s).map(c=>c.id)).toEqual(ids));
});
