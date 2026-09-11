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
  initArchitectureScene();
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

  const command = 'databricks bundle deploy --target prod';
  const outputLines = [
    'Validating bundle configuration...',
    'Uploading resources to workspace...',
    'Updating jobs, pipelines, and permissions...',
    'Running deployment checks...',
    'Deployment completed successfully.'
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

function initArchitectureScene() {
  const container = document.getElementById('architecture-3d');
  if (!container || typeof THREE === 'undefined') return;

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x0d1117, 16, 28);

  const camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 0.1, 1000);
  camera.position.set(10, 8, 13);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 8;
  controls.maxDistance = 20;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.55;
  controls.maxPolarAngle = Math.PI / 2.05;

  scene.add(new THREE.AmbientLight(0xffffff, 0.9));

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.15);
  keyLight.position.set(8, 14, 10);
  scene.add(keyLight);

  const rimLight = new THREE.PointLight(0xff6f42, 2, 30, 2);
  rimLight.position.set(-8, 8, 6);
  scene.add(rimLight);

  const base = new THREE.Mesh(
    new THREE.CylinderGeometry(6.4, 7.2, 0.6, 48),
    new THREE.MeshStandardMaterial({ color: 0x121821, metalness: 0.2, roughness: 0.72 })
  );
  base.position.y = -2.2;
  scene.add(base);

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(5.8, 0.08, 16, 90),
    new THREE.MeshBasicMaterial({ color: 0xff3621, transparent: true, opacity: 0.5 })
  );
  ring.rotation.x = Math.PI / 2;
  ring.position.y = -1.9;
  scene.add(ring);

  const layerDefinitions = [
    { name: 'Unity Catalog', color: 0x00A972, size: [7.0, 0.8, 7.0], y: -1.2, explode: [-2.1, -1.2, 1.0] },
    { name: 'Delta & Lakehouse', color: 0x12B5CB, size: [6.3, 0.72, 6.3], y: -0.15, explode: [2.2, -0.05, -0.9] },
    { name: 'Lakeflow Jobs', color: 0x2962FF, size: [5.4, 0.72, 5.4], y: 0.9, explode: [-2.6, 1.2, -1.4] },
    { name: 'Lakeflow Pipelines', color: 0x7C4DFF, size: [4.5, 0.72, 4.5], y: 1.95, explode: [2.8, 2.25, 1.2] },
    { name: 'SQL, BI & Genie', color: 0xFF6F42, size: [3.6, 0.72, 3.6], y: 3.0, explode: [-1.8, 3.35, 2.1] },
    { name: 'AI Apps & ML', color: 0xFF3621, size: [2.7, 0.72, 2.7], y: 4.05, explode: [2.1, 4.4, -2.0] }
  ];

  const interactiveMeshes = [];
  let hoveredMesh = null;
  let exploded = false;

  layerDefinitions.forEach((layer, index) => {
    const group = new THREE.Group();
    const geometry = new THREE.BoxGeometry(...layer.size);
    const material = new THREE.MeshStandardMaterial({
      color: layer.color,
      transparent: true,
      opacity: 0.94,
      metalness: 0.18,
      roughness: 0.38,
      emissive: 0x000000
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.userData.basePosition = new THREE.Vector3(0, layer.y, 0);
    mesh.userData.explodedPosition = new THREE.Vector3(...layer.explode);
    mesh.userData.label = layer.name;
    group.add(mesh);

    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.24 })
    );
    mesh.add(edges);

    const sprite = createLabelSprite(layer.name);
    sprite.position.set(0, layer.size[1] / 2 + 0.65, 0);
    sprite.scale.set(3.6, 0.9, 1);
    mesh.add(sprite);

    const pulse = new THREE.Mesh(
      new THREE.RingGeometry(0.32, 0.38, 32),
      new THREE.MeshBasicMaterial({ color: layer.color, transparent: true, opacity: 0.8, side: THREE.DoubleSide })
    );
    pulse.rotation.x = -Math.PI / 2;
    pulse.position.set(0, layer.size[1] / 2 + 0.02, 0);
    mesh.add(pulse);
    mesh.userData.pulse = pulse;
    mesh.userData.floatOffset = index * 0.55;

    scene.add(group);
    interactiveMeshes.push(mesh);
  });

  for (let i = 0; i < 10; i += 1) {
    const node = new THREE.Mesh(
      new THREE.SphereGeometry(0.08, 16, 16),
      new THREE.MeshBasicMaterial({ color: i % 2 === 0 ? 0xff3621 : 0x00A972, transparent: true, opacity: 0.9 })
    );
    const angle = (i / 10) * Math.PI * 2;
    node.position.set(Math.cos(angle) * 5.2, -1.86, Math.sin(angle) * 5.2);
    scene.add(node);
  }

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function handlePointerMove(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  renderer.domElement.addEventListener('pointermove', handlePointerMove);
  renderer.domElement.addEventListener('click', () => {
    exploded = !exploded;
  });

  function resizeRenderer() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  window.addEventListener('resize', resizeRenderer);

  function animate(time) {
    const t = time * 0.001;
    controls.update();
    ring.rotation.z += 0.002;

    raycaster.setFromCamera(pointer, camera);
    const intersections = raycaster.intersectObjects(interactiveMeshes);
    const nextHovered = intersections.length ? intersections[0].object : null;

    if (hoveredMesh !== nextHovered) {
      if (hoveredMesh) hoveredMesh.material.emissive.setHex(0x000000);
      hoveredMesh = nextHovered;
      if (hoveredMesh) hoveredMesh.material.emissive.setHex(0x2a2a2a);
    }

    interactiveMeshes.forEach(mesh => {
      const target = exploded ? mesh.userData.explodedPosition : mesh.userData.basePosition;
      mesh.position.lerp(target, 0.08);
      mesh.rotation.y += ((hoveredMesh === mesh ? 0.12 : 0.0) - mesh.rotation.y) * 0.08;
      mesh.position.y += Math.sin(t + mesh.userData.floatOffset) * 0.004;
      if (mesh.userData.pulse) {
        const scale = 1 + (Math.sin(t * 2 + mesh.userData.floatOffset) * 0.08);
        mesh.userData.pulse.scale.set(scale, scale, scale);
        mesh.userData.pulse.material.opacity = 0.45 + ((Math.sin(t * 2 + mesh.userData.floatOffset) + 1) * 0.12);
      }
    });

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}

function createLabelSprite(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = 'rgba(13, 17, 23, 0.82)';
  roundRect(ctx, 12, 16, 488, 96, 18);
  ctx.fill();
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
  ctx.lineWidth = 2;
  roundRect(ctx, 12, 16, 488, 96, 18);
  ctx.stroke();

  ctx.font = '600 36px DM Sans';
  ctx.fillStyle = '#E6EDF3';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 256, 64);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
  return new THREE.Sprite(material);
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}
