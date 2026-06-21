/**
 * PerteDocsTG — JavaScript Principal
 */
'use strict';

// ── Toast JS ─────────────────────────────────────────────────────────────────
const Toast = {
  container: null,
  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'fixed top-4 right-4 z-50 space-y-3 pointer-events-none max-w-sm w-full';
      document.body.appendChild(this.container);
    }
  },
  show(message, type = 'info', duration = 5000) {
    if (!this.container) this.init();
    const classes = {
      success: 'toast-success', error: 'toast-error',
      warning: 'toast-warning', info: 'toast-info'
    };
    const icons = {
      success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
      error:   '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
      warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.072 16.5c-.77.833.192 2.5 1.732 2.5z"/>',
      info:    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
    };
    const toast = document.createElement('div');
    toast.className = `${classes[type] || classes.info} pointer-events-auto`;
    toast.style.animation = 'slideInRight .3s ease-out';
    toast.innerHTML = `
      <div class="flex items-start gap-3">
        <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">${icons[type] || icons.info}</svg>
        <p class="text-sm font-medium flex-1">${message}</p>
        <button onclick="this.closest('.pointer-events-auto').remove()" class="opacity-60 hover:opacity-100">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>`;
    this.container.appendChild(toast);
    setTimeout(() => { toast.style.opacity='0'; toast.style.transform='translateX(100%)'; toast.style.transition='all .3s ease'; setTimeout(()=>toast.remove(), 300); }, duration);
  },
  success(m) { this.show(m, 'success'); },
  error(m)   { this.show(m, 'error'); },
  warning(m) { this.show(m, 'warning'); },
  info(m)    { this.show(m, 'info'); },
};

// ── CSRF ─────────────────────────────────────────────────────────────────────
function getCsrfToken() {
  const c = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  return c ? c.split('=')[1].trim() : '';
}

// ── Recherche AJAX instantanée ────────────────────────────────────────────────
class InstantSearch {
  constructor(inputSel, resultsSel, url) {
    this.input = document.querySelector(inputSel);
    this.results = document.querySelector(resultsSel);
    this.url = url;
    this.timer = null;
    if (this.input) this._bind();
  }
  _bind() {
    this.input.addEventListener('input', () => {
      clearTimeout(this.timer);
      const q = this.input.value.trim();
      if (q.length < 2) { this._hide(); return; }
      this.timer = setTimeout(() => this._search(q), 280);
    });
    document.addEventListener('click', e => {
      if (!this.results?.contains(e.target) && e.target !== this.input) this._hide();
    });
  }
  async _search(q) {
    try {
      const r = await fetch(`${this.url}?q=${encodeURIComponent(q)}`);
      const d = await r.json();
      this._render(d.results || []);
    } catch(e) { console.error('Search error:', e); }
  }
  _render(results) {
    if (!this.results) return;
    const statusClass = s => s === 'validated' ? 'badge-validated' : s === 'rejected' ? 'badge-rejected' : 'badge-submitted';
    this.results.innerHTML = results.length
      ? results.map(r => `<a href="${r.url}" class="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-b border-gray-50 dark:border-gray-700 last:border-0">
          <div class="flex-1 min-w-0">
            <p class="text-sm font-bold text-gray-900 dark:text-white truncate">${r.name}</p>
            <p class="text-xs text-gray-400">${r.number} · ${r.document_type}</p>
          </div>
          <span class="badge ${statusClass(r.status)} text-xs">${r.status_label}</span>
        </a>`).join('')
      : '<p class="px-4 py-4 text-sm text-gray-400 text-center">Aucun résultat</p>';
    this.results.classList.remove('hidden');
  }
  _hide() { this.results?.classList.add('hidden'); }
}

// ── Charts Dashboard ──────────────────────────────────────────────────────────
function initCharts() {
  const monthlyEl = document.getElementById('monthly-chart');
  if (monthlyEl) {
    const data = JSON.parse(monthlyEl.dataset.chartData || '{}');
    new Chart(monthlyEl, {
      type: 'line', data,
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position:'bottom', labels:{ usePointStyle:true, padding:16 } }, tooltip:{ mode:'index', intersect:false } },
        scales: {
          x: { grid:{ display:false }, border:{ display:false } },
          y: { grid:{ color:'rgba(0,0,0,0.04)' }, border:{ display:false }, ticks:{ precision:0 } }
        }
      }
    });
  }
  const doctypeEl = document.getElementById('doctype-chart');
  if (doctypeEl) {
    const data = JSON.parse(doctypeEl.dataset.chartData || '{}');
    new Chart(doctypeEl, {
      type: 'doughnut',
      data: { labels: data.labels||[], datasets:[{ data:data.data||[], backgroundColor:data.colors||[], borderWidth:3, borderColor:'#fff' }] },
      options: {
        responsive:true, maintainAspectRatio:false, cutout:'62%',
        plugins:{ legend:{ position:'right', labels:{ usePointStyle:true, padding:12, font:{size:11} } } }
      }
    });
  }
}

// ── File Upload Preview ───────────────────────────────────────────────────────
function initFileUpload() {
  document.querySelectorAll('.file-upload-zone').forEach(zone => {
    const input = zone.querySelector('input[type="file"]');
    const preview = zone.querySelector('.file-preview');
    if (!input) return;
    ['dragover','dragenter'].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.style.borderColor='#006B3F'; zone.style.background='rgba(0,107,63,0.03)'; }));
    ['dragleave','drop'].forEach(ev => zone.addEventListener(ev, e => { zone.style.borderColor=''; zone.style.background=''; }));
    zone.addEventListener('drop', e => { e.preventDefault(); if(e.dataTransfer.files.length) { input.files = e.dataTransfer.files; showPreview(input, preview); } });
    input.addEventListener('change', () => showPreview(input, preview));
  });
}
function showPreview(input, preview) {
  if (!preview || !input.files.length) return;
  const f = input.files[0];
  const mb = (f.size/1024/1024).toFixed(2);
  preview.innerHTML = `
    <div class="flex items-center gap-3 p-3 bg-togo-green/5 rounded-xl border border-togo-green/20 mt-2">
      <svg class="w-8 h-8 text-togo-green" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
      <div class="flex-1 min-w-0"><p class="text-sm font-semibold text-gray-900 dark:text-white truncate">${f.name}</p><p class="text-xs text-gray-400">${mb} Mo</p></div>
      <button type="button" onclick="this.closest('.file-preview').innerHTML='';this.closest('.file-upload-zone').querySelector('input').value=''" class="text-gray-400 hover:text-red-500 transition-colors">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>`;
}

// ── Dark mode persistence ─────────────────────────────────────────────────────
document.addEventListener('alpine:init', () => {
  window.addEventListener('toggle-dark', async e => {
    try {
      await fetch('/accounts/preferences/', {
        method:'POST',
        headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},
        body: JSON.stringify({dark_mode: e.detail})
      });
    } catch(e2) {}
  });
});

// ── Initialisation ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  initCharts();
  initFileUpload();

  // Recherche instantanée
  if (document.getElementById('global-search')) {
    new InstantSearch('#global-search','#search-results','/declarations/ajax/search/');
  }

  // Confirmation avant actions dangereuses
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => { if (!confirm(el.dataset.confirm)) e.preventDefault(); });
  });

  // Chargement des préfectures via AJAX
  const regionSelect = document.getElementById('region-select');
  if (regionSelect) {
    regionSelect.addEventListener('change', async function() {
      const resp = await fetch(`/declarations/ajax/prefectures/?region_id=${this.value}`);
      const data = await resp.json();
      const prefSelect = document.getElementById('prefecture-select');
      if (prefSelect) {
        prefSelect.innerHTML = '<option value="">— Sélectionner une préfecture —</option>' +
          (data.prefectures || []).map(p => `<option value="${p.id}">${p.name}</option>`).join('');
      }
    });
  }
});
