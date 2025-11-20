// --------------------- Login Logic ---------------------
    let p = "";

    function k(n) {
        // Only run if keypad display exists
        if (!document.getElementById('d1')) return;
        
        if (p.length < 4) {
            p += n;
            u();
            if (p.length === 4) c();
        }
    }

    function clr() {
        if (!document.getElementById('d1')) return;
        p = "";
        u();
    }

    function u() {
        for (let i = 1; i <= 4; i++) {
            let dot = document.getElementById('d' + i);
            if (dot) dot.className = i <= p.length ? 'dot active' : 'dot';
        }
    }

    async function c() {
        try {
            let r = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pin: p })
            });
            let d = await r.json();
            if (d.success) {
                location.reload();
            } else {
                document.querySelectorAll('.dot').forEach(e => e.classList.add('err'));
                setTimeout(() => {
                    document.querySelectorAll('.dot').forEach(e => e.classList.remove('err'));
                    clr();
                }, 400);
            }
        } catch (e) {
            clr();
        }
    }

    document.addEventListener('keydown', e => {
        if (!document.getElementById('d1')) return;
        if (e.key >= '0' && e.key <= '9') k(e.key);
        else if (e.key === 'Backspace') clr();
    });

    // --------------------- Dashboard Logic ---------------------

    // Added 'lastEdit' to track state changes
    let st = [], edit = false, lastEdit = null, eId = -1, eCol = '';
    const COLS = ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#10b981', '#06b6d4', '#3b82f6', '#6366f1', '#d946ef', '#ffffff', '#000000'];

    const IC_MIC = '<svg class="icon-xl" viewBox="0 0 352 512"><path d="M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.65 63.97 169.6 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z" fill="currentColor"/></svg>';
    const IC_PEN = '<svg class="icon" style="width:14px; height:14px;" viewBox="0 0 512 512"><path d="M290.74 93.24l128.02 128.02-277.99 277.99-114.14 12.6C11.35 513.54-1.56 500.62.14 485.34l12.7-114.22 277.9-277.88zm207.2-19.06l-60.11-60.11c-18.75-18.75-49.16-18.75-67.91 0l-56.55 56.55 128.02 128.02 56.55-56.55c18.75-18.76 18.75-49.16 0-67.91z" fill="currentColor"/></svg>';

    // --------------------- Init ---------------------

    if (document.getElementById('list')) {
        (async () => {
            let r = await fetch('/api/status?t=' + Date.now());
            if (r.status === 401) location.reload();

            let d = await r.json();

            if (!d.hardware) {
                if(document.getElementById('demo')) document.getElementById('demo').style.display = 'block';
                if(document.getElementById('blueprint')) document.getElementById('blueprint').style.display = 'block';
            }

            draw(d.channels);
            updateConn(true);

            let pal = document.getElementById('pal');
            COLS.forEach(c => {
                let d = document.createElement('div');
                d.className = 'swatch';
                d.style.background = c;
                if (c === '#000000') d.style.border = '1px solid #334155';
                d.onclick = () => {
                    eCol = c;
                    document.querySelectorAll('.swatch').forEach(x => x.classList.remove('sel'));
                    d.classList.add('sel');
                };
                pal.appendChild(d);
            });

            setInterval(poll, 2000);
        })();
    }

    // --------------------- Functions ---------------------

    async function poll() {
        try {
            let r = await fetch('/api/status?t=' + Date.now());
            if (r.status === 401) location.reload();

            let d = await r.json();
            // Remove the !edit check here, let draw() handle the optimization
            draw(d.channels);
            updateConn(true);
        } catch (e) {
            updateConn(false);
        }
    }

    function updateConn(ok) {
        let el = document.getElementById('status-dot');
        if(el) el.className = 'conn-dot ' + (ok ? 'online' : 'offline');
    }

    function draw(chs) {
        // FIX: Check if data matches AND if edit mode is same as last time
        if (JSON.stringify(chs) === JSON.stringify(st) && edit === lastEdit) return;
        
        st = chs;
        lastEdit = edit; // Update the tracker

        let h = '';
        chs.forEach(c => {
            let col = c.color || '#3b82f6';
            let on = c.active;
            let bc = on ? col : '#334155';
            let glow = on ? `box-shadow:0 0 15px ${col}40` : '';
            let actC = on ? '#10b981' : '#ef4444';
            let actT = on ? 'LIVE' : 'MUTED';
            let tr = on ? 'transform:translateX(20px)' : '';
            let tb = on ? '#10b981' : '#334155';
            let iconBg = on ? `color:${col}; border-color:${col}; background:${col}15` : `color:#64748b; border-color:#475569`;
            let safeName = c.name.replace(/'/g, "\\\\'");

            let w = document.getElementById('wire-' + c.id);
            if (w) {
                w.style.stroke = on ? col : '#334155';
                if (on) w.classList.add('active'); else w.classList.remove('active');
            }

            h += `<div class="card" style="border-color:${edit ? '#475569' : bc}; ${edit ? '' : glow}" onclick="${edit ? `openModal(${c.id}, '${safeName}', '${col}')` : `toggle(${c.id})`}">
                    <div class="edit-overlay-icon">${IC_PEN}</div>
                    <div class="card-left">
                        <div class="icon-box" style="${iconBg}">${IC_MIC}</div>
                        <div>
                            <div style="font-weight:bold; font-size:1.1rem;">${c.name}</div>
                            <div class="status" style="color:${actC}">
                                <div class="status-dot" style="background:${actC}"></div>${actT}
                            </div>
                        </div>
                    </div>
                    <div class="toggle" style="background:${tb}"><div class="thumb" style="${tr}"></div></div>
                    <div class="color-bar" style="background:${col}; ${on ? 'opacity:1; box-shadow:0 0 10px ' + col : ''}"></div>
                </div>`;
        });

        let list = document.getElementById('list');
        if(list) list.innerHTML = h;
    }

    async function toggle(id) {
        if (edit) return;
        let t = JSON.parse(JSON.stringify(st));
        let i = t.findIndex(x => x.id === id);
        if (i >= 0) {
            t[i].active = !t[i].active;
            draw(t);
        }
        await fetch('/api/toggle/' + id, { method: 'POST' });
        poll();
    }

    async function allCh(a) {
        if (edit) return;
        let s = a === 'unmute';
        let t = JSON.parse(JSON.stringify(st));
        t.forEach(x => x.active = s);
        draw(t);
        await fetch('/api/all/' + a, { method: 'POST' });
        poll();
    }

    function toggleEdit() {
        edit = !edit;
        document.body.className = edit ? 'edit' : '';
        draw(st);
    }

    function openModal(id, n, c) {
        eId = id;
        eCol = c;
        document.getElementById('e-name').value = n;
        document.querySelectorAll('.swatch').forEach(x => {
            if (x.style.background.includes(c)) x.classList.add('sel'); else x.classList.remove('sel');
        });
        document.getElementById('modal').className = 'modal open';
    }

    function closeModal() {
        document.getElementById('modal').className = 'modal';
    }

    async function save() {
        let n = document.getElementById('e-name').value;
        if (n) {
            await fetch('/api/update/' + eId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: n, color: eCol })
            });
            poll();
            closeModal();
        }
    }