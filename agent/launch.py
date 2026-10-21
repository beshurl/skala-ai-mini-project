"""Start live servers; preserve data and unrelated processes."""
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def main():
    load_dotenv(ROOT / '.env')
    backend = os.getenv('LLM_BACKEND', 'ollama')
    if backend not in ('ollama', 'openai'):
        raise SystemExit('LLM_BACKEND=ollama 또는 openai를 설정하세요. fake 자동 대체는 하지 않습니다.')
    env = dict(os.environ)
    env.update(LLM_BACKEND=backend, AGENT_PORT=os.getenv('AGENT_PORT', '18100'),
               FRONTEND_PORT=os.getenv('FRONTEND_PORT', '8600'))
    env['AGENT_BACKEND_URL'] = 'http://127.0.0.1:' + env['AGENT_PORT']
    for name in ('AGENT_PORT', 'FRONTEND_PORT'):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try: sock.bind(('127.0.0.1', int(env[name])))
            except OSError:
                raise SystemExit(f'{name}={env[name]} 포트가 사용 중입니다. 기존 서버를 유지합니다. 다른 포트를 지정하세요.')
    children = []
    def stop(*_): raise SystemExit(0)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if backend == 'ollama':
            base = env.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
            try:
                tags = httpx.get(base + '/api/tags', timeout=3)
                tags.raise_for_status()
            except httpx.HTTPError:
                if base != 'http://127.0.0.1:11434' or not shutil.which('ollama'):
                    raise SystemExit('Ollama 연결 실패. OLLAMA_BASE_URL과 ollama serve를 확인하세요.')
                (ROOT/'artifacts').mkdir(exist_ok=True)
                with open(ROOT/'artifacts'/'ollama-server.log', 'a') as log:
                    children.append(subprocess.Popen(['ollama', 'serve'], env=env, stdout=log, stderr=log))
                for _ in range(40):
                    try:
                        tags = httpx.get(base + '/api/tags', timeout=2)
                        tags.raise_for_status()
                        break
                    except httpx.HTTPError: time.sleep(.5)
                else: raise SystemExit('Ollama 시작 실패. artifacts/ollama-server.log를 확인하세요.')
            installed = {m['name'] for m in tags.json()['models']}
            models = {env.get('OLLAMA_FAST_MODEL', 'qwen3.5:2b'), env.get('OLLAMA_QUALITY_MODEL', 'qwen3.5:2b')}
            if env.get('JUDGE_BACKEND', backend) == 'ollama': models.add(env.get('JUDGE_MODEL', 'qwen3:8b'))
            missing = sorted(models - installed)
            if missing: raise SystemExit('미설치 모델: ' + ', '.join(missing) + '. ollama pull <모델명> 후 다시 시작하세요.')
        elif not env.get('OPENAI_API_KEY') or env['OPENAI_API_KEY'].endswith('...'):
            raise SystemExit('OPENAI_API_KEY가 필요합니다. .env에 설정하세요.')
        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server:app', '--host', '127.0.0.1',
                                '--port', env['AGENT_PORT']], cwd=ROOT, env=env)
        children.append(api)
        for _ in range(60):
            if api.poll() is not None: raise SystemExit('API 시작 실패. 위 오류를 확인하세요.')
            try:
                health = httpx.get(env['AGENT_BACKEND_URL'] + '/health', timeout=2)
                health.raise_for_status()
                break
            except httpx.HTTPError: time.sleep(.5)
        else: raise SystemExit('API 준비 시간 초과')
        frontend = subprocess.Popen([sys.executable, 'web_demo_server.py'], cwd=ROOT, env=env)
        children.append(frontend)
        state = health.json()
        print(f"실제 생성 모델: {state['quality_llm']} · LangSmith 설정: {state['tracing_configured']}", flush=True)
        print(f"화면 http://127.0.0.1:{env['FRONTEND_PORT']} · API {env['AGENT_BACKEND_URL']}", flush=True)
        while api.poll() is None and frontend.poll() is None: time.sleep(.5)
        raise SystemExit('서버가 종료되었습니다.')
    finally:
        for child in reversed(children):
            if child.poll() is None: child.terminate()
        for child in reversed(children):
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill()


if __name__ == '__main__': main()
