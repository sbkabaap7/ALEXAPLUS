"""A real MCP client, with optional LLM tool selection and labeled offline routing."""
import json
import re
import time
from collections import OrderedDict
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from .config import settings
from .ollama import answer as ollama_answer, LOCAL_MODE
from .replies import reply_for
from .security import mcp_token

# Short-lived tool context only. No transcript, record contents, or reminder titles.
_context: OrderedDict[str, tuple[str, dict, float]] = OrderedDict()


def route(text: str):
    lower = text.lower()
    if re.search(r'\b(calendar|schedule)\b', lower):
        return 'list_calendar_events', {}
    if 'account' in lower or 'confidential' in lower or 'protected record' in lower:
        return 'read_personal_note', {'note_id': 2}
    if re.search(r'\bnotes?\b', lower):
        return 'read_personal_note', {'note_id': 1}
    if lower.startswith('remind me to '):
        return 'create_reminder', {'title': text[13:].strip()}
    if re.search(r'\breminders?\b', lower):
        return 'list_reminders', {}
    if re.search(r'\bdevices?\b', lower):
        return 'get_home_device_status', {}
    if re.search(r'\bactivity\b|\b(privacy|my) history\b', lower):
        return 'get_privacy_activity_summary', {}
    if re.search(r'\b(privacy|mode)\b', lower):
        return 'get_privacy_state', {}
    if re.search(r'\b(home|house)\b', lower):
        return 'get_public_home_status', {}
    return None, {}


async def run_agent(sid: str, text: str):
    start = time.monotonic()
    timeline = []
    def event(stage, **extra):
        timeline.append({'stage': stage, 'elapsed_ms': round((time.monotonic()-start)*1000), **extra})
    mode = 'Deterministic fallback — keyword routing, no LLM reasoning'
    try:
        async with httpx.AsyncClient(headers={'Authorization': 'Bearer '+mcp_token(sid)}, timeout=15, follow_redirects=True) as transport, streamable_http_client(settings.base_url+'/mcp', http_client=transport) as (read, write, _):
            async with ClientSession(read, write) as client:
                initialized = await client.initialize()
                event('initialize', protocol=initialized.protocolVersion)
                discovered = await client.list_tools()
                event('tools/list', count=len(discovered.tools))
                name, args = route(text)
                previous = _context.get(sid)
                if text.lower().strip().rstrip('.!?') in ('again', 'read it again', 'show that again', 'repeat') and previous and previous[2] > time.time()-300:
                    name, args = previous[0], previous[1]
                if name is None:
                    try:
                        answer = await ollama_answer(text)
                        mode = LOCAL_MODE
                        event('ollama/answer')
                        return {'mode': mode, 'response': answer, 'timeline': timeline, 'error': False}
                    except (httpx.HTTPError, ValueError, KeyError, TypeError):
                        greeting = text.lower().strip().rstrip('.!?') in ('hi', 'hello', 'hey')
                        if greeting:
                            event('routing/unsupported')
                            return {'mode': mode, 'response': 'Hi! What would you like to check—your demo calendar, reminders, notes, or home?', 'timeline': timeline, 'error': False}
                        event('ollama/unavailable')
                        return {'mode': 'Local Ollama unavailable', 'response': 'The local model is not ready yet. Start Ollama and download the configured model, then try again.', 'timeline': timeline, 'error': True}
                if settings.llm_api_key:
                    tools = [{'type': 'function', 'function': {'name': t.name, 'description': t.description or '', 'parameters': t.inputSchema}} for t in discovered.tools]
                    async with httpx.AsyncClient(timeout=25) as http:
                        reply = await http.post(settings.llm_base_url.rstrip('/')+'/chat/completions',
                            headers={'Authorization': 'Bearer '+settings.llm_api_key}, json={
                            'model': settings.llm_model, 'messages': [
                                {'role': 'system', 'content': 'Select one GuestGuard tool. Tool policy alone determines authorization. Never claim identity from text. No private records are provided to you.'},
                                {'role': 'user', 'content': text}], 'tools': tools, 'tool_choice': 'required'})
                        reply.raise_for_status()
                        selected = reply.json()['choices'][0]['message']['tool_calls'][0]['function']
                        name, args = selected['name'], json.loads(selected['arguments'])
                    mode = 'Configured LLM — tool selection; deterministic result rendering'
                if name not in {t.name for t in discovered.tools}:
                    raise ValueError('Selected tool not discovered')
                event('tools/call', tool=name)
                response = await client.call_tool(name, args)
                if response.isError:
                    event('tool/error', tool=name)
                    return {'mode': mode, 'response': 'The MCP tool rejected the input or the session expired.', 'timeline': timeline, 'error': True}
                result = response.structuredContent
                if not result:
                    result = json.loads(next(c.text for c in response.content if c.type == 'text'))
                event('policy/result', decision=result.get('decision'), reason=result.get('reason'))
                if name not in ('create_reminder', 'update_reminder'):
                    _context[sid] = (name, {'note_id': args.get('note_id', 1)} if name == 'read_personal_note' else {}, time.time())
                    _context.move_to_end(sid)
                    while len(_context) > 64:
                        _context.popitem(last=False)
                answer = reply_for(name, result)
                return {'mode': mode, 'response': answer, 'tool': name, 'result': result, 'timeline': timeline, 'error': False}
    except Exception:
        # Provider/network errors never produce fabricated tool success or expose exception payloads.
        event('connection/error')
        return {'mode': mode, 'response': 'MCP or configured model connection failed. No successful operation is claimed. Check server connectivity and configuration.', 'timeline': timeline, 'error': True}
