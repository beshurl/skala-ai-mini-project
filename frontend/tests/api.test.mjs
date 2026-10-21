import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createApiClient, ApiError} from '../src/api.ts';
test('write uses same-origin credentials and CSRF and never retries a failure', async () => {
  let count = 0;
  const api = createApiClient(() => 'local-csrf', async (_path, options) => {
    count++; assert.equal(options.credentials, 'same-origin'); assert.equal(options.headers.get('X-Recase-CSRF'), 'local-csrf');
    return new Response(JSON.stringify({error:'JOB_ALREADY_ACTIVE'}), {status:409,headers:{'X-Request-ID':'test-id'}});
  });
  await assert.rejects(api('/api/test',{method:'POST',body:'{}'}), e => e instanceof ApiError && e.status===409 && e.requestId==='test-id');
  assert.equal(count,1);
});
test('timeout and caller cancellation are distinct, without retry', async () => {
  const hanging = async (_path, options) => new Promise((_, reject) => {
    if(options.signal.aborted) return reject(new DOMException('cancelled','AbortError'));
    options.signal.addEventListener('abort', () => reject(new DOMException('cancelled','AbortError')));
  });
  const api = createApiClient(undefined,hanging);
  await assert.rejects(api('/api/test',{timeoutMs:2}), e=>e.code==='REQUEST_TIMEOUT');
  const ctrl = new AbortController(); ctrl.abort();
  await assert.rejects(api('/api/test',{signal:ctrl.signal}), e=>e.code==='CLIENT_CANCELLED');
});
test('non-JSON/network errors and external URLs fail closed', async () => {
  await assert.rejects(createApiClient(undefined,async()=>new Response('<html/>'))('/api/test'),e=>e.code==='INVALID_RESPONSE');
  await assert.rejects(createApiClient(undefined,async()=>{throw new TypeError('network')})('/api/test'),e=>e.code==='NETWORK_ERROR');
  await assert.rejects(createApiClient()('//external.example'),e=>e.code==='INVALID_API_PATH');
});
