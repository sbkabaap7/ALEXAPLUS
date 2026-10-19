"""Local-only general answers. MCP data and authorization never enter this context."""
import json
from urllib.parse import urlparse

import httpx

from .config import settings

LOCAL_MODE = 'Local Ollama — general answer'


def _base_url() -> str:
    parsed = urlparse(settings.ollama_base_url)
    if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Ollama must use a local HTTP address')
    return settings.ollama_base_url.rstrip('/')


def model_ready() -> bool:
    """Use the installed model list for an honest status indicator."""
    try:
        response = httpx.get(_base_url() + '/api/tags', timeout=1)
        response.raise_for_status()
        return any(model.get('name') == settings.ollama_model for model in response.json().get('models', []))
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return False


def _request(question: str, stream: bool) -> dict:
    return {
            'model': settings.ollama_model,
            'stream': stream,
            'think': False,
            'messages': [
                {'role': 'system', 'content': (
                    'You are GuestGuard. Answer the user clearly and conversationally. '
                    'You have no access to their calendar, notes, devices, live data, or MCP tools in this conversation. '
                    'Do not claim you performed an action or saw private information. '
                    'If asked about those, suggest asking GuestGuard to check the relevant item directly. '
                    'Lead with the answer. Do not praise the question or use filler such as "Great question". '
                    'For simple questions, use two or three plain sentences and under 70 words. '
                    'Give more detail only when the user asks for it.')},
                {'role': 'user', 'content': question},
            ],
        }


async def answer(question: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=3)) as client:
        response = await client.post(_base_url() + '/api/chat', json=_request(question, False))
        response.raise_for_status()
        content = response.json().get('message', {}).get('content', '').strip()
        if not content:
            raise ValueError('Ollama returned an empty answer')
        return content


async def stream_answer(question: str):
    """Yield real model chunks from Ollama's newline-delimited chat response."""
    produced = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=3)) as client:
        async with client.stream('POST', _base_url() + '/api/chat', json=_request(question, True)) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                item = json.loads(line)
                if item.get('error'):
                    raise ValueError('Ollama failed to generate an answer')
                content = item.get('message', {}).get('content', '')
                if content:
                    produced = True
                    yield content
    if not produced:
        raise ValueError('Ollama returned an empty answer')
