import {afterEach,describe,expect,it,vi} from 'vitest';
import {streamRequest} from './stream';

afterEach(()=>vi.unstubAllGlobals());
function response(parts:string[]){return new Response(new ReadableStream({start(controller){for(const part of parts)controller.enqueue(new TextEncoder().encode(part));controller.close();}}));}
describe('reply transport',()=>{
 it('reads split NDJSON frames without duplicating text',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(['{"type":"del','ta","text":"Hello"}\n{"type":"delta","text":" there"}\n','{"type":"result","result":{"response":"Hello there","error":false}}\n'])));
  let text='';const result=await streamRequest('hello',part=>text+=part);expect(text).toBe('Hello there');expect(result.response).toBe(text);
 });
 it('does not accept a truncated response as completed',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(['{"type":"delta","text":"Incomplete"}\n'])));
  await expect(streamRequest('hello',()=>{})).rejects.toThrow('interrupted');
 });
});
