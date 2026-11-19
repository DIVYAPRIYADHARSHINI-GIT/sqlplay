import {createContext,useContext,useState,type ReactNode} from 'react';
import {emptyProgress,parseProgress,record,STORAGE_KEY,type Progress} from './model';
interface Store {progress:Progress;attempt:(id:string,correct:boolean)=>void;replace:(p:Progress)=>void;warning:string;dark:boolean;toggleTheme:()=>void}
const Context=createContext<Store>(null!);
export const useStore=()=>useContext(Context);
export function StoreProvider({children}:{children:ReactNode}) {
  const [initial]=useState(()=>{try{const raw=localStorage.getItem(STORAGE_KEY);return {progress:raw?parseProgress(JSON.parse(raw)):emptyProgress(),warning:''}}catch{return {progress:emptyProgress(),warning:'We could not read saved progress. Your old data has not been overwritten. Export or restore a valid backup before continuing; new attempts will replace unreadable data.'}}});
  const [progress,setProgress]=useState(initial.progress),[warning,setWarning]=useState(initial.warning),[dark,setDark]=useState(document.documentElement.dataset.theme==='dark');
  function save(next:Progress) {setProgress(next);try{localStorage.setItem(STORAGE_KEY,JSON.stringify(next));setWarning('')}catch{setWarning('Progress is available for this session, but your browser could not save it. Export a backup before leaving.')}}
  function attempt(id:string,correct:boolean) {setProgress(current=>{const next=record(current,id,correct);try{localStorage.setItem(STORAGE_KEY,JSON.stringify(next))}catch{setWarning('Your browser could not save progress. Export a backup before leaving.')}return next})}
  function toggleTheme(){const next=!dark;setDark(next);document.documentElement.dataset.theme=next?'dark':'light';try{localStorage.setItem('sqlplay-theme',next?'dark':'light')}catch{setWarning('Theme preference could not be saved in this browser.')}}
  return <Context.Provider value={{progress,attempt,replace:save,warning,dark,toggleTheme}}>{children}</Context.Provider>
}
