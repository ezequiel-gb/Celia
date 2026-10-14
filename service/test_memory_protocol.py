"""Two real MCP sessions with disposable roots and a separate copied server."""
import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
from mcp import Client
from mcp.client.stdio import StdioServerParameters


def unpack(result):
    assert not result.is_error, result
    for item in result.content:
        if getattr(item, 'type', None) == 'text':
            return json.loads(item.text)
    raise AssertionError('No JSON result')


async def run():
    with tempfile.TemporaryDirectory(prefix='celious-memory-mcp-') as temporary:
        base = Path(temporary)
        service = base / 'service'
        service.mkdir()
        for name in ['engine.py', 'server.py', 'second_brain.py', 'memory_tools.py']:
            shutil.copy2(Path(__file__).parent / name, service / name)
        for name in ['vault', 'projects']:
            (base/name).mkdir()
        (base/'vault/INDEX.md').write_text('# Disposable vault', 'utf-8')
        config = dict(direct_operations=True, roots={name.title(): dict(path=str(base/name), writable=True) for name in ['vault','projects']},
                      second_brain=dict(root='Projects', path='Celious/Second Brain'))
        (service/'config.json').write_text(json.dumps(config), 'utf-8')
        transport = StdioServerParameters(command=sys.executable, args=[str(service/'server.py')])
        async with Client(transport) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert len(names) == 19, names
            assert {'memory_search','memory_archive_preview','memory_commit','memory_inspect','memory_supersede_preview'} <= names
            args = dict(title='Actually supplied transcript', text='User: Prefer portable Markdown memory.',
                        source_ref='disposable MCP session A', completeness='excerpt', claims_json=json.dumps([
                            dict(type='preference', title='Portable memory', topic='Celious', key='format', value='portable Markdown',
                                 evidence='Prefer portable Markdown memory.', epistemic='asserted', uncertainty='Supplied excerpt only')]))
            preview = unpack(await client.call_tool('memory_archive_preview', args))
            assert not preview['saved_to_memory']
            denied = await client.call_tool('memory_commit', dict(plan_id=preview['plan_id'], approved_sha256='wrong'))
            assert denied.is_error
            result = unpack(await client.call_tool('memory_commit', dict(plan_id=preview['plan_id'], approved_sha256=preview['plan_sha256'])))
            assert result['status'] == 'committed'
        # Fresh process, independent client state; retrieve only persisted Markdown.
        async with Client(transport) as client:
            hit = unpack(await client.call_tool('memory_search', dict(query='portable Markdown')))['hits'][0]
            assert hit['sources'][0]['completeness'] == 'excerpt'
            assert hit['evidence'][0]['quote'] == 'Prefer portable Markdown memory.'
            assert unpack(await client.call_tool('memory_inspect', {}))['issues'] == []
            assert not (await client.call_tool('list_roots', {})).is_error
            assert not (await client.call_tool('read_document', dict(root='Vault', path='INDEX.md'))).is_error
            denied = await client.call_tool('read_document', dict(root='Projects', path='../outside'))
            assert denied.is_error
        print('19 MCP tools, exact proposal approval, persisted retrieval in a second MCP session, provenance, integrity, original reads and traversal denial passed.')


if __name__ == '__main__':
    asyncio.run(run())
