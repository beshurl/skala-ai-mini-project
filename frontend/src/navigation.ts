import { shallowRef } from 'vue';
export const location = shallowRef(window.location.pathname);
export const query = shallowRef(window.location.search);
export function safeNext(value: string|null): string {
  if(!value)return '/cases';
  if(/^\/(?:cases(?:\/[A-Za-z0-9_-]+)?|history|settings|admin(?:\/[a-z]+)?)$/.test(value))return value;
  // A saved analysis may survive sign-in; arbitrary queries still cannot.
  return /^\/cases\/[A-Za-z0-9_-]+\?job=[A-Za-z0-9_-]+$/.test(value) ? value : '/cases';
}
export function loginPathFor(pathname: string, search = ''): string {
  return '/login?next=' + encodeURIComponent(safeNext(pathname + search));
}
function syncLocation() {
  location.value = window.location.pathname;
  query.value = window.location.search;
}
window.addEventListener('popstate', syncLocation);
export function navigate(path: string) {
  if (path === window.location.pathname + window.location.search) return;
  const previousPath = window.location.pathname;
  window.history.pushState(null, '', path);
  syncLocation();
  if (window.location.pathname !== previousPath) window.scrollTo({top: 0, behavior: 'instant'});
}
export function followLink(event: MouseEvent) {
  const a = (event.target as Element)?.closest('a');
  if (!a || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || a.target || a.hasAttribute('download')) return;
  const url = new URL(a.href);
  if (url.origin !== window.location.origin || url.hash || !url.pathname.startsWith('/')) return;
  if (!/^\/(?:login|signup|cases(?:\/[^/]+)?|history|settings|admin(?:\/[^/]+)?)?$/.test(url.pathname)) return;
  event.preventDefault(); navigate(url.pathname + url.search);
}
