import { shallowRef } from 'vue';
import { api, createApiClient, ApiError } from './api';
import { loginPathFor } from './navigation';

export interface Account { user_id: string; email: string; name: string; role: 'user'|'admin'; csrf: string }
export const account = shallowRef<Account|null>(null);
export const authReady = shallowRef(false);
export const authError = shallowRef('');
export const accountApi = createApiClient(() => account.value?.csrf);

export {safeNext} from './navigation';
export function loginPath() { return loginPathFor(window.location.pathname, window.location.search); }
export async function refreshAccount() {
  authError.value = '';
  try { account.value = await api<Account>('/api/auth/session'); }
  catch (e) {
    if (e instanceof ApiError && e.code === 'AUTH_REQUIRED') account.value = null;
    else authError.value = (e as Error).message;
  } finally { authReady.value = true; }
}
export async function logout() {
  await accountApi('/api/auth/logout', {method:'POST'});
  account.value = null;
}
