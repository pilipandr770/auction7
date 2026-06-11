// ════════════════════════════════════════════════════════════
//  DropBid — frontend interactions
// ════════════════════════════════════════════════════════════

// MetaMask wallet connect
async function connectWallet() {
    if (window.ethereum) {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            const response = await fetch('/user/connect_wallet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `wallet_address=${accounts[0]}`
            });
            response.ok ? window.location.reload() : alert('Wallet konnte nicht verbunden werden.');
        } catch (err) {
            alert('MetaMask-Verbindung abgebrochen oder ein Fehler ist aufgetreten.');
        }
    } else {
        alert('MetaMask ist nicht installiert!');
    }
}

document.addEventListener('DOMContentLoaded', function () {

    // Copy wallet address
    const walletShort = document.getElementById('wallet-address-short');
    if (walletShort) {
        walletShort.addEventListener('click', function () {
            const full = walletShort.getAttribute('data-full') || walletShort.textContent.trim();
            navigator.clipboard.writeText(full).then(() => {
                const status = document.getElementById('wallet-copy-status');
                if (status) {
                    status.style.display = 'inline';
                    setTimeout(() => { status.style.display = 'none'; }, 1500);
                }
            });
        });
    }

    // Real-time auction status (SSE)
    initStreams();

    // Open auction modal on card click
    document.querySelectorAll('[data-auction-toggle]').forEach(function (card) {
        card.addEventListener('click', function () {
            const id = card.getAttribute('data-auction-toggle');
            const modalEl = document.getElementById('auctionModal-' + id);
            if (modalEl && window.bootstrap) {
                new bootstrap.Modal(modalEl).show();
            }
        });
    });

    // ── Participate (POST → JSON) ────────────────────────────
    document.querySelectorAll('.db-participate-btn').forEach(function (btn) {
        btn.addEventListener('click', async function (e) {
            e.preventDefault();
            const url = btn.getAttribute('data-url');
            const id = btn.getAttribute('data-auction-id');
            const original = btn.textContent;
            btn.disabled = true;
            btn.textContent = '⏳ Wird verarbeitet...';
            try {
                const resp = await fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await resp.json();
                if (data.error) {
                    btn.textContent = original;
                    btn.disabled = false;
                    showResult(btn, 'error', data.error);
                } else {
                    btn.outerHTML = '<div class="db-joined-badge">✓ Sie nehmen an der Auktion teil</div>';
                    // Eintritt zeigt — wie der Kauf der Preis-Einsicht — Preis & Teilnehmer für 5 Sekunden
                    const priceEl = document.getElementById('reveal-price-' + id);
                    if (priceEl) {
                        priceEl.textContent = (data.final_price ?? '?') + ' €';
                        document.getElementById('reveal-part-' + id).textContent = data.participants ?? '?';
                        startReveal(id);
                    }
                }
            } catch (err) {
                btn.textContent = original;
                btn.disabled = false;
                showResult(btn, 'error', 'Ein Fehler ist aufgetreten. Bitte erneut versuchen.');
            }
        });
    });

    // ── Reveal price (POST → JSON) + 5-second countdown ──────
    document.querySelectorAll('.db-reveal-btn').forEach(function (btn) {
        btn.addEventListener('click', async function (e) {
            e.preventDefault();
            const id = btn.getAttribute('data-auction-id');
            const url = btn.getAttribute('data-url');
            const errBox = document.getElementById('reveal-error-' + id);
            errBox.style.display = 'none';
            btn.disabled = true;
            const original = btn.textContent;
            btn.textContent = '⏳...';
            try {
                const resp = await fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await resp.json();
                if (data.error) {
                    btn.disabled = false;
                    btn.textContent = original;
                    errBox.innerHTML = `<div class="db-alert db-alert-error">${data.error}</div>`;
                    errBox.style.display = 'block';
                } else {
                    document.getElementById('reveal-price-' + id).textContent = (data.final_price ?? '?') + ' €';
                    document.getElementById('reveal-part-' + id).textContent = data.participants ?? '?';
                    startReveal(id);
                }
            } catch (err) {
                btn.disabled = false;
                btn.textContent = original;
                errBox.innerHTML = `<div class="db-alert db-alert-error">Ein Fehler ist aufgetreten. Bitte erneut versuchen.</div>`;
                errBox.style.display = 'block';
            }
        });
    });
});

function startReveal(id) {
    const idle = document.getElementById('reveal-idle-' + id);
    const dataPanel = document.getElementById('reveal-data-' + id);
    const done = document.getElementById('reveal-done-' + id);
    const numEl = document.getElementById('countdown-' + id);
    const bar = document.getElementById('progress-' + id);

    idle.style.display = 'none';
    done.style.display = 'none';
    dataPanel.style.display = 'block';

    let sec = 5;
    numEl.textContent = sec;
    bar.style.transition = 'none';
    bar.style.width = '100%';
    // force reflow then enable smooth transition
    void bar.offsetWidth;
    bar.style.transition = 'width 1s linear';

    const timer = setInterval(() => {
        sec--;
        numEl.textContent = sec;
        bar.style.width = ((sec / 5) * 100) + '%';
        if (sec <= 0) {
            clearInterval(timer);
            dataPanel.style.display = 'none';
            done.style.display = 'block';
        }
    }, 1000);
}

// ── Real-time auction status via SSE ─────────────────────────
const _streams = {};

function renderLiveStatus(id, data) {
    const el = document.getElementById('live-status-' + id);
    if (!el) return;
    el.className = 'db-live-status show';
    if (!data.exists || data.is_active === false) {
        el.classList.add('db-live-closed');
        el.innerHTML = '🔒 Auktion beendet';
        // disable action buttons in this scope
        const scope = el.closest('.modal-content') || el.closest('[data-stream-page]') || document;
        scope.querySelectorAll('.db-participate-btn, .db-reveal-btn').forEach(b => b.disabled = true);
        scope.querySelectorAll('form[action*="close_auction"] button').forEach(b => b.disabled = true);
    } else if (data.frozen) {
        el.classList.add('db-live-frozen');
        el.innerHTML = '<span class="db-live-dot amber"></span>🔒 Einstiege eingefroren · ' + data.seconds_left + ' Sek';
    } else {
        el.classList.add('db-live-active');
        el.innerHTML = '<span class="db-live-dot green"></span>Auktion aktiv · Einstiege offen';
    }
}

function connectStream(id) {
    if (_streams[id]) return;
    if (typeof EventSource === 'undefined') return;
    const es = new EventSource('/auction/' + id + '/stream');
    es.onmessage = function (e) {
        try { renderLiveStatus(id, JSON.parse(e.data)); } catch (err) {}
    };
    es.onerror = function () { /* Browser verbindet automatisch neu */ };
    _streams[id] = es;
}

function disconnectStream(id) {
    if (_streams[id]) { _streams[id].close(); delete _streams[id]; }
}

function initStreams() {
    // Detail page: auto-connect
    document.querySelectorAll('[data-stream-page]').forEach(el => {
        connectStream(el.getAttribute('data-stream-page'));
    });
    // Modals: connect on show, disconnect on hide
    document.querySelectorAll('[data-stream-auction]').forEach(modal => {
        const id = modal.getAttribute('data-stream-auction');
        modal.addEventListener('shown.bs.modal', () => connectStream(id));
        modal.addEventListener('hidden.bs.modal', () => disconnectStream(id));
    });
}

// DSA Notice-and-Action — Inserat melden
async function reportAuction(id) {
    const reason = prompt('Warum möchten Sie dieses Inserat melden? (z. B. verbotener Artikel, Betrug)');
    if (!reason) return;
    try {
        const r = await fetch('/auction/' + id + '/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: reason })
        });
        const d = await r.json();
        alert(d.message || d.error || 'Meldung verarbeitet.');
    } catch (e) {
        alert('Meldung fehlgeschlagen. Bitte später erneut versuchen.');
    }
}

function showResult(btn, type, msg) {
    const div = document.createElement('div');
    div.className = 'db-alert db-alert-' + type;
    div.style.marginTop = '8px';
    div.textContent = msg;
    btn.parentNode.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}
