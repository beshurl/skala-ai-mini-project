export const errors: Record<string, string> = {
  GENERAL_OUTPUT_INVALID:'다중 증거 분석의 원문 인용 또는 출력 검증에 실패했습니다. 원문과 실행 정보를 확인하세요.',
  GENERAL_CONTEXT_LIMIT:'모델 입력 한도를 넘었습니다. 사건을 나누어 작성하거나 검토할 원문 범위를 줄이세요.',
  GENERAL_INPUT_BUDGET:'주장·자료 처리 범위를 넘었습니다. 최대 8개 주장, 24개 자료, 원문 합계 24,000자까지 지원합니다.',
  GENERAL_MODEL_FAILED:'모델 실행에 실패해 뒤의 호출을 중단했습니다. 실행 상태를 확인하세요.',
  REQUEST_TOO_LARGE:'요청 크기 한도를 넘었습니다. 원문 범위를 줄이거나 사건을 나누어 작성하세요.',
  CREATION_REQUEST_CONFLICT:'같은 저장 요청의 내용이 달라졌습니다. 먼저 사건 목록에서 이전 저장 결과를 확인하세요.',
  EVIDENCE_VERSION_CHANGED: '증거 버전이 바뀌었습니다. 사건 내용을 새로고침한 뒤 다시 시도하세요.',
  MODEL_NOT_READY: '모델이 준비되지 않았습니다. 실행 상태를 확인하세요.',
  ANALYSIS_QUEUE_FULL: '대기열이 가득 찼습니다. 진행 중인 작업이 끝난 뒤 다시 요청하세요.',
  JOB_ALREADY_ACTIVE: '이 사건의 분석이 진행 중입니다. 상태를 새로고침하세요.',
  CASE_CLOSED: '종료된 사건입니다. 사건 관리에서 검토를 재개한 뒤 진행하세요.',
  CASE_HAS_ACTIVE_JOB: '진행 중인 분석이 있어 사건을 종료할 수 없습니다. 분석 상태를 확인하세요.',
  LIFECYCLE_REVISION_CHANGED: '사건의 종료·보류 상태가 바뀌었습니다. 현재 상태를 확인한 뒤 다시 선택하세요.',
  CLOCK_BEFORE_CASE_CREATION: '서버 시각을 확인해야 합니다. 사건 생성일보다 앞선 날짜로 종료할 수 없습니다.',
  INVALID_RESPONSE: '서버 응답을 확인할 수 없습니다. 상태를 다시 확인하세요.',
  SERVER_RESTARTED: '서버가 다시 시작되어 작업이 종료되었습니다. 새 분석을 요청하세요.',
  ANALYSIS_TIMEOUT: '분석 시간 제한을 초과했습니다. 상태 확인 후 새 분석을 요청하세요.',
  MCP_TOOL_FAILED: '증거 도구 연결에 실패했습니다. 서버 상태를 확인하세요.',
  ANALYSIS_FAILED: '분석을 완료하지 못했습니다. 상태를 확인한 뒤 다시 요청하세요.',
  CSRF_REQUIRED: '세션이 변경되었습니다. 페이지를 새로고침하세요.',
  AUTH_REQUIRED: '로그인이 필요합니다. 다시 로그인해주세요.',
  LOGIN_FAILED: '이메일 또는 비밀번호가 일치하지 않습니다.',
  INVALID_EMAIL: '이메일 주소를 확인해주세요.',
  PASSWORD_LENGTH: '비밀번호는 12자 이상 128자 이하로 입력해주세요.',
  EMAIL_IN_USE: '이미 가입된 이메일입니다. 로그인해주세요.',
  AUTH_INPUT_INVALID: '입력한 내용을 확인해주세요.',
  ACCOUNT_STORE_UNAVAILABLE: '계정 정보를 확인하지 못했습니다. 서버 상태를 확인한 뒤 다시 시도해주세요.',
  ADMIN_REQUIRED: '운영자 권한이 필요한 페이지입니다.',
  LOGIN_RATE_LIMITED: '로그인 시도가 많습니다. 1분 뒤 다시 시도하세요.',
  NOT_FOUND: '접근 가능한 자료를 찾지 못했습니다.', MODEL_OUTPUT_INVALID: '모델 출력의 형식 또는 근거 검증에 실패했습니다.',
  CANCELLED: '분석이 취소되었습니다.', RETRIEVAL_INSUFFICIENT: '관련 공개 증거가 부족합니다.',
  CHRONOLOGICAL_RESULTS_REQUIRED: '현재 분석보다 이전에 실행한 결과를 선택하세요.',
  COMPARABLE_RESULTS_REQUIRED: '같은 사건에서 결과가 저장된 분석을 선택하세요.',
  CLIENT_CANCELLED: '요청을 취소했습니다.', REQUEST_TIMEOUT: '응답 시간이 초과되었습니다. 쓰기 요청은 처리됐을 수 있으므로 상태부터 확인하세요.',
  NETWORK_ERROR: '서버에 연결할 수 없습니다. 연결 상태를 확인하세요.',
};
export class ApiError extends Error {
  code: string; status: number; requestId: string|null;
  constructor(code: string, status = 0, requestId: string|null = null) {
    super(errors[code] || `요청을 처리하지 못했습니다 (${status}). 상태를 확인한 뒤 다시 시도하세요.`);
    this.name = 'ApiError'; this.code = code; this.status = status; this.requestId = requestId;
  }
}
type Options = Omit<RequestInit, 'body'> & { body?: string; timeoutMs?: number };
export function createApiClient(csrf: () => string|undefined = () => undefined, transport: typeof fetch = fetch) {
  // No automatic retries: especially never repeat POST/LLM calls after an uncertain response.
  return async function api<T = any>(path: string, options: Options = {}): Promise<T> {
    if (!path.startsWith('/') || path.startsWith('//')) throw new ApiError('INVALID_API_PATH');
    const {timeoutMs = 15000, signal, ...init} = options;
    const controller = new AbortController();
    let expired = false;
    const abort = () => controller.abort();
    if (signal?.aborted) abort();
    signal?.addEventListener('abort', abort, {once: true});
    const timer = setTimeout(() => { expired = true; abort(); }, timeoutMs);
    try {
      const headers = new Headers(init.headers);
      if (init.body) headers.set('Content-Type', 'application/json');
      const token = csrf();
      if (token && !['GET','HEAD'].includes((init.method || 'GET').toUpperCase())) headers.set('X-Recase-CSRF', token);
      const response = await transport(path, {...init, headers, credentials: 'same-origin', signal: controller.signal});
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const code = typeof data?.detail === 'string' ? data.detail : data?.error || 'HTTP_ERROR';
        if (code === 'AUTH_REQUIRED' && path !== '/api/auth/session' && typeof window !== 'undefined') window.dispatchEvent(new Event('recase-auth-required'));
        throw new ApiError(code, response.status, response.headers.get('X-Request-ID'));
      }
      if (data === null) throw new ApiError('INVALID_RESPONSE', response.status);
      return data as T;
    } catch (error) {
      if (controller.signal.aborted) throw new ApiError(expired ? 'REQUEST_TIMEOUT' : 'CLIENT_CANCELLED');
      if (error instanceof TypeError) throw new ApiError('NETWORK_ERROR');
      throw error;
    } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
  };
}
export const api = createApiClient();
