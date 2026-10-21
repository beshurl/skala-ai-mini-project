import { shallowRef } from 'vue';
export const location = shallowRef(window.location.pathname);
export const query = shallowRef(window.location.search);
export function safeNext(value: string|null): string {
  return value && /^\/(?:cases(?:\/[A-Za-z0-9_-]+)?|history|settings|admin(?:\/[a-z]+)?)$/.test(value) ? value : '/cases';
}
function syncLocation() {
  location.value = window.location.pathname;
  query.value = window.location.search;
}
window.addEventListener('popstate', syncLocation);
export function navigate(path: string) {
  if (path === window.location.pathname + window.location.search) return;
  window.history.pushState(null, '', path);
  syncLocation();
  window.scrollTo({top: 0, behavior: 'instant'});
}
export function followLink(event: MouseEvent) {
  const a = (event.target as Element)?.closest('a');
  if (!a || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || a.target || a.hasAttribute('download')) return;
  const url = new URL(a.href);
  if (url.origin !== window.location.origin || url.hash || !url.pathname.startsWith('/')) return;
  if (!/^\/(?:login|signup|cases(?:\/[^/]+)?|history|settings|admin(?:\/[^/]+)?)?$/.test(url.pathname)) return;
  event.preventDefault(); navigate(url.pathname + url.search);
}
