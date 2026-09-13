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
  const explanations = {
    1: 'Benchmark regressions are the best promotion gate because they catch quality drift before executives feel it.',
    2: 'Supervisor Agent is strongest when it must route across multiple agents, tools, or domains rather than answer from one source.',
    3: 'Trust comes from governed data, clear definitions, and representative examples, not from larger prompts alone.'
  };

  document.querySelectorAll('.quiz-card').forEach((card, cardIndex) => {
    const correct = card.dataset.answer;
    const feedback = card.querySelector('.quiz-feedback');
    const options = card.querySelectorAll('.quiz-option');

    options.forEach(option => {
      option.addEventListener('click', () => {
        const choice = option.dataset.choice;
        options.forEach(btn => btn.classList.add('disabled'));

        if (choice === correct) {
          option.classList.add('correct');
          feedback.textContent = `Correct. ${explanations[cardIndex + 1]}`;
        } else {
          option.classList.add('incorrect');
          const correctOption = card.querySelector(`.quiz-option[data-choice="${correct}"]`);
          if (correctOption) correctOption.classList.add('correct');
          feedback.textContent = `Not quite. ${explanations[cardIndex + 1]}`;
        }
      });
    });
  });
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
