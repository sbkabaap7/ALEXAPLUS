import {describe,it,expect,vi,afterEach} from 'vitest';
import {api,readable} from './api';
import {encodeWav} from '../components/AudioCapture';
afterEach(()=>vi.restoreAllMocks());
describe('API boundary',()=>{
 it('reports server rejection without treating it as success',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:403,json:async()=>({detail:'Independent PIN verification is required.'})}));await expect(api('/guest/clear','POST',{confirmed:true})).rejects.toThrow('Independent PIN');});
 it('uses same-origin cookies and does not add a client role',async()=>{const mock=vi.fn().mockResolvedValue({ok:true,json:async()=>({mode:'GUEST'})});vi.stubGlobal('fetch',mock);expect(await api('/state')).toEqual({mode:'GUEST'});expect(mock.mock.calls[0][1].credentials).toBe('same-origin');expect(mock.mock.calls[0][1].body).toBeUndefined();});
 it('rejects network failure',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline')));await expect(api('/state')).rejects.toThrow('offline');});
});
describe('real capture encoding',()=>{it('writes a mono PCM WAV with actual samples',async()=>{const blob=encodeWav([new Float32Array([0,-1,1,.5])],16000);const buffer=await blob.arrayBuffer();const view=new DataView(buffer);expect(blob.type).toBe('audio/wav');expect(view.getUint32(24,true)).toBe(16000);expect(view.getUint32(40,true)).toBe(8);expect(view.getInt16(46,true)).toBe(-32768);expect(view.getInt16(48,true)).toBe(32767);});});
