/* ============================================================
   KINDRED — Main JavaScript
   ============================================================ */

// ── CSRF token (read from meta tag, attached to all POST fetches) ─────────
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';

/**
 * Secure fetch wrapper — automatically attaches CSRF token to POST requests.
 * Use this instead of raw fetch() for all API calls.
 */
async function apiFetch(url, options = {}) {
  const isPost = (options.method || 'GET').toUpperCase() === 'POST';
  const headers = { ...(options.headers || {}) };

  if (isPost) {
    if (options.body instanceof FormData) {
      // FormData: append CSRF as a field
      options.body.append('_csrf_token', CSRF_TOKEN);
    } else if (typeof options.body === 'string') {
      // JSON body: add as header
      headers['X-CSRF-Token'] = CSRF_TOKEN;
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }
  }

  return fetch(url, { ...options, headers });
}

// ── AOS init ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (typeof AOS !== 'undefined') {
    AOS.init({ duration: 700, easing: 'ease-out-cubic', once: true, offset: 60 });
  }
  initFlashMessages();
  initNavHighlight();
  initHobbySelection();
});

/* ── Flash message auto-dismiss ──────────────────────────────────────────── */
function initFlashMessages() {
  document.querySelectorAll('.flash-message').forEach((flash, i) => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transform = 'translateX(20px)';
      flash.style.transition = 'all 0.4s ease';
      setTimeout(() => flash.remove(), 400);
    }, 4000 + i * 500);
  });
}

/* ── Toast notification ───────────────────────────────────────────────────── */
function showToast(message, type = 'info') {
  document.querySelector('.kindred-toast')?.remove();

  const icons = { success: 'bi-check-circle', error: 'bi-exclamation-circle', info: 'bi-info-circle' };
  const toast = document.createElement('div');
  toast.className = `kindred-toast toast-${type}`;
  toast.innerHTML = `<i class="bi ${icons[type] || icons.info}"></i> ${escapeHtml(message)}`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.4s ease';
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

/* ── XSS-safe HTML escape ─────────────────────────────────────────────────── */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(String(text)));
  return div.innerHTML;
}

/* ── Nav scroll highlight ─────────────────────────────────────────────────── */
function initNavHighlight() {
  const nav = document.getElementById('mainNav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 20 ? '0 2px 20px rgba(0,0,0,0.3)' : 'none';
  }, { passive: true });
}

/* ── Hobby card selection (profile build step 3) ──────────────────────────── */
function initHobbySelection() {
  const checkboxes = document.querySelectorAll('.hobby-checkbox');
  if (!checkboxes.length) return;

  const submitBtn = document.getElementById('hobbiesSubmit');
  const countEl   = document.getElementById('selectedCount');

  const updateState = () => {
    const n = document.querySelectorAll('.hobby-checkbox:checked').length;
    if (countEl) countEl.textContent = n;
    if (submitBtn) {
      submitBtn.disabled    = n < 2;
      submitBtn.style.opacity = n < 2 ? '0.5' : '1';
    }
  };

  checkboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      cb.closest('.hobby-card').classList.toggle('selected', cb.checked);
      updateState();
    });
  });

  updateState(); // init state
}

/* ── Keyboard: ESC closes modals ──────────────────────────────────────────── */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.match-modal-overlay.active, .modal-overlay.active')
      .forEach(el => el.classList.remove('active'));
  }
});

/* ── Discover page: like profile ─────────────────────────────────────────── */
async function likeProfile(userId, btn) {
  const remaining = parseInt(document.getElementById('likesCount')?.textContent || '0');
  if (remaining <= 0) {
    showToast("You've used all your likes for today. Come back tomorrow! 💫", 'info');
    return;
  }

  btn.classList.add('liked');
  btn.disabled = true;

  try {
    const fd = new FormData();
    // apiFetch will append _csrf_token to fd automatically
    const res  = await apiFetch(`/like/${userId}`, { method: 'POST', body: fd });
    const data = await res.json();

    if (data.success) {
      const countEl = document.getElementById('likesCount');
      if (countEl) countEl.textContent = data.remaining_likes;

      if (data.is_match) {
        const matchChatBtn = document.getElementById('matchChatBtn');
        if (matchChatBtn && data.match_id) matchChatBtn.href = `/chat/${data.match_id}`;
        document.getElementById('matchModal')?.classList.add('active');
      } else {
        showToast('Liked! ♥', 'success');
        const card = btn.closest('.profile-card');
        if (card) {
          setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity    = '0';
            card.style.transform  = 'scale(0.95)';
            setTimeout(() => card.remove(), 400);
          }, 500);
        }
      }
    } else {
      btn.classList.remove('liked');
      btn.disabled = false;
      showToast(data.message || 'Something went wrong.', 'error');
    }
  } catch {
    btn.classList.remove('liked');
    btn.disabled = false;
    showToast('Network error. Please try again.', 'error');
  }
}

function closeMatchModal() {
  document.getElementById('matchModal')?.classList.remove('active');
}

/* ── Profile view: like ───────────────────────────────────────────────────── */
async function likeProfilePage(userId, btn) {
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-heart-fill"></i> Liking...';

  try {
    const fd = new FormData();
    const res  = await apiFetch(`/like/${userId}`, { method: 'POST', body: fd });
    const data = await res.json();

    if (data.success) {
      if (data.is_match) {
        showToast("It's a match! 💫 Check your Matches.", 'success');
        btn.innerHTML  = '<i class="bi bi-heart-fill"></i> Matched! ✦';
        btn.className  = 'btn-profile-liked';
      } else {
        btn.innerHTML = '<i class="bi bi-heart-fill"></i> Liked!';
        btn.className = 'btn-profile-liked';
      }
    } else {
      btn.disabled  = false;
      btn.innerHTML = '<i class="bi bi-heart"></i> Like this profile';
      showToast(data.message || 'Something went wrong.', 'error');
    }
  } catch {
    btn.disabled  = false;
    btn.innerHTML = '<i class="bi bi-heart"></i> Like this profile';
    showToast('Network error.', 'error');
  }
}

/* ── Modal overlay click-outside to close ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('active');
    });
  });
});
