import React,{Suspense,lazy,useEffect,useState,useRef} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter,Link,NavLink,Route,Routes,useLocation} from 'react-router-dom';
import {Terminal,Sun,Moon,ArrowUpRight,BookOpen,Code2,ChartNoAxesCombined} from 'lucide-react';
import '@fontsource-variable/inter';
import '@fontsource/jetbrains-mono/400.css';
import './style.css';
import {api,type Challenge} from './model';
import {StoreProvider,useStore} from './store';
import {Home,Library} from './pages';
import {Loading} from './components';
const Workspace=lazy(()=>import('./Workspace'));
const Dashboard=lazy(()=>import('./Dashboard'));
function App(){
 const {dark,toggleTheme,warning}=useStore(),location=useLocation(),initialRoute=useRef(true);
 const [challenges,setChallenges]=useState<Challenge[]|null>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{let live=true;setError('');api<Challenge[]>('/challenges').then(c=>{if(live)setChallenges(c)}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[retry]);
 useEffect(()=>{window.scrollTo(0,0);document.title=location.pathname==='/'?'SQLPlay — Small queries. Big possibilities.':location.pathname==='/challenges'?'Challenge library · SQLPlay':location.pathname==='/progress'?'Your progress · SQLPlay':'SQLPlay';if(initialRoute.current){initialRoute.current=false;return}const main=document.getElementById('main');main?.focus({preventScroll:true});},[location.pathname]);
 useEffect(()=>{function shortcut(e:KeyboardEvent){if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes((e.target as HTMLElement).tagName)&&!(e.target as HTMLElement).isContentEditable){const search=document.querySelector<HTMLInputElement>('[aria-label="Search challenges"]');if(search){e.preventDefault();search.focus()}}}window.addEventListener('keydown',shortcut);return()=>window.removeEventListener('keydown',shortcut)},[]);
 const workspace=location.pathname.startsWith('/challenge/')||location.pathname==='/playground';
 return <><a href="#main" className="skip-link">Skip to content</a><header className="site-header"><div className="header-inner"><Link to="/" className="logo" aria-label="SQLPlay home"><span className="logo-symbol"><Terminal size={22}/></span>SQL<span>Play</span><span className="logo-dot">.</span></Link><nav aria-label="Main navigation"><NavLink to="/challenges"><BookOpen size={16}/> Challenges</NavLink><NavLink to="/playground"><Code2 size={16}/> Playground</NavLink><NavLink to="/progress"><ChartNoAxesCombined size={16}/> My progress</NavLink></nav><div className="header-end"><span className="local-tag">Made for curious minds</span><button className="icon-button theme-toggle" aria-label={dark?'Switch to light theme':'Switch to dark theme'} onClick={toggleTheme}>{dark?<Sun size={19}/>:<Moon size={19}/>}</button></div></div></header><main id="main" tabIndex={-1} className={workspace?'container wide':'container'}>{warning&&<p className="notice error" role="alert">{warning}</p>}<Suspense fallback={<Loading/>}><Routes><Route path="/" element={<Home/>}/><Route path="/challenges" element={<Library challenges={challenges} error={error} retry={()=>setRetry(n=>n+1)}/>}/><Route path="/challenge/:id" element={<Workspace/>}/><Route path="/playground" element={<Workspace playground/>}/><Route path="/progress" element={<Dashboard challenges={challenges} error={error} retry={()=>setRetry(n=>n+1)}/>}/><Route path="*" element={<div className="empty"><h1>A query took a wrong turn.</h1><p>This page doesn’t exist. There’s plenty to explore in the library.</p><Link to="/challenges" className="button primary">Back to challenges</Link></div>}/></Routes></Suspense></main><footer className="site-footer"><div className="container"><Link to="/" className="logo small-logo"><Terminal size={18}/> SQLPlay<span className="logo-dot">.</span></Link><p>A little practice. A lot of possibility.</p><span>Powered by SQLite · Progress stays on your device</span><Link to="/playground">Stay curious <ArrowUpRight size={15}/></Link></div></footer></>
}
class Boundary extends React.Component<{children:React.ReactNode},{failed:boolean}> {state={failed:false};static getDerivedStateFromError(){return {failed:true}}render(){return this.state.failed?<main className="empty"><h1>Something interrupted your session.</h1><p>Your saved progress is still in this browser. Please reload to try again.</p><button className="button" onClick={()=>window.location.reload()}>Reload SQLPlay</button></main>:this.props.children}}
createRoot(document.getElementById('root')!).render(<Boundary><BrowserRouter><StoreProvider><App/></StoreProvider></BrowserRouter></Boundary>);
