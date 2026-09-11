/* ============================================================
   FCTG x Databricks  –  Lunch & Learn Interactive Script
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ────────── Sidebar Navigation ────────── */
  const sessionItems = document.querySelectorAll('.session-item');
  const sessionPages = document.querySelectorAll('.session-page');

  sessionItems.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.session;

      // Update sidebar active state
      sessionItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      // Show correct session page
      sessionPages.forEach(page => {
        page.classList.remove('active');
        if (page.id === target) {
          page.classList.add('active');
          page.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });

      // Close mobile sidebar
      document.getElementById('sidebar').classList.remove('open');
    });
  });

  /* ────────── Mobile Menu Toggle ────────── */
  const menuToggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');

  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 768 &&
          !sidebar.contains(e.target) &&
          !menuToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  /* ────────── 3D Stack Visualization ────────── */
  const stackScene = document.getElementById('stack-3d');
  const toggleBtn = document.getElementById('toggle-stack');
  const collapseBtn = document.getElementById('collapse-stack');
  const roadmapGrid = document.getElementById('roadmap-grid');
  let isUnstacked = false;

  function unstackLayers() {
    if (isUnstacked) return;
    isUnstacked = true;

    // Add unstacked class for CSS animation
    stackScene.classList.add('unstacked');
    toggleBtn.classList.add('hidden');

    // After stack fades, show roadmap grid
    setTimeout(() => {
      stackScene.style.display = 'none';
      roadmapGrid.classList.remove('hidden');
      roadmapGrid.classList.add('visible');
      collapseBtn.classList.remove('hidden');
    }, 600);
  }

  function collapseToStack() {
    if (!isUnstacked) return;
    isUnstacked = false;

    roadmapGrid.classList.remove('visible');
    roadmapGrid.classList.add('hidden');
    collapseBtn.classList.add('hidden');

    stackScene.style.display = 'block';
    // Small delay for DOM repaint
    requestAnimationFrame(() => {
      stackScene.classList.remove('unstacked');
      toggleBtn.classList.remove('hidden');
    });
  }

  if (toggleBtn) toggleBtn.addEventListener('click', unstackLayers);
  if (collapseBtn) collapseBtn.addEventListener('click', collapseToStack);

  /* ────────── Layer Hover Glow Effect ────────── */
  const layers = document.querySelectorAll('.stack-layer');
  layers.forEach(layer => {
    layer.addEventListener('click', unstackLayers);

    // Subtle float animation on hover
    layer.addEventListener('mouseenter', () => {
      if (!isUnstacked) {
        layer.style.transform = `
          translateX(-50%)
          translateY(calc((4 - ${layer.style.getPropertyValue('--i')}) * 60px - 6px))
          rotateX(-20deg)
          rotateY(25deg)
          scale(1.04)
        `;
      }
    });

    layer.addEventListener('mouseleave', () => {
      if (!isUnstacked) {
        layer.style.transform = '';
      }
    });
  });

  /* ────────── Roadmap Card Hover Particles ────────── */
  const roadmapCards = document.querySelectorAll('.roadmap-card');
  roadmapCards.forEach(card => {
    card.addEventListener('mouseenter', () => {
      card.style.boxShadow = '0 8px 32px rgba(255,54,33,.12)';
    });
    card.addEventListener('mouseleave', () => {
      card.style.boxShadow = '';
    });
  });

  /* ────────── Scroll-Triggered Animations ────────── */
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const fadeInObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        fadeInObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // Animate content cards on scroll
  document.querySelectorAll('.content-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';
    card.style.transition = `opacity .6s ease ${i * 0.1}s, transform .6s ease ${i * 0.1}s`;
    fadeInObserver.observe(card);
  });

  /* ────────── Architecture Diagram Animation ────────── */
  const archBoxes = document.querySelectorAll('.arch-box');
  const archObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const boxes = entry.target.querySelectorAll('.arch-box');
        boxes.forEach((box, i) => {
          box.style.opacity = '0';
          box.style.transform = 'scale(0.9)';
          box.style.transition = `all .4s ease ${i * 0.08}s`;
          requestAnimationFrame(() => {
            box.style.opacity = '1';
            box.style.transform = 'scale(1)';
          });
        });
        archObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  document.querySelectorAll('.arch-diagram').forEach(d => archObserver.observe(d));

  /* ────────── Subtle background pulse on stack ────────── */
  if (stackScene) {
    let angle = 0;
    function animateStack() {
      if (!isUnstacked && stackScene.style.display !== 'none') {
        angle += 0.3;
        const y = Math.sin(angle * Math.PI / 180) * 3;
        stackScene.style.transform = `translateY(${y}px)`;
      }
      requestAnimationFrame(animateStack);
    }
    animateStack();
  }

  /* ────────── Resource Tile Interaction ────────── */
  document.querySelectorAll('.resource-tile:not(.placeholder)').forEach(tile => {
    tile.addEventListener('mouseenter', () => {
      tile.style.boxShadow = '0 8px 24px rgba(255,54,33,.15)';
    });
    tile.addEventListener('mouseleave', () => {
      tile.style.boxShadow = '';
    });
  });

  /* ────────── Gallery Slot Click Hint ────────── */
  document.querySelectorAll('.gallery-slot').forEach(slot => {
    slot.addEventListener('click', () => {
      slot.style.borderColor = '#FF3621';
      slot.innerHTML = '<span>📷</span><p>Drop an image here<br><small>(Coming soon)</small></p>';
      setTimeout(() => {
        slot.style.borderColor = '';
      }, 2000);
    });
  });

});
