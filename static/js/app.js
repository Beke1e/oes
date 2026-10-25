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

const examForm = document.getElementById('examForm');
const examTimer = document.getElementById('examTimer');
if (examForm && examTimer) {
  const timerKey = `soems-exam-deadline-${examTimer.dataset.examId}`;
  const duration = Math.max(1, Number(examTimer.dataset.duration));
  const storedDeadline = Number(sessionStorage.getItem(timerKey));
  const deadline = storedDeadline > 0 ? storedDeadline : Date.now() + duration * 1000;
  sessionStorage.setItem(timerKey, String(deadline));
  const clockProgress = document.getElementById('clockProgress');
  const clockRing = document.getElementById('clockRing');
  const timerTick = () => {
    const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    const hours = Math.floor(remaining / 3600);
    const minutes = Math.floor((remaining % 3600) / 60);
    const seconds = remaining % 60;
    examTimer.textContent = [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':');
    clockProgress?.style.setProperty('stroke-dashoffset', String(283 * (1 - remaining / duration)));
    clockRing?.classList.toggle('is-low-time', remaining <= 300);
    if (remaining === 0) {
      examForm.dataset.autoSubmit = 'true';
      examForm.requestSubmit();
      return;
    }
    window.setTimeout(timerTick, 1000);
  };

  const questionCards = [...examForm.querySelectorAll('[data-question-index]')];
  const paletteButtons = [...examForm.querySelectorAll('[data-go-to]')];
  const answeredCount = document.getElementById('answeredCount');
  const remainingCount = document.getElementById('remainingCount');
  const questionPosition = document.getElementById('questionPosition');
  const progressBar = document.getElementById('questionProgress');
  const progressPercent = document.getElementById('progressPercent');
  const progressFill = progressBar?.querySelector('span');
  const previousButton = document.getElementById('previousQuestion');
  const nextButton = document.getElementById('nextQuestion');
  const submitButton = document.getElementById('submitExam');
  const submitHint = document.getElementById('submitHint');
  const submitConfirmation = document.getElementById('submitConfirmation');
  const confirmSubmit = document.getElementById('confirmSubmit');
  const cancelSubmit = document.getElementById('cancelSubmit');
  let currentIndex = 0;
  let submissionConfirmed = false;

  const updateAnswerState = () => {
    let answered = 0;
    questionCards.forEach((card, index) => {
      const hasAnswer = Boolean(card.querySelector('input[type="radio"]:checked'));
      if (hasAnswer) answered += 1;
      paletteButtons[index]?.classList.toggle('is-answered', hasAnswer);
    });
    if (answeredCount) answeredCount.textContent = String(answered);
    if (remainingCount) remainingCount.textContent = String(questionCards.length - answered);
    const completion = questionCards.length ? Math.round((answered / questionCards.length) * 100) : 0;
    if (progressPercent) progressPercent.textContent = `${completion}% complete`;
    if (progressFill && questionCards.length) progressFill.style.width = `${((currentIndex + 1) / questionCards.length) * 100}%`;
    if (progressBar) progressBar.setAttribute('aria-valuenow', String(currentIndex + 1));
    if (submitButton) submitButton.disabled = !questionCards.length || answered !== questionCards.length;
    if (submitHint) {
      submitHint.textContent = answered === questionCards.length
        ? 'All questions answered. Ready to submit.'
        : examForm.dataset.autoSubmit === 'true'
          ? 'Time is up. Answer every question before submitting.'
          : 'Answer all questions to enable submission.';
    }
  };

  const showQuestion = (index) => {
    if (index < 0 || index >= questionCards.length) return;
    currentIndex = index;
    questionCards.forEach((card, cardIndex) => {
      card.classList.toggle('d-none', cardIndex !== index);
    });
    paletteButtons.forEach((button, buttonIndex) => {
      button.classList.toggle('is-current', buttonIndex === index);
      if (buttonIndex === index) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    if (questionPosition) questionPosition.textContent = `Question ${index + 1} of ${questionCards.length}`;
    if (previousButton) previousButton.disabled = index === 0;
    if (nextButton) {
      nextButton.classList.toggle('d-none', index === questionCards.length - 1);
    }
    updateAnswerState();
  };

  paletteButtons.forEach((button) => button.addEventListener('click', () => showQuestion(Number(button.dataset.goTo))));
  previousButton?.addEventListener('click', () => showQuestion(currentIndex - 1));
  nextButton?.addEventListener('click', () => showQuestion(currentIndex + 1));
  confirmSubmit?.addEventListener('click', () => {
    submissionConfirmed = true;
    submitConfirmation?.close();
    examForm.requestSubmit();
  });
  cancelSubmit?.addEventListener('click', () => submitConfirmation?.close());
  examForm.addEventListener('change', updateAnswerState);
  examForm.addEventListener('submit', (event) => {
    const unanswered = questionCards.length - questionCards.filter((card) => card.querySelector('input[type="radio"]:checked')).length;
    if (unanswered) {
      event.preventDefault();
      if (examForm.dataset.autoSubmit === 'true') sessionStorage.removeItem(timerKey);
      if (submitHint) submitHint.textContent = examForm.dataset.autoSubmit === 'true'
        ? 'Time is up. Answer every question before submitting.'
        : 'Answer all questions to enable submission.';
      return;
    }
    if (examForm.dataset.autoSubmit === 'true') {
      sessionStorage.removeItem(timerKey);
      return;
    }
    if (!submissionConfirmed) {
      event.preventDefault();
      submitConfirmation?.showModal();
      return;
    }
    submissionConfirmed = false;
    sessionStorage.removeItem(timerKey);
  });
  showQuestion(0);
  timerTick();
}
