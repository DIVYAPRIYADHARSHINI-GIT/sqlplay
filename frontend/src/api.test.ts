import {afterEach,expect,it,vi} from 'vitest';
import {api} from './model';
afterEach(()=>vi.unstubAllGlobals());
it('returns JSON results',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({rows:[[1]]}),{status:200})));expect(await api('/run',{query:'SELECT 1'})).toEqual({rows:[[1]]})});
it('explains non-JSON server errors without dumping HTML',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>Internal server error</html>',{status:500})));await expect(api('/run',{query:'SELECT 1'})).rejects.toThrow('unexpected response')});
it('preserves friendly API validation errors',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Use one SELECT query.'}),{status:400})));await expect(api('/run',{query:'bad'})).rejects.toThrow('Use one SELECT query.')});
it('explains network errors',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));await expect(api('/schema')).rejects.toThrow('could not reach')});
it('explains timeouts',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new DOMException('Timed out','TimeoutError')));await expect(api('/schema')).rejects.toThrow('wake up')});
