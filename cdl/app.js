const state = {
  tab: 'home',
  questions: [],
  topics: [],
  questionIndex: 0,
  selected: null,
  showWhy: false,
  answered: 148,
  correct: 128,
  streak: 9
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function text(value) {
  return value && typeof value === 'object' ? value.en : value;
}

function progressFor(index) {
  const values = [82, 64, 47, 28, 71, 36, 90, 58, 44, 52, 33];
  return values[index % values.length];
}

function buildFlag() {
  const fabric = $('#flagFabric');
  if (!fabric) return;
  const red = '#4A1520';
  const white = '#5A544D';
  const blue = '#0A1220';
  const stripeH = 1000 / 13;
  const pieces = [];
  for (let i = 0; i < 13; i += 1) {
    pieces.push(`<rect x="0" y="${i * stripeH}" width="1900" height="${stripeH + 1}" fill="${i % 2 === 0 ? red : white}" />`);
  }
  pieces.push(`<rect x="0" y="0" width="760" height="${stripeH * 7}" fill="${blue}" />`);
  const starPath = (cx, cy, r) => {
    const points = [];
    for (let i = 0; i < 10; i += 1) {
      const angle = -Math.PI / 2 + (Math.PI / 5) * i;
      const radius = i % 2 === 0 ? r : r * 0.42;
      points.push(`${cx + Math.cos(angle) * radius},${cy + Math.sin(angle) * radius}`);
    }
    return `<polygon points="${points.join(' ')}" fill="#FFFFFF" opacity="0.25" />`;
  };
  const cols = 9;
  const rows = 7;
  const sx = 760 / (cols + 1);
  const sy = (stripeH * 7) / (rows + 1);
  for (let row = 1; row <= rows; row += 1) {
    for (let col = 1; col <= cols; col += 1) {
      if (row % 2 === 0 && col > cols - 1) continue;
      pieces.push(starPath(col * sx + (row % 2 === 0 ? sx * .5 : 0), row * sy, 16));
    }
  }
  pieces.push('<rect x="0" y="0" width="1900" height="1000" fill="url(#stripeSheen)" opacity=".42" />');
  fabric.innerHTML = pieces.join('');

  const turbulence = $('#flagTurbulence');
  let frame = 0;
  const animate = () => {
    frame += 1;
    if (frame % 3 === 0 && turbulence) {
      const t = performance.now() * 0.001;
      const x = 0.0065 + Math.sin(t * 0.72) * 0.0011;
      const y = 0.027 + Math.cos(t * 0.58) * 0.0025;
      turbulence.setAttribute('baseFrequency', `${x.toFixed(4)} ${y.toFixed(4)}`);
    }
    requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);
}

function renderHome() {
  const accuracy = Math.round((state.correct / state.answered) * 100);
  $('#home').innerHTML = `
    <div class="hero stack">
      <span class="pill">FMCSA focused • Offline PWA</span>
      <h1>Ready to pass your <span class="gold">CDL?</span></h1>
      <p>Train with tough scenarios drivers miss: pre-trip, air brakes, hazmat, tankers, emergencies and road safety.</p>
    </div>
    <section class="card readiness-card">
      <div class="ring" style="--value: ${accuracy}"><div><strong>${accuracy}%</strong><br><span>Ready</span></div></div>
      <div class="stack">
        <h3>Readiness ring</h3>
        <p>Your score is trending up. One more short practice run keeps the streak alive.</p>
        <button class="btn primary" data-action="start-practice">Quick practice</button>
      </div>
    </section>
    <section class="grid-3" style="margin-top:14px">
      <div class="stat-card"><strong>${state.streak}</strong><span>Day streak</span></div>
      <div class="stat-card"><strong>${state.answered}</strong><span>Answered</span></div>
      <div class="stat-card"><strong>${accuracy}%</strong><span>Accuracy</span></div>
    </section>
    <section class="stack" style="margin-top:18px">
      <div class="row"><h2>Quick Start</h2><span class="pill">3 paths</span></div>
      <div class="grid-3">
        <button class="card quick-card" data-action="start-practice"><span class="quick-icon">📝</span><b>Practice Test</b><small>15 questions</small></button>
        <button class="card quick-card" data-tab-target="study"><span class="quick-icon">🔎</span><b>Pre-Trip</b><small>Checklist</small></button>
        <button class="card quick-card" data-action="mock-exam"><span class="quick-icon">🎯</span><b>Mock Exam</b><small>Timed mode</small></button>
      </div>
    </section>
    <section class="card continue-card" style="margin-top:18px">
      <div class="row"><h3>Continue learning</h3><span class="pill">44%</span></div>
      <p><b>Emergencies:</b> tire blowouts, skids, brake failure and roadside triangles.</p>
      <div class="progress-bar" style="--bar:#F97316"><span style="--progress:44%"></span></div>
      <button class="btn secondary" data-tab-target="study">Resume topic</button>
    </section>
  `;
}

function renderStudy() {
  const list = state.topics.map((topic, index) => {
    const progress = progressFor(index);
    return `
      <article class="card topic-card" style="--topic-color:${topic.color}">
        <div class="topic-strip"></div>
        <div class="topic-body">
          <div class="topic-title"><span>${topic.emoji || '📚'}</span><div><h3>${text(topic.title)}</h3><p>${text(topic.summary)}</p></div></div>
          <div class="progress-bar" style="--bar:${topic.color}"><span style="--progress:${progress}%"></span></div>
          <div class="topic-actions">
            <button class="btn secondary" data-action="learn" data-topic="${topic.id}">LEARN</button>
            <button class="btn ghost" data-action="practice-topic" data-topic="${topic.id}">PRACTICE</button>
          </div>
        </div>
      </article>
    `;
  }).join('');
  $('#study').innerHTML = `
    <div class="hero stack">
      <span class="pill">11 CDL manual topics</span>
      <h2>Study by topic</h2>
      <p>Short modules with progress bars and focused practice for every endorsement.</p>
    </div>
    <div class="stack">${list}</div>
  `;
}

function currentQuestion() {
  return state.questions[state.questionIndex % state.questions.length];
}

function renderExam() {
  const q = currentQuestion();
  if (!q) {
    $('#exam').innerHTML = '<div class="card pad"><h2>Loading questions…</h2></div>';
    return;
  }
  const topic = state.topics.find((item) => item.id === q.topicId);
  const options = q.options.map((option) => {
    const isSelected = state.selected === option.id;
    const isCorrect = option.id === q.correctAnswer;
    const className = state.selected ? (isCorrect ? 'correct' : isSelected ? 'wrong' : '') : '';
    return `
      <button class="option ${className}" data-answer="${option.id}" ${state.selected ? 'disabled' : ''}>
        <span class="letter-bubble">${option.id}</span>
        <span>${text(option.text)}</span>
      </button>
    `;
  }).join('');
  const feedback = state.selected ? `
    <div class="feedback ${state.showWhy ? 'open' : ''}">
      <button class="why-toggle" data-action="toggle-why">
        <span>${state.selected === q.correctAnswer ? 'Correct — nice work' : 'Not quite'} · why?</span>
        <span>${state.showWhy ? '−' : '+'}</span>
      </button>
      <p class="explanation">${text(q.explanation)}</p>
    </div>
  ` : '';
  $('#exam').innerHTML = `
    <div class="hero stack">
      <span class="pill">${topic ? text(topic.title) : 'Practice Test'}</span>
      <h2>Practice exam</h2>
      <p>Answer the question, open the explanation, then move to the next scenario.</p>
    </div>
    <article class="card question-card">
      <div class="question-meta"><span>Question ${state.questionIndex + 1} of ${state.questions.length}</span><span>${q.correctAnswer ? 'FMCSA style' : ''}</span></div>
      <div class="question-text">${text(q.text)}</div>
      <div class="options">${options}</div>
      ${feedback}
      <button class="btn primary full" data-action="next-question">Next</button>
    </article>
  `;
}

function renderTools() {
  $('#tools').innerHTML = `
    <div class="hero stack">
      <span class="pill">Driver toolbox</span>
      <h2>Tools for test day</h2>
      <p>Fast helpers that keep pre-trip, inspection and vocabulary close at hand.</p>
    </div>
    <div class="tool-grid">
      <article class="card tool-card"><span class="quick-icon">🔎</span><b>Pre-Trip Checklist</b><p>Engine, suspension, brakes, lights, trailer and cab flow.</p></article>
      <article class="card tool-card"><span class="quick-icon">👮</span><b>Inspector Q&A</b><p>Common verbal inspection prompts with crisp answers.</p></article>
      <article class="card tool-card"><span class="quick-icon">🪧</span><b>Road Signs</b><p>High-signal signs and CDL-specific warnings.</p></article>
      <article class="card tool-card"><span class="quick-icon">📖</span><b>Vocabulary</b><p>Endorsements, placards, coupling, baffles and brake terms.</p></article>
    </div>
  `;
}

function renderProfile() {
  const accuracy = Math.round((state.correct / state.answered) * 100);
  $('#profile').innerHTML = `
    <div class="hero stack">
      <span class="pill">Your progress</span>
      <h2>Profile</h2>
      <p>Offline progress is stored locally in this PWA.</p>
    </div>
    <section class="card profile-badge">
      <div class="avatar">🚛</div>
      <h2>Commercial Driver Candidate</h2>
      <p>${state.streak}-day streak • ${accuracy}% readiness</p>
    </section>
    <section class="stack" style="margin-top:14px">
      <div class="card pad row"><span>Questions answered</span><b>${state.answered}</b></div>
      <div class="card pad row"><span>Correct answers</span><b>${state.correct}</b></div>
      <div class="card pad row"><span>Saved offline</span><b class="gold">Ready</b></div>
    </section>
  `;
}

function render() {
  renderHome();
  renderStudy();
  renderExam();
  renderTools();
  renderProfile();
  bindActions();
}

function setTab(tab) {
  state.tab = tab;
  $$('.screen').forEach((screen) => screen.classList.toggle('active', screen.id === tab));
  $$('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.tab === tab));
  $('.screen-scroll').scrollTop = 0;
}

function bindActions() {
  $$('[data-tab]').forEach((button) => button.onclick = () => setTab(button.dataset.tab));
  $$('[data-tab-target]').forEach((button) => button.onclick = () => setTab(button.dataset.tabTarget));
  $$('[data-action="start-practice"], [data-action="mock-exam"], [data-action="practice-topic"]').forEach((button) => {
    button.onclick = () => { state.selected = null; state.showWhy = false; setTab('exam'); renderExam(); bindActions(); };
  });
  $$('[data-action="learn"]').forEach((button) => {
    button.onclick = () => { setTab('exam'); state.selected = currentQuestion().correctAnswer; state.showWhy = true; renderExam(); bindActions(); };
  });
  $$('[data-answer]').forEach((button) => {
    button.onclick = () => {
      if (state.selected) return;
      const q = currentQuestion();
      state.selected = button.dataset.answer;
      state.showWhy = false;
      state.answered += 1;
      if (state.selected === q.correctAnswer) state.correct += 1;
      renderExam(); bindActions();
    };
  });
  const toggle = $('[data-action="toggle-why"]');
  if (toggle) toggle.onclick = () => { state.showWhy = !state.showWhy; renderExam(); bindActions(); };
  const next = $('[data-action="next-question"]');
  if (next) next.onclick = () => {
    state.questionIndex = (state.questionIndex + 1) % state.questions.length;
    state.selected = null;
    state.showWhy = false;
    renderExam(); bindActions();
  };
}

async function loadData() {
  try {
    const [questions, topics] = await Promise.all([
      fetch('data/questions.json').then((response) => response.json()),
      fetch('data/topics.json').then((response) => response.json())
    ]);
    state.questions = questions;
    state.topics = topics;
  } catch (error) {
    state.questions = [{
      topicId: 'emergencies',
      text: { en: 'Steer-tire failure at highway speed is recognized by:' },
      options: [
        { id: 'A', text: { en: 'Radio static' } },
        { id: 'B', text: { en: 'Strong pull, vibration, loud bang or flapping' } },
        { id: 'C', text: { en: 'Engine temperature spike' } },
        { id: 'D', text: { en: 'Truck horn sounding' } }
      ],
      correctAnswer: 'B',
      explanation: { en: 'A front blowout causes sudden steering pull and vibration. Hold the wheel firm and do not brake.' }
    }];
    state.topics = [];
  }
  render();
}

buildFlag();
loadData();
