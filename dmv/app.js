/* =========================================================================
   DMV Practice Test 2026 — PWA App
   ========================================================================= */

/* ---------- DATA ---------- */
const CATEGORIES = [
  { id: 'Road Signs',    emoji: '🚦', target: 25 },
  { id: 'Traffic Laws',  emoji: '📋', target: 25 },
  { id: 'Safe Driving',  emoji: '🚗', target: 20 },
  { id: 'Parking Rules', emoji: '🅿️', target: 15 },
  { id: 'Alcohol & DUI', emoji: '🍺', target: 15 }
];

const TOOLS_DATA = [
  {
    emoji: '🚦', label: 'Road Signs Gallery', sub: 'Shapes, colors & meaning',
    items: [
      { title: '🛑 Octagon (Red)', desc: 'STOP — Come to a complete stop and yield.' },
      { title: '⬆️ Inverted Triangle', desc: 'YIELD — Slow down, give right-of-way.' },
      { title: '⬛ Diamond (Yellow)', desc: 'WARNING — Hazard or condition ahead.' },
      { title: '⬜ Rectangle (White)', desc: 'REGULATORY — Speed limits, lane rules.' },
      { title: '🟢 Circle (Yellow)', desc: 'RAILROAD — Advance warning of crossing.' },
      { title: '⭐ Pentagon (Yellow)', desc: 'SCHOOL — Watch for children and buses.' },
      { title: '✕ Crossbuck (White)', desc: 'RAILROAD CROSSING — At the tracks.' },
      { title: '🔵 Square/Rectangle (Blue/Green)', desc: 'GUIDE — Services, destinations, routes.' }
    ]
  },
  {
    emoji: '🅿️', label: 'Parking Rules', sub: 'Curbs, hills & distances',
    items: [
      { title: '⬆️ Uphill with curb', desc: 'Turn wheels LEFT (away from curb). Car rolls into curb.' },
      { title: '⬆️ Uphill NO curb', desc: 'Turn wheels RIGHT (off road). Car rolls off road, not into traffic.' },
      { title: '⬇️ Downhill (any)', desc: 'Turn wheels RIGHT (toward curb). Car rolls into curb.' },
      { title: '🔴 Red curb', desc: 'No stopping or parking at any time.' },
      { title: '🟡 Yellow curb', desc: 'Loading zone — freight/passengers, limited time.' },
      { title: '⚪ White curb', desc: 'Passenger loading only — 5 minutes max.' },
      { title: '🟢 Green curb', desc: 'Limited-time parking (check sign for duration).' },
      { title: '🔵 Blue curb', desc: 'Disabled persons only (placard required).' },
      { title: '📏 18 inches', desc: 'Wheels must be within 18 inches of the curb.' }
    ]
  },
  {
    emoji: '🏎️', label: 'Speed Limits', sub: 'By zone and condition',
    items: [
      { title: '🏘️ Residential', desc: '25 mph (unless otherwise posted).' },
      { title: '🏫 School zone', desc: '25 mph when children are present.' },
      { title: '🏙️ Business district', desc: '25 mph (unless otherwise posted).' },
      { title: '🛣️ Highway (2-lane)', desc: '55 mph (unless otherwise posted).' },
      { title: '🛣️ Freeway', desc: '65 mph (may be posted higher, up to 70).' },
      { title: '🅿️ Alley', desc: '15 mph.' },
      { title: '🚧 Construction zone', desc: 'Obey posted signs; fines doubled.' },
      { title: '🌧️ Rain/Fog', desc: 'Reduce speed — no specific limit, drive for conditions.' }
    ]
  }
];

let allQuestions = [];
let progress = loadProgress();

/* ---------- STATE ---------- */
let currentScreen = 'home';
let quizState = null; // { questions, current, correct, answered, mode, category, timer, timerInterval }

/* ---------- STORAGE ---------- */
function loadProgress() {
  try {
    const d = JSON.parse(localStorage.getItem('dmv_progress') || '{}');
    return {
      answered: d.answered || {},        // questionId -> true/false (correct)
      catAnswered: d.catAnswered || {},   // cat -> { total, correct }
      exams: d.exams || [],              // [{ score, total, date }]
      totalCorrect: d.totalCorrect || 0,
      totalAnswered: d.totalAnswered || 0
    };
  } catch { return { answered: {}, catAnswered: {}, exams: [], totalCorrect: 0, totalAnswered: 0 }; }
}
function saveProgress() {
  localStorage.setItem('dmv_progress', JSON.stringify(progress));
}
function resetProgress() {
  progress = { answered: {}, catAnswered: {}, exams: [], totalCorrect: 0, totalAnswered: 0 };
  saveProgress();
}
function getCatProgress(catId) {
  const d = progress.catAnswered[catId];
  if (!d) return { total: 0, correct: 0 };
  return d;
}
function recordAnswer(q, wasCorrect) {
  progress.answered[q.id] = wasCorrect;
  progress.totalAnswered++;
  if (wasCorrect) progress.totalCorrect++;
  const cat = q.category;
  if (!progress.catAnswered[cat]) progress.catAnswered[cat] = { total: 0, correct: 0 };
  progress.catAnswered[cat].total++;
  if (wasCorrect) progress.catAnswered[cat].correct++;
  saveProgress();
}

/* ---------- HELPERS ---------- */
function esc(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

/* ---------- NAVIGATION ---------- */
const SCREENS = ['home', 'study', 'exam', 'tools', 'profile'];
const NAV_ITEMS = [
  { id: 'home',    emoji: '🏠', label: 'Home' },
  { id: 'study',   emoji: '📚', label: 'Study' },
  { id: 'exam',    emoji: '📝', label: 'Exam' },
  { id: 'tools',   emoji: '🛠️', label: 'Tools' },
  { id: 'profile', emoji: '👤', label: 'Profile' }
];

function renderNav() {
  const nav = document.getElementById('bottomNav');
  nav.innerHTML = NAV_ITEMS.map(n =>
    `<button class="nav-item${currentScreen === n.id ? ' active' : ''}" data-screen="${n.id}">` +
    `<span class="nav-emoji">${n.emoji}</span><span>${n.label}</span></button>`
  ).join('');
  nav.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.screen));
  });
}

function navigateTo(screen) {
  if (quizState && quizState.timerInterval) clearInterval(quizState.timerInterval);
  quizState = null;
  currentScreen = screen;
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const el = document.getElementById('screen' + screen.charAt(0).toUpperCase() + screen.slice(1));
  if (el) el.classList.add('active');
  // Also hide quiz screen
  document.getElementById('screenQuiz').classList.remove('active');
  renderNav();
  renderScreen(screen);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showQuizScreen() {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screenQuiz').classList.add('active');
}

/* ---------- RENDER SCREENS ---------- */
function renderScreen(screen) {
  switch (screen) {
    case 'home': renderHome(); break;
    case 'study': renderStudy(); break;
    case 'exam': renderExam(); break;
    case 'tools': renderTools(); break;
    case 'profile': renderProfile(); break;
  }
}

/* --- HOME --- */
function renderHome() {
  const el = document.getElementById('screenHome');
  const readiness = allQuestions.length ? Math.round((progress.totalCorrect / allQuestions.length) * 100) : 0;
  const radius = 58;
  const circ = 2 * Math.PI * radius;
  const offset = circ * (1 - readiness / 100);

  let h = '';
  h += `<h1 class="home-title"><span class="blue">Ready to pass your<br>DMV test?</span></h1>`;

  // Readiness ring
  h += `<div class="readiness">`;
  h += `<div class="readiness-ring">`;
  h += `<svg viewBox="0 0 140 140"><circle class="ring-bg" cx="70" cy="70" r="${radius}" fill="none" stroke-width="8"/>`;
  h += `<circle class="ring-fg" cx="70" cy="70" r="${radius}" fill="none" stroke-width="8" stroke-linecap="round" stroke-dasharray="${circ}" stroke-dashoffset="${circ}" id="homeRingFg"/></svg>`;
  h += `<div class="readiness-num"><div class="readiness-pct">${readiness}%</div><div class="readiness-label">Readiness</div></div>`;
  h += `</div></div>`;

  // Quick Start
  h += `<div class="quick-start">`;
  h += `<button class="qs-btn" data-action="practice"><span class="qs-emoji">📝</span>Practice Test<span class="qs-arrow">→</span></button>`;
  h += `<button class="qs-btn" data-action="signs"><span class="qs-emoji">🚦</span>Road Signs<span class="qs-arrow">→</span></button>`;
  h += `<button class="qs-btn" data-action="exam"><span class="qs-emoji">🎯</span>Mock Exam<span class="qs-arrow">→</span></button>`;
  h += `</div>`;

  // Continue learning
  h += `<div class="section-title">Continue learning</div>`;
  h += `<div class="cat-cards">`;
  for (const cat of CATEGORIES) {
    const cp = getCatProgress(cat.id);
    const catQs = allQuestions.filter(q => q.category === cat.id);
    const pct = catQs.length ? Math.round((cp.correct / catQs.length) * 100) : 0;
    h += `<button class="cat-card" data-cat="${esc(cat.id)}">`;
    h += `<span class="cat-emoji">${cat.emoji}</span>`;
    h += `<div class="cat-info">`;
    h += `<div class="cat-name">${esc(cat.id)}</div>`;
    h += `<div class="cat-progress-text">${cp.correct}/${catQs.length} mastered</div>`;
    h += `<div class="cat-bar"><div class="cat-bar-fill" style="width:${pct}%"></div></div>`;
    h += `</div>`;
    h += `<span class="cat-arrow">→</span>`;
    h += `</button>`;
  }
  h += `</div>`;

  el.innerHTML = h;

  // Animate ring
  requestAnimationFrame(() => {
    setTimeout(() => {
      const ring = document.getElementById('homeRingFg');
      if (ring) ring.style.strokeDashoffset = offset;
    }, 100);
  });

  // Event listeners
  el.querySelector('[data-action="practice"]').addEventListener('click', () => startPractice());
  el.querySelector('[data-action="signs"]').addEventListener('click', () => startPractice('Road Signs'));
  el.querySelector('[data-action="exam"]').addEventListener('click', () => navigateTo('exam'));
  el.querySelectorAll('.cat-card').forEach(card => {
    card.addEventListener('click', () => startPractice(card.dataset.cat));
  });
}

/* --- STUDY --- */
function renderStudy() {
  const el = document.getElementById('screenStudy');
  let h = `<h2 class="study-title">Study by Category</h2>`;
  h += `<div class="study-cat-list">`;
  for (const cat of CATEGORIES) {
    const cp = getCatProgress(cat.id);
    const catQs = allQuestions.filter(q => q.category === cat.id);
    const pct = catQs.length ? Math.round((cp.correct / catQs.length) * 100) : 0;
    h += `<div class="study-cat-card">`;
    h += `<div class="study-cat-header">`;
    h += `<span class="cat-emoji">${cat.emoji}</span>`;
    h += `<span class="cat-name">${esc(cat.id)}</span>`;
    h += `<span class="cat-count">${catQs.length} questions</span>`;
    h += `</div>`;
    h += `<div class="study-bar-row"><div class="study-bar"><div class="study-bar-fill" style="width:${pct}%"></div></div><span class="study-bar-pct">${pct}%</span></div>`;
    h += `<div class="study-btns">`;
    h += `<button class="study-btn learn" data-cat="${esc(cat.id)}" data-mode="learn">LEARN</button>`;
    h += `<button class="study-btn practice" data-cat="${esc(cat.id)}" data-mode="practice">PRACTICE</button>`;
    h += `</div></div>`;
  }
  h += `</div>`;
  el.innerHTML = h;

  el.querySelectorAll('.study-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      startPractice(btn.dataset.cat);
    });
  });
}

/* --- EXAM --- */
function renderExam() {
  const el = document.getElementById('screenExam');
  let h = `<div class="exam-intro">`;
  h += `<h2>Mock DMV Exam</h2>`;
  h += `<p>30 random questions, 30-minute timer.<br>You need 80% (24/30) to pass.</p>`;
  h += `<div class="exam-stats">`;
  h += `<div class="exam-stat"><div class="stat-val">30</div><div class="stat-label">Questions</div></div>`;
  h += `<div class="exam-stat"><div class="stat-val">30:00</div><div class="stat-label">Minutes</div></div>`;
  h += `<div class="exam-stat"><div class="stat-val">80%</div><div class="stat-label">Pass rate</div></div>`;
  h += `</div>`;

  if (progress.exams.length) {
    const last = progress.exams[progress.exams.length - 1];
    h += `<p style="color:var(--muted);font-size:12px;margin-bottom:12px;">Last attempt: ${last.score}/${last.total} (${Math.round(last.score/last.total*100)}%)</p>`;
  }

  h += `<button class="start-exam-btn" id="startExamBtn">Start Mock Exam →</button>`;
  h += `</div>`;
  el.innerHTML = h;

  document.getElementById('startExamBtn').addEventListener('click', startExam);
}

/* --- TOOLS --- */
function renderTools(detail) {
  const el = document.getElementById('screenTools');
  if (detail !== undefined) {
    const tool = TOOLS_DATA[detail];
    let h = `<div class="tool-detail">`;
    h += `<h3>${tool.emoji} ${esc(tool.label)}</h3>`;
    for (const item of tool.items) {
      h += `<div class="tool-item"><div class="tool-item-title">${esc(item.title)}</div><div class="tool-item-desc">${esc(item.desc)}</div></div>`;
    }
    h += `<button class="tool-back-btn" id="toolBackBtn">← Back to Tools</button>`;
    h += `</div>`;
    el.innerHTML = h;
    document.getElementById('toolBackBtn').addEventListener('click', () => renderTools());
    return;
  }
  let h = `<h2 class="tools-title">Tools</h2>`;
  h += `<div class="tools-grid">`;
  TOOLS_DATA.forEach((t, i) => {
    h += `<button class="tool-card" data-idx="${i}"><span class="tool-emoji">${t.emoji}</span><span class="tool-label">${esc(t.label)}</span><span class="tool-sub">${esc(t.sub)}</span></button>`;
  });
  h += `</div>`;
  el.innerHTML = h;
  el.querySelectorAll('.tool-card').forEach(card => {
    card.addEventListener('click', () => renderTools(parseInt(card.dataset.idx)));
  });
}

/* --- PROFILE --- */
function renderProfile() {
  const el = document.getElementById('screenProfile');
  const readiness = allQuestions.length ? Math.round((progress.totalCorrect / allQuestions.length) * 100) : 0;
  const accuracy = progress.totalAnswered ? Math.round((progress.totalCorrect / progress.totalAnswered) * 100) : 0;

  let h = `<h2 class="profile-title">Your Progress</h2>`;
  h += `<div class="profile-card"><h3>Overall Statistics</h3>`;
  h += `<div class="stat-row"><span class="stat-key">Readiness</span><span class="stat-value">${readiness}%</span></div>`;
  h += `<div class="stat-row"><span class="stat-key">Questions answered</span><span class="stat-value">${progress.totalAnswered}</span></div>`;
  h += `<div class="stat-row"><span class="stat-key">Correct answers</span><span class="stat-value">${progress.totalCorrect}</span></div>`;
  h += `<div class="stat-row"><span class="stat-key">Accuracy</span><span class="stat-value">${accuracy}%</span></div>`;
  h += `<div class="stat-row"><span class="stat-key">Exams taken</span><span class="stat-value">${progress.exams.length}</span></div>`;
  h += `</div>`;

  h += `<div class="profile-card"><h3>By Category</h3>`;
  for (const cat of CATEGORIES) {
    const cp = getCatProgress(cat.id);
    const catQs = allQuestions.filter(q => q.category === cat.id);
    h += `<div class="stat-row"><span class="stat-key">${cat.emoji} ${esc(cat.id)}</span><span class="stat-value">${cp.correct}/${catQs.length}</span></div>`;
  }
  h += `</div>`;

  h += `<button class="reset-btn" id="resetBtn">Reset All Progress</button>`;
  el.innerHTML = h;

  document.getElementById('resetBtn').addEventListener('click', () => {
    if (confirm('Reset all progress? This cannot be undone.')) {
      resetProgress();
      navigateTo('profile');
    }
  });
}

/* ---------- QUIZ ENGINE ---------- */
function startPractice(category) {
  let qs = category ? allQuestions.filter(q => q.category === category) : [...allQuestions];
  qs = shuffle(qs);
  quizState = {
    questions: qs,
    current: 0,
    correct: 0,
    answered: false,
    mode: 'practice',
    category: category || 'All Categories',
    feedbackCollapsed: false
  };
  showQuizScreen();
  renderQuizQuestion();
}

function startExam() {
  let qs = shuffle([...allQuestions]).slice(0, 30);
  quizState = {
    questions: qs,
    current: 0,
    correct: 0,
    answered: false,
    mode: 'exam',
    category: 'MOCK EXAM',
    feedbackCollapsed: false,
    timer: 30 * 60,
    timerInterval: null
  };
  showQuizScreen();
  renderQuizQuestion();
  // Start timer
  quizState.timerInterval = setInterval(() => {
    quizState.timer--;
    updateTimer();
    if (quizState.timer <= 0) {
      clearInterval(quizState.timerInterval);
      renderQuizResults();
    }
  }, 1000);
}

function updateTimer() {
  const el = document.getElementById('quizTimer');
  if (!el || !quizState) return;
  const m = Math.floor(quizState.timer / 60);
  const s = quizState.timer % 60;
  el.textContent = `${m}:${s.toString().padStart(2, '0')}`;
  if (quizState.timer < 60) el.style.color = 'var(--bad)';
}

function renderQuizQuestion() {
  const qs = quizState;
  if (!qs || qs.current >= qs.questions.length) { renderQuizResults(); return; }
  qs.answered = false;
  qs.feedbackCollapsed = false;
  const q = qs.questions[qs.current];
  const el = document.getElementById('screenQuiz');

  let h = '';
  h += `<div class="meta-row">`;
  h += `<button class="meta-back" id="quizBack">←</button>`;
  h += `<span class="meta-counter"><b>${qs.current + 1}</b>/${qs.questions.length}</span>`;
  h += `<span class="meta-pill">${esc(q.category)}</span>`;
  if (qs.mode === 'exam') {
    h += `<span class="meta-timer" id="quizTimer"></span>`;
  } else {
    h += `<span class="meta-pts">${qs.correct * 10} pts</span>`;
  }
  h += `</div>`;
  h += `<div class="progress-track"><div class="progress-bar" id="quizProgress" style="width:${(qs.current / qs.questions.length) * 100}%"></div></div>`;
  h += `<div class="quiz-shell">`;
  h += `<div class="q-text">${esc(q.text)}</div>`;
  h += `<div class="options">`;
  for (const o of q.options) {
    h += `<button class="option" data-id="${o.id}"><span class="opt-letter">${o.id}</span><span class="opt-text">${esc(o.text)}</span><span class="opt-icon"></span></button>`;
  }
  h += `</div>`;
  h += `<div class="feedback" id="quizFeedback">`;
  h += `<div class="feedback-header" id="quizFeedbackHeader">`;
  h += `<span class="feedback-title" id="quizFeedbackTitle"></span>`;
  h += `<span class="feedback-toggle">why</span></div>`;
  h += `<div class="feedback-body" id="quizFeedbackBody"></div></div>`;
  h += `<button class="next-btn" id="quizNext" disabled>Select an answer</button>`;
  h += `</div>`;

  el.innerHTML = h;

  if (qs.mode === 'exam') updateTimer();

  document.getElementById('quizBack').addEventListener('click', () => {
    if (quizState && quizState.timerInterval) clearInterval(quizState.timerInterval);
    quizState = null;
    navigateTo(currentScreen);
  });
  document.querySelectorAll('#screenQuiz .option').forEach(btn => {
    btn.addEventListener('click', () => onQuizAnswer(btn.dataset.id));
  });
  document.getElementById('quizNext').addEventListener('click', () => {
    qs.current++;
    renderQuizQuestion();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  const fbH = document.getElementById('quizFeedbackHeader');
  if (fbH) fbH.addEventListener('click', () => {
    qs.feedbackCollapsed = !qs.feedbackCollapsed;
    document.getElementById('quizFeedback').classList.toggle('collapsed', qs.feedbackCollapsed);
  });
}

function onQuizAnswer(chosenId) {
  const qs = quizState;
  if (!qs || qs.answered) return;
  qs.answered = true;
  const q = qs.questions[qs.current];
  const wasCorrect = chosenId === q.correctAnswer;
  if (wasCorrect) qs.correct++;
  recordAnswer(q, wasCorrect);

  document.querySelectorAll('#screenQuiz .option').forEach(btn => {
    btn.disabled = true;
    if (btn.dataset.id === q.correctAnswer) {
      btn.classList.add('correct');
      btn.querySelector('.opt-icon').textContent = '✓';
    }
    if (btn.dataset.id === chosenId && !wasCorrect) {
      btn.classList.add('wrong');
      btn.querySelector('.opt-icon').textContent = '✕';
    }
  });

  const pts = document.querySelector('#screenQuiz .meta-pts');
  if (pts) pts.textContent = (qs.correct * 10) + ' pts';

  const fb = document.getElementById('quizFeedback');
  fb.classList.add('show');
  fb.classList.toggle('is-correct', wasCorrect);
  qs.feedbackCollapsed = wasCorrect;
  fb.classList.toggle('collapsed', qs.feedbackCollapsed);

  document.getElementById('quizFeedbackTitle').textContent = wasCorrect
    ? '✓ Correct — tap "why" for details'
    : '✕ Incorrect — Here\'s Why';

  const correctOpt = q.options.find(o => o.id === q.correctAnswer);
  document.getElementById('quizFeedbackBody').textContent =
    `The correct answer is ${q.correctAnswer}: ${correctOpt ? correctOpt.text : ''}.`;

  const nextBtn = document.getElementById('quizNext');
  nextBtn.disabled = false;
  nextBtn.textContent = qs.current === qs.questions.length - 1 ? 'See Results →' : 'Next Question →';
  setTimeout(() => nextBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 50);
}

function renderQuizResults() {
  const qs = quizState;
  if (!qs) return;
  if (qs.timerInterval) clearInterval(qs.timerInterval);

  const total = qs.questions.length;
  const correct = qs.correct;
  const pct = Math.round((correct / total) * 100);
  const radius = 62;
  const circ = 2 * Math.PI * radius;
  const offset = circ * (1 - correct / total);

  let verdict = '';
  if (qs.mode === 'exam') {
    if (pct >= 80) verdict = '🎉 You PASSED! Great job!';
    else verdict = '❌ You need 80% to pass. Keep practicing!';
    progress.exams.push({ score: correct, total: total, date: new Date().toISOString() });
    saveProgress();
  } else {
    if (pct >= 80) verdict = 'Strong result! Keep it up.';
    else if (pct >= 60) verdict = 'Good progress. Review weak areas.';
    else verdict = 'Keep practicing — you\'ll get there!';
  }

  const el = document.getElementById('screenQuiz');
  let h = `<div class="results-card">`;
  h += `<div class="score-ring"><svg viewBox="0 0 140 140">`;
  h += `<defs><linearGradient id="blueGrad2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#60A5FA"/><stop offset="100%" stop-color="#1D4ED8"/></linearGradient></defs>`;
  h += `<circle class="ring-bg" cx="70" cy="70" r="${radius}" fill="none" stroke-width="8"/>`;
  h += `<circle class="ring-fg" cx="70" cy="70" r="${radius}" fill="none" stroke-width="8" stroke-linecap="round" stroke-dasharray="${circ}" stroke-dashoffset="${circ}" id="resultRingFg"/>`;
  h += `</svg><div class="score-num"><div class="score-pct">${pct}%</div><div class="score-label">${qs.mode === 'exam' ? (pct >= 80 ? 'PASSED' : 'FAILED') : 'Score'}</div></div></div>`;
  h += `<div class="score-correct">${correct} / ${total}</div>`;
  h += `<div class="score-correct-label">Answered correctly</div>`;
  h += `<div class="score-verdict">${verdict}</div>`;
  h += `<div class="results-btns">`;
  h += `<button class="results-btn primary" id="resultHome">Back to Home</button>`;
  if (qs.mode === 'exam') {
    h += `<button class="results-btn secondary" id="resultRetry">Retry Exam</button>`;
  } else {
    h += `<button class="results-btn secondary" id="resultRetry">Practice Again</button>`;
  }
  h += `</div></div>`;
  el.innerHTML = h;

  requestAnimationFrame(() => {
    setTimeout(() => {
      const ring = document.getElementById('resultRingFg');
      if (ring) ring.style.strokeDashoffset = offset;
    }, 100);
  });

  document.getElementById('resultHome').addEventListener('click', () => navigateTo('home'));
  document.getElementById('resultRetry').addEventListener('click', () => {
    if (qs.mode === 'exam') startExam();
    else startPractice(qs.category === 'All Categories' ? null : qs.category);
  });
}

/* ---------- ANIMATED US FLAG ---------- */
(function initFlag() {
  const COLORS = { red: '#4A1520', white: '#5A544D', blue: '#0A1220' };
  const STRIPE_COUNT = 13;
  const ROTATION = '-35deg';

  function buildFlag() {
    const SW = window.innerWidth, SH = window.innerHeight;
    const diagonal = Math.sqrt(SW * SW + SH * SH);
    const FLAG_W = diagonal * 1.4;
    const FLAG_H = FLAG_W / 1.9;
    const STRIPE_H = FLAG_H / STRIPE_COUNT;
    const CANTON_H = STRIPE_H * 7;
    const CANTON_W = FLAG_W * 0.4;
    const bottomOffset = -diagonal * 0.28;
    const leftOffset = -diagonal * 0.32;

    const stars = [];
    const cols = 9, rows = 7, sx = CANTON_W / (cols + 1), sy = CANTON_H / (rows + 1);
    for (let r = 1; r <= rows; r++) for (let c = 1; c <= cols; c++) {
      if (r % 2 === 0 && c > cols - 1) continue;
      const x = c * sx + (r % 2 === 0 ? sx * 0.5 : 0);
      const y = r * sy;
      const sz = STRIPE_H * 0.3;
      stars.push(`<path d="M ${x} ${y-sz} L ${x+sz*0.22} ${y-sz*0.22} L ${x+sz*0.95} ${y-sz*0.31} L ${x+sz*0.44} ${y+sz*0.22} L ${x+sz*0.59} ${y+sz*0.9} L ${x} ${y+sz*0.5} L ${x-sz*0.59} ${y+sz*0.9} L ${x-sz*0.44} ${y+sz*0.22} L ${x-sz*0.95} ${y-sz*0.31} L ${x-sz*0.22} ${y-sz*0.22} Z" fill="#FFFFFF" opacity="0.25"/>`);
    }

    let stripes = '';
    for (let i = 0; i < STRIPE_COUNT; i++) {
      stripes += `<rect x="0" y="${i * STRIPE_H}" width="${FLAG_W}" height="${STRIPE_H + 0.5}" fill="${i % 2 === 0 ? COLORS.red : COLORS.white}"/>`;
    }

    const wrap = document.getElementById('flagBg');
    wrap.innerHTML = `
      <div class="flag-layer" style="bottom:${bottomOffset}px;left:${leftOffset}px;width:${FLAG_W}px;height:${FLAG_H}px;transform:rotate(${ROTATION})">
        <svg width="${FLAG_W}" height="${FLAG_H}" viewBox="0 0 ${FLAG_W} ${FLAG_H}" style="overflow:visible">
          <defs>
            <filter id="flag-wave" x="-20%" y="-20%" width="140%" height="140%">
              <feTurbulence id="ft" type="fractalNoise" baseFrequency="0.00275 0.00525" numOctaves="2" seed="5" result="turbulence"/>
              <feDisplacementMap id="fd" in="SourceGraphic" in2="turbulence" scale="80" xChannelSelector="R" yChannelSelector="G"/>
            </filter>
          </defs>
          <g filter="url(#flag-wave)">
            ${stripes}
            <rect x="0" y="0" width="${CANTON_W}" height="${CANTON_H}" fill="${COLORS.blue}"/>
            ${stars.join('')}
          </g>
        </svg>
      </div>`;

    const ft = document.getElementById('ft');
    const fd = document.getElementById('fd');
    const startTime = performance.now();
    let frameCount = 0;

    function animate() {
      frameCount++;
      if (frameCount % 3 === 0) {
        const elapsed = performance.now() - startTime;
        const turbSin = Math.sin((elapsed % 32000) / 32000 * Math.PI * 2);
        const freqX = 0.00275 + 0.00075 * turbSin;
        const freqY = 0.00525 + 0.00125 * turbSin;
        if (ft) ft.setAttribute('baseFrequency', freqX.toFixed(5) + ' ' + freqY.toFixed(5));
        const dispSin = Math.sin((elapsed % 24000) / 24000 * Math.PI * 2);
        const scale = 80 + 5 * dispSin;
        if (fd) fd.setAttribute('scale', scale.toFixed(1));
      }
      requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
  }

  buildFlag();
  window.addEventListener('resize', buildFlag);
})();

/* ---------- INIT ---------- */
(async function init() {
  // Load questions (try fetch, fall back to inline)
  try {
    const resp = await fetch('data/questions.json');
    allQuestions = await resp.json();
  } catch {
    console.warn('Could not fetch questions.json, using empty set');
    allQuestions = [];
  }

  renderNav();
  renderHome();

  // Register SW
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
