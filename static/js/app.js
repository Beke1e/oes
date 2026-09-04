const root = document.documentElement;
const savedTheme = localStorage.getItem('soems-theme');
if (savedTheme) root.dataset.theme = savedTheme;
const savedSidebar = localStorage.getItem('soems-sidebar');
if (savedSidebar === 'collapsed') document.body.classList.add('sidebar-collapsed');
document.getElementById('themeToggle')?.addEventListener('click', () => {
  const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  root.dataset.theme = theme; localStorage.setItem('soems-theme', theme);
});
document.getElementById('menuToggle')?.addEventListener('click', () => document.getElementById('sidebar')?.classList.toggle('open'));
document.getElementById('sidebarToggle')?.addEventListener('click', () => {
  const collapsed = document.body.classList.toggle('sidebar-collapsed');
  localStorage.setItem('soems-sidebar', collapsed ? 'collapsed' : 'expanded');
  const control = document.getElementById('sidebarToggle');
  if (control) { control.title = collapsed ? 'Expand sidebar' : 'Collapse sidebar'; control.setAttribute('aria-label', control.title); control.querySelector('i').className = collapsed ? 'fa-solid fa-angles-right' : 'fa-solid fa-angles-left'; }
});
document.getElementById('passwordToggle')?.addEventListener('click', (event) => {
  const button = event.currentTarget;
  const password = document.getElementById('password');
  const showing = password.type === 'text';
  password.type = showing ? 'password' : 'text';
  button.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
  button.title = showing ? 'Show password' : 'Hide password';
  button.querySelector('i').className = showing ? 'fa-regular fa-eye' : 'fa-regular fa-eye-slash';
});
document.getElementById('profile_photo')?.addEventListener('change', (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const preview = document.getElementById('profilePreview');
  const fallback = document.getElementById('profileFallback');
  if (preview) { preview.src = URL.createObjectURL(file); preview.classList.remove('d-none'); }
  fallback?.classList.add('d-none');
});
document.querySelectorAll('[data-countdown]').forEach((timer) => {
  let seconds = Number(timer.dataset.countdown) * 60;
  const form = timer.closest('form');
  const tick = () => { const minutes = Math.floor(seconds / 60); timer.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`; if (seconds <= 0) { form?.submit(); return; } seconds -= 1; };
  tick(); setInterval(tick, 1000);
});
