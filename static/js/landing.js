/* ============================================================
   KINDRED — Landing Page JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initLandingNav();
  initHeroParallax();
  initCardTilt();
  initCounterAnimation();
});

/* ============================================================
   NAV SCROLL BEHAVIOR
   ============================================================ */
function initLandingNav() {
  const nav = document.getElementById('landingNav');
  if (!nav) return;

  const onScroll = () => {
    if (window.scrollY > 40) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Smooth anchor scrolling
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

/* ============================================================
   HERO PARALLAX
   ============================================================ */
function initHeroParallax() {
  const hero = document.querySelector('.hero-section');
  if (!hero) return;

  window.addEventListener('mousemove', (e) => {
    const { clientX, clientY } = e;
    const { innerWidth, innerHeight } = window;
    const xPct = (clientX / innerWidth - 0.5) * 2;
    const yPct = (clientY / innerHeight - 0.5) * 2;

    const orbs = document.querySelectorAll('.ambient-orb');
    orbs.forEach((orb, i) => {
      const factor = (i + 1) * 12;
      orb.style.transform = `translate(${xPct * factor}px, ${yPct * factor}px)`;
    });

    const cards = document.querySelectorAll('.preview-card');
    cards.forEach((card, i) => {
      const factor = (i + 1) * 6;
      const baseAnim = card.style.animationName;
      card.style.transform = `translateY(${yPct * factor}px) translateX(${xPct * factor * 0.5}px)`;
    });
  });
}

/* ============================================================
   CARD TILT EFFECT (hero preview cards)
   ============================================================ */
function initCardTilt() {
  const cards = document.querySelectorAll('.preview-card');

  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -8;
      const rotateY = ((x - centerX) / centerX) * 8;

      card.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px)`;
      card.style.transition = 'transform 0.1s ease';
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
      card.style.transition = 'transform 0.6s ease';
    });
  });
}

/* ============================================================
   COUNTER ANIMATION (hero stats)
   ============================================================ */
function initCounterAnimation() {
  const statNums = document.querySelectorAll('.stat-num');
  if (!statNums.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const text = el.textContent.trim();

        // Only animate pure numbers
        if (/^\d+$/.test(text)) {
          const target = parseInt(text);
          animateCounter(el, 0, target, 1200);
        }
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  statNums.forEach(el => observer.observe(el));
}

function animateCounter(el, start, end, duration) {
  const startTime = performance.now();

  const tick = (now) => {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (end - start) * eased);
    el.textContent = current;

    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      el.textContent = end;
    }
  };

  requestAnimationFrame(tick);
}

/* ============================================================
   FEATURE MOCKUP — LIKES DOTS ANIMATION
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const dots = document.querySelectorAll('.fm-dot');
  if (!dots.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        dots.forEach((dot, i) => {
          setTimeout(() => {
            if (dot.classList.contains('filled')) {
              dot.style.transform = 'scale(1.3)';
              setTimeout(() => dot.style.transform = '', 200);
            }
          }, i * 60);
        });
        observer.disconnect();
      }
    });
  }, { threshold: 0.5 });

  const container = document.querySelector('.fm-likes-dots');
  if (container) observer.observe(container);
});
