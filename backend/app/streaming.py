"""Stream authorized results without inventing model tokens or delaying text."""
import asyncio
import json
from .agent import run_agent, route
from .ollama import stream_answer, LOCAL_MODE
import httpx
from .security import db
from .privacy import evaluate
from .tools import TOOL_META


def packet(kind, **data):
    return json.dumps({'type': kind, **data}) + '\n'


def current_result(token, output):
    """Recheck at delivery: tool execution may have raced a room/session change."""
    try:
        session = db.session(token)
        sensitivity, operation = TOOL_META.get(output.get('tool'), ('SENSITIVE', 'read'))
        check = evaluate(session, sensitivity, operation)
        if output.get('result', {}).get('decision') == 'ALLOW' and check.decision != 'ALLOW':
            return {**output, 'response': 'Access changed while this request was running. Please verify again.',
                    'result': {'decision': str(check.decision), 'reason': check.reason, 'status': 'denied'}}
        return output
    except PermissionError:
        return {'mode': output.get('mode', ''), 'response': 'Your session ended. Send a new request to start again.',
                'timeline': [], 'error': True}


async def stream_agent(token, text):
    yield packet('status', message='Working…')
    repeat = text.lower().strip().rstrip('.!?') in ('again', 'read it again', 'show that again', 'repeat')
    if route(text)[0] is None and not repeat:
        parts = []
        try:
            async for chunk in stream_answer(text):
                parts.append(chunk)
                yield packet('delta', text=chunk)
            output = {'mode': LOCAL_MODE, 'response': ''.join(parts), 'timeline': [{'stage': 'ollama/stream'}], 'error': False}
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            greeting = text.lower().strip().rstrip('.!?') in ('hi', 'hello', 'hey')
            output = ({'mode': 'Deterministic fallback — greeting', 'response': 'Hi! What would you like to check—your demo calendar, reminders, notes, or home?', 'timeline': [{'stage': 'routing/unsupported'}], 'error': False}
                      if greeting and not parts else
                      {'mode': 'Local Ollama unavailable', 'response': 'The local model is not ready yet. Start Ollama and download the configured model, then try again.', 'timeline': [{'stage': 'ollama/unavailable'}], 'error': True})
            yield packet('delta', text=output['response'])
        yield packet('result', result=current_result(token, output))
        return
    output = await run_agent(token, text)
    output = current_result(token, output)
    # The fallback renders completed tool results. These are transport chunks,
    # not claims of live LLM generation; no artificial typing delays are added.
    sensitivity = TOOL_META.get(output.get('tool'), ('SENSITIVE', 'read'))[0]
    # Private answers are delivered only in the final policy-rechecked result.
    if output.get('result', {}).get('decision') != 'ALLOW' or sensitivity == 'PUBLIC':
        for offset in range(0, len(output['response']), 32):
            yield packet('delta', text=output['response'][offset:offset+32])
            await asyncio.sleep(0)
    yield packet('result', result=current_result(token, output))
