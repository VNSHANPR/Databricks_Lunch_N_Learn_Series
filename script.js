/* ============================================================
   Databricks Lunch & Learn Interactive Script
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initSessionNavigation();
  initMobileMenu();
  initAgendaTabs();
  initTerminalSimulation();
  initQuiz();
  initScrollAnimations();
  initResourceTiles();
  initGalleryHints();
});

function initSessionNavigation() {
  const sessionItems = document.querySelectorAll('.session-item');
  const sessionPages = document.querySelectorAll('.session-page');
  const sidebar = document.getElementById('sidebar');

  sessionItems.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.session;
      sessionItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      sessionPages.forEach(page => {
        page.classList.toggle('active', page.id === target);
      });

      if (sidebar) sidebar.classList.remove('open');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

function initMobileMenu() {
  const menuToggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  if (!menuToggle || !sidebar) return;

  menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  document.addEventListener('click', event => {
    if (window.innerWidth <= 768 && !sidebar.contains(event.target) && !menuToggle.contains(event.target)) {
      sidebar.classList.remove('open');
    }
  });
}

function initAgendaTabs() {
  const tabs = document.querySelectorAll('.agenda-tab');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      panels.forEach(panel => panel.classList.remove('active'));

      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add('active');
    });
  });
}

function initTerminalSimulation() {
  const commandEl = document.getElementById('terminal-command');
  const outputEl = document.getElementById('terminal-output');
  if (!commandEl || !outputEl) return;

  const command = 'databricks bundle generate --existing-space-id abc123';
  const outputLines = [
    'Connecting to Databricks workspace...',
    'Fetching Genie space configuration...',
    'Discovering linked tables and permissions...',
    'Generating databricks.yml with resource definitions...',
    'Writing ./databricks.yml  ...done',
    'Writing ./resources/genie_space.yml  ...done',
    'Bundle scaffold created. Run "databricks bundle deploy" to publish.'
  ];

  let index = 0;
  const typeCommand = () => {
    if (index <= command.length) {
      commandEl.textContent = command.slice(0, index);
      index += 1;
      setTimeout(typeCommand, 55);
      return;
    }

    outputLines.forEach((line, lineIndex) => {
      setTimeout(() => {
        const div = document.createElement('div');
        div.className = 'terminal-output-line';
        div.textContent = line;
        outputEl.appendChild(div);
      }, 250 + (lineIndex * 420));
    });
  };

  setTimeout(typeCommand, 400);
}

function initQuiz() {
  const cards = Array.from(document.querySelectorAll('.quiz-card'));
  if (!cards.length) return;
  const total = cards.length;
  const fill = document.getElementById('quiz-progress-fill');
  const progressText = document.getElementById('quiz-progress-text');
  const result = document.getElementById('quiz-result');
  const successEl = document.getElementById('quiz-success');
  const retryEl = document.getElementById('quiz-retry');
  const retryText = document.getElementById('quiz-retry-text');

  let answered = 0;
  let correctCount = 0;

  function updateProgress() {
    if (fill) fill.style.width = `${(answered / total) * 100}%`;
    if (progressText) progressText.textContent = `${answered} of ${total} answered`;
  }

  function finish() {
    if (result) result.hidden = false;
    const perfect = correctCount === total;
    if (successEl) successEl.hidden = !perfect;
    if (retryEl) retryEl.hidden = perfect;
    if (!perfect && retryText) {
      retryText.textContent = `You got ${correctCount} of ${total} correct. The certification needs all ${total} — give it another go!`;
    }
    if (result) result.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function bindCard(card) {
    const correct = card.dataset.answer;
    const explain = card.dataset.explain || '';
    const feedback = card.querySelector('.quiz-feedback');
    const options = card.querySelectorAll('.quiz-option');

    options.forEach(option => {
      option.addEventListener('click', () => {
        if (card.dataset.done === 'true') return;
        card.dataset.done = 'true';
        const choice = option.dataset.choice;
        options.forEach(btn => btn.classList.add('disabled'));

        if (choice === correct) {
          option.classList.add('correct');
          feedback.className = 'quiz-feedback correct';
          feedback.textContent = `Correct. ${explain}`;
          correctCount += 1;
        } else {
          option.classList.add('incorrect');
          const correctOption = card.querySelector(`.quiz-option[data-choice="${correct}"]`);
          if (correctOption) correctOption.classList.add('correct');
          feedback.className = 'quiz-feedback incorrect';
          feedback.textContent = `Not quite. ${explain}`;
        }

        answered += 1;
        updateProgress();
        if (answered === total) finish();
      });
    });
  }

  function reset() {
    answered = 0;
    correctCount = 0;
    cards.forEach(card => {
      card.dataset.done = 'false';
      const feedback = card.querySelector('.quiz-feedback');
      if (feedback) { feedback.textContent = ''; feedback.className = 'quiz-feedback'; }
      card.querySelectorAll('.quiz-option').forEach(btn =>
        btn.classList.remove('disabled', 'correct', 'incorrect'));
    });
    if (result) result.hidden = true;
    if (successEl) successEl.hidden = true;
    if (retryEl) retryEl.hidden = true;
    updateProgress();
    cards[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  cards.forEach(bindCard);
  ['quiz-retry-btn', 'quiz-retry-btn2'].forEach(id => {
    const b = document.getElementById(id);
    if (b) b.addEventListener('click', reset);
  });
  updateProgress();
}

function initScrollAnimations() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.content-card, .terminal-card').forEach((element, i) => {
    element.style.opacity = '0';
    element.style.transform = 'translateY(24px)';
    element.style.transition = `opacity .55s ease ${i * 0.06}s, transform .55s ease ${i * 0.06}s`;
    observer.observe(element);
  });
}

function initResourceTiles() {
  document.querySelectorAll('.resource-tile:not(.placeholder)').forEach(tile => {
    tile.addEventListener('mouseenter', () => {
      tile.style.boxShadow = '0 10px 28px rgba(255,54,33,.16)';
    });
    tile.addEventListener('mouseleave', () => {
      tile.style.boxShadow = '';
    });
  });
}

function initGalleryHints() {
  document.querySelectorAll('.gallery-slot').forEach(slot => {
    slot.addEventListener('click', () => {
      slot.style.borderColor = '#FF3621';
      slot.innerHTML = '<span>+</span><p>Media placeholder ready</p>';
      setTimeout(() => { slot.style.borderColor = ''; }, 1500);
    });
  });
}
