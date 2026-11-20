/* ============================================================
   틀린그림찾기 — 게임 로직 (외부 라이브러리 없음)
   ============================================================ */
(function () {
  'use strict';

  var RECORD_KEY = 'spotdiff.records.v2';
  var SOUND_KEY = 'spotdiff.sound.v1';
  var DIFF_LABEL = { 1: '쉬움', 2: '보통', 3: '어려움' };

  var $ = function (id) { return document.getElementById(id); };

  /* ---------------- 저장소 ---------------- */
  function loadRecords() {
    try { return JSON.parse(localStorage.getItem(RECORD_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function saveRecords(r) {
    try { localStorage.setItem(RECORD_KEY, JSON.stringify(r)); } catch (e) {}
  }

  /* ---------------- 효과음 (Web Audio 자체 합성) ---------------- */
  var Sfx = (function () {
    var ctx = null;
    var master = null;
    var enabled = true;

    function ensure() {
      if (ctx) {
        if (ctx.state === 'suspended') { ctx.resume(); }
        return ctx;
      }
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { return null; }
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = 0.5;
      master.connect(ctx.destination);
      return ctx;
    }

    function tone(freq, dur, type, gain, delay, sweepTo) {
      if (!enabled) { return; }
      var c = ensure();
      if (!c) { return; }
      var t0 = c.currentTime + (delay || 0);
      var osc = c.createOscillator();
      var g = c.createGain();
      osc.type = type || 'sine';
      osc.frequency.setValueAtTime(freq, t0);
      if (sweepTo) { osc.frequency.exponentialRampToValueAtTime(sweepTo, t0 + dur); }
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(gain || 0.25, t0 + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(g); g.connect(master);
      osc.start(t0); osc.stop(t0 + dur + 0.02);
    }

    function noise(dur, gain) {
      if (!enabled) { return; }
      var c = ensure();
      if (!c) { return; }
      var len = Math.floor(c.sampleRate * dur);
      var buf = c.createBuffer(1, len, c.sampleRate);
      var data = buf.getChannelData(0);
      for (var i = 0; i < len; i++) {
        data[i] = (Math.random() * 2 - 1) * (1 - i / len);
      }
      var src = c.createBufferSource();
      src.buffer = buf;
      var g = c.createGain();
      g.gain.value = gain || 0.12;
      var f = c.createBiquadFilter();
      f.type = 'bandpass'; f.frequency.value = 1800; f.Q.value = 0.8;
      src.connect(f); f.connect(g); g.connect(master);
      src.start();
    }

    return {
      setEnabled: function (v) { enabled = !!v; },
      unlock: function () { ensure(); },
      ding: function () {
        tone(1046.5, 0.16, 'sine', 0.28, 0);
        tone(1568.0, 0.24, 'sine', 0.22, 0.07);
      },
      wrong: function () {
        tone(196, 0.18, 'square', 0.16, 0, 130);
        noise(0.16, 0.08);
      },
      hint: function () {
        tone(880, 0.1, 'triangle', 0.18, 0);
        tone(1174.7, 0.12, 'triangle', 0.14, 0.08);
      },
      tick: function () { tone(1318.5, 0.05, 'square', 0.06, 0); },
      clear: function () {
        var notes = [523.25, 659.25, 783.99, 1046.5];
        for (var i = 0; i < notes.length; i++) {
          tone(notes[i], 0.28, 'triangle', 0.2, i * 0.11);
        }
        tone(1568, 0.5, 'sine', 0.12, 0.46);
      },
      over: function () {
        var notes = [440, 392, 329.6, 261.6];
        for (var i = 0; i < notes.length; i++) {
          tone(notes[i], 0.3, 'sawtooth', 0.1, i * 0.13);
        }
      }
    };
  })();

  function buzz(pattern) {
    if (navigator.vibrate) { try { navigator.vibrate(pattern); } catch (e) {} }
  }

  /* ---------------- 상태 ---------------- */
  var state = {
    records: loadRecords(),
    sound: localStorage.getItem(SOUND_KEY) !== '0',
    idx: 0,
    stage: null,
    found: [],
    wrong: 0,
    hintsLeft: 2,
    hearts: 3,
    timeLeft: 0,
    used: 0,
    running: false,
    timerId: null,
    hintTimer: null,
    lastTick: 0,
    muted: false
  };

  /* ---------------- 공통 UI ---------------- */
  function fmtTime(sec) {
    sec = Math.max(0, Math.round(sec));
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function applySound() {
    Sfx.setEnabled(state.sound);
    var icons = ['soundToggleHome', 'soundToggleGame'];
    icons.forEach(function (id) {
      var el = $(id);
      if (!el) { return; }
      el.textContent = state.sound ? '🔊' : '🔇';
      el.classList.toggle('is-off', !state.sound);
      el.setAttribute('aria-pressed', String(state.sound));
    });
  }

  function toggleSound() {
    state.sound = !state.sound;
    try { localStorage.setItem(SOUND_KEY, state.sound ? '1' : '0'); } catch (e) {}
    applySound();
    if (state.sound) { Sfx.tick(); }
  }

  function totalStars() {
    var sum = 0;
    Object.keys(state.records).forEach(function (k) { sum += state.records[k].stars || 0; });
    return sum;
  }

  /* ---------------- 홈 화면 ---------------- */
  function renderHome() {
    var list = $('stageList');
    var html = '';
    STAGES.forEach(function (st, i) {
      var rec = state.records[st.id];
      var pips = '';
      for (var p = 1; p <= 3; p++) {
        pips += '<i class="pip' + (p <= st.difficulty ? ' on' : '') + '"></i>';
      }
      var stars = '';
      for (var s = 1; s <= 3; s++) {
        stars += '<span class="s' + (rec && s <= rec.stars ? ' on' : '') + '">★</span>';
      }
      html += '' +
        '<button class="stage-card" type="button" data-idx="' + i + '">' +
          '<span class="stage-thumb">' +
            '<img src="' + st.thumb + '" alt="' + st.title + ' 미리보기" loading="lazy">' +
            '<span class="stage-no">' + st.no + '</span>' +
          '</span>' +
          '<span class="stage-info">' +
            '<span class="stage-title">' + st.title + '</span>' +
            '<span class="stage-meta"><span class="pips">' + pips + '</span>' +
              '<span>' + DIFF_LABEL[st.difficulty] + '</span>' +
              '<span>· ' + st.time + '초</span>' +
            '</span>' +
            '<span class="stage-stars">' + stars + '</span>' +
            '<span class="stage-best">' + (rec ? '최고 <b>' + fmtTime(rec.time) + '</b> · 오답 ' + rec.wrong + '회' : '아직 도전 전') + '</span>' +
          '</span>' +
          (rec ? '<span class="clear-ribbon">CLEAR</span>' : '') +
        '</button>';
    });
    list.innerHTML = html;

    var cleared = Object.keys(state.records).length;
    $('statStars').textContent = totalStars();
    $('statCleared').innerHTML = cleared + '<small>/' + STAGES.length + '</small>';

    var best = null;
    Object.keys(state.records).forEach(function (k) {
      var t = state.records[k].time;
      if (best === null || t < best) { best = t; }
    });
    $('statBest').textContent = best === null ? '—' : fmtTime(best);
  }

  function showScreen(which) {
    $('screenHome').classList.toggle('is-active', which === 'home');
    $('screenGame').classList.toggle('is-active', which === 'game');
    window.scrollTo(0, 0);
  }

  /* ---------------- 게임 화면 ---------------- */
  function layoutBoard() {
    var screen = $('screenGame');
    var hud = document.querySelector('.hud-wrap');
    if (!hud) { return; }
    var avail = screen.clientHeight - hud.getBoundingClientRect().height - 26;
    var maxW = Math.min(screen.clientWidth - 16, 540);
    var w = Math.min(maxW, (avail - 8) / 1.5);
    w = Math.max(220, Math.floor(w));
    $('board').style.width = w + 'px';
  }

  function renderHearts() {
    var html = '';
    for (var i = 0; i < 3; i++) {
      html += '<span class="h' + (i < state.hearts ? '' : ' lost') + '">❤️</span>';
    }
    $('hearts').innerHTML = html;
  }

  function updateHud() {
    $('hudFound').textContent = state.found.filter(Boolean).length + '/5';
    $('hintBadge').textContent = state.hintsLeft;
    $('hintBtn').classList.toggle('is-empty', state.hintsLeft <= 0);

    var ratio = Math.max(0, state.timeLeft / state.stage.time);
    $('timerFill').style.width = (ratio * 100).toFixed(1) + '%';
    $('timeLeft').textContent = fmtTime(state.timeLeft);
    var low = state.timeLeft <= 10;
    document.querySelector('.timer').classList.toggle('is-low', low);
    $('timeLeft').classList.toggle('is-low', low);
  }

  function startGame(idx) {
    var st = STAGES[idx];
    state.idx = idx;
    state.stage = st;
    state.found = st.spots.map(function () { return false; });
    state.wrong = 0;
    state.hintsLeft = 2;
    state.hearts = 3;
    state.timeLeft = st.time;
    state.used = 0;
    state.running = true;

    $('imgA').src = st.a;
    $('imgB').src = st.b;
    $('marksA').innerHTML = '';
    $('marksB').innerHTML = '';
    $('hudTitle').textContent = st.no + '. ' + st.title;
    $('gameTip').textContent = st.desc;
    $('gameTip').classList.remove('is-hidden');
    $('panelA').classList.remove('is-locked');
    $('panelB').classList.remove('is-locked');

    renderHearts();
    updateHud();
    showScreen('game');
    layoutBoard();
    Sfx.unlock();

    clearInterval(state.timerId);
    state.lastTick = Date.now();
    state.timerId = setInterval(tick, 100);

    setTimeout(function () {
      $('gameTip').classList.add('is-hidden');
    }, 4200);
  }

  function tick() {
    if (!state.running) { return; }
    var now = Date.now();
    var dt = (now - state.lastTick) / 1000;
    state.lastTick = now;
    state.timeLeft -= dt;
    state.used += dt;
    if (state.timeLeft <= 0) {
      state.timeLeft = 0;
      updateHud();
      endGame('time');
      return;
    }
    updateHud();
  }

  function pauseTimer() {
    if (state.timerId) { clearInterval(state.timerId); state.timerId = null; }
  }
  function resumeTimer() {
    if (!state.running) { return; }
    pauseTimer();
    state.lastTick = Date.now();
    state.timerId = setInterval(tick, 100);
  }

  /* ---------------- 터치 판정 ---------------- */
  function hitTest(nx, ny) {
    var best = -1;
    var bestScore = Infinity;
    state.stage.spots.forEach(function (sp, i) {
      var dx = (nx - sp.x) / sp.rx;
      var dy = (ny - sp.y) / sp.ry;
      var d = dx * dx + dy * dy;
      if (d <= 1 && d < bestScore) { bestScore = d; best = i; }
    });
    return best;
  }

  function pts(panel, nx, ny) {
    return {
      left: (nx * 100).toFixed(3) + '%',
      top: (ny * 100).toFixed(3) + '%'
    };
  }

  function addMark(kind, spot, nx, ny, onlyPanel) {
    var hosts = onlyPanel ? [onlyPanel === 'a' ? 'marksA' : 'marksB'] : ['marksA', 'marksB'];
    hosts.forEach(function (id) {
      var host = $(id);
      var el = document.createElement('div');
      if (kind === 'found') {
        el.className = 'mark';
        var p = pts(host, spot.x, spot.y);
        el.style.left = p.left;
        el.style.top = p.top;
        el.style.width = (spot.rx * 200) + '%';
        el.style.height = (spot.ry * 200) + '%';
      } else if (kind === 'x') {
        el.className = 'xmark';
        el.textContent = '✕';
        var q = pts(host, nx, ny);
        el.style.left = q.left;
        el.style.top = q.top;
      } else {
        el.className = 'hint-ring';
        var r = pts(host, spot.x, spot.y);
        el.style.left = r.left;
        el.style.top = r.top;
        el.style.width = (spot.rx * 230) + '%';
        el.style.height = (spot.ry * 230) + '%';
      }
      host.appendChild(el);
      if (kind !== 'found') {
        setTimeout(function () { if (el.parentNode) { el.parentNode.removeChild(el); } },
          kind === 'x' ? 720 : 3200);
      }
    });
  }

  function onPanelTap(ev) {
    if (!state.running) { return; }
    var panel = ev.currentTarget;
    var rect = panel.getBoundingClientRect();
    var clientX = ev.clientX;
    var clientY = ev.clientY;
    if (typeof clientX !== 'number') { return; }
    var nx = (clientX - rect.left) / rect.width;
    var ny = (clientY - rect.top) / rect.height;
    if (nx < 0 || nx > 1 || ny < 0 || ny > 1) { return; }

    $('gameTip').classList.add('is-hidden');

    var idx = hitTest(nx, ny);
    if (idx >= 0) {
      if (state.found[idx]) { return; }   // 이미 찾은 곳은 벌점 없음
      state.found[idx] = true;
      addMark('found', state.stage.spots[idx]);
      Sfx.ding();
      buzz(25);
      updateHud();
      if (state.found.every(Boolean)) {
        state.running = false;
        pauseTimer();
        setTimeout(function () { endGame('clear'); }, 520);
      }
      return;
    }

    // 오답
    state.wrong += 1;
    state.hearts = Math.max(0, state.hearts - 1);
    state.timeLeft = Math.max(0, state.timeLeft - 5);
    addMark('x', null, nx, ny, panel.id === 'panelA' ? 'a' : 'b');
    panel.classList.add('shake');
    setTimeout(function () { panel.classList.remove('shake'); }, 340);
    renderHearts();
    updateHud();
    Sfx.wrong();
    buzz([40, 60, 40]);
    if (state.hearts <= 0) {
      state.running = false;
      pauseTimer();
      setTimeout(function () { endGame('hearts'); }, 480);
    } else if (state.timeLeft <= 0) {
      state.running = false;
      pauseTimer();
      setTimeout(function () { endGame('time'); }, 480);
    }
  }

  /* ---------------- 힌트 ---------------- */
  function useHint() {
    if (!state.running || state.hintsLeft <= 0) { return; }
    var remaining = [];
    state.found.forEach(function (v, i) { if (!v) { remaining.push(i); } });
    if (!remaining.length) { return; }
    state.hintsLeft -= 1;
    state.timeLeft = Math.max(0, state.timeLeft - 5);
    var pick = remaining[Math.floor(Math.random() * remaining.length)];
    addMark('hint', state.stage.spots[pick]);
    Sfx.hint();
    buzz(20);
    updateHud();
    if (state.hintsLeft <= 0) { $('hintBtn').classList.add('is-empty'); }
  }

  /* ---------------- 결과 ---------------- */
  function starsFor(used, wrong) {
    var st = 3;
    if (wrong >= 2) { st -= 1; }
    if (wrong >= 4 || used > state.stage.time * 0.7) { st -= 1; }
    return Math.max(1, st);
  }

  function endGame(reason) {
    state.running = false;
    pauseTimer();
    var st = state.stage;
    var foundAll = reason === 'clear';
    var stars = foundAll ? starsFor(state.used, state.wrong) : 0;
    var prev = state.records[st.id];
    var isBest = false;

    if (foundAll) {
      var better = !prev || stars > prev.stars ||
        (stars === prev.stars && state.used < prev.time);
      if (better) {
        state.records[st.id] = {
          stars: Math.max(stars, prev ? prev.stars : 0),
          time: Math.min(state.used, prev ? prev.time : Infinity),
          wrong: state.wrong,
          at: new Date().toISOString()
        };
        saveRecords(state.records);
        isBest = true;
      }
      Sfx.clear();
      buzz([18, 60, 18, 60, 30]);
    } else {
      Sfx.over();
      buzz([60, 80, 60]);
    }

    var hasNext = state.idx < STAGES.length - 1;
    var emoji = foundAll ? (stars === 3 ? '🎉' : '✨') : (reason === 'time' ? '⏰' : '💔');
    var title = foundAll ? '다 찾았어요!' : (reason === 'time' ? '시간 초과!' : '하트를 다 잃었어요');

    var starHtml = '';
    for (var i = 1; i <= 3; i++) {
      starHtml += '<span class="star' + (i <= stars ? ' on' : '') + '">★</span>';
    }

    var html = '' +
      '<div class="modal-emoji">' + emoji + '</div>' +
      '<h2>' + title + '</h2>' +
      '<p class="sub">' + st.title + '</p>' +
      (foundAll ? '<div class="star-row">' + starHtml + '</div>' : '') +
      '<div class="result-grid">' +
        (foundAll
          ? '<div class="result-cell"><span>걸린 시간</span><b>' + fmtTime(state.used) + '</b></div>' +
            '<div class="result-cell"><span>오답</span><b>' + state.wrong + '회</b></div>' +
            '<div class="result-cell"><span>기록</span><b class="' + (isBest ? 'best' : '') + '">' +
              (isBest ? 'BEST!' : fmtTime(prev ? prev.time : state.used)) + '</b></div>'
          : '<div class="result-cell"><span>찾은 곳</span><b>' + state.found.filter(Boolean).length + '/5</b></div>' +
            '<div class="result-cell"><span>오답</span><b>' + state.wrong + '회</b></div>') +
      '</div>' +
      '<div class="modal-actions">' +
        (foundAll && hasNext
          ? '<button class="btn btn-primary" data-act="next">다음 스테이지 →</button>' +
            '<div class="btn-row"><button class="btn btn-ghost" data-act="retry">다시 하기</button>' +
            '<button class="btn btn-ghost" data-act="home">목록</button></div>'
          : '<button class="btn btn-primary" data-act="retry">다시 도전</button>' +
            '<button class="btn btn-ghost" data-act="home">스테이지 목록</button>') +
      '</div>';

    openModal(html);
  }

  /* ---------------- 모달 ---------------- */
  function openModal(html) {
    var root = $('modalRoot');
    $('modal').innerHTML = html;
    root.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    $('modalRoot').hidden = true;
    $('modal').innerHTML = '';
    document.body.style.overflow = '';
  }

  $('modalRoot').addEventListener('click', function (ev) {
    var t = ev.target;
    if (t.getAttribute && (t.getAttribute('data-close') || t.getAttribute('data-act') === 'home')) {
      closeModal();
      if (t.getAttribute('data-act') === 'home') { renderHome(); showScreen('home'); }
      return;
    }
    var act = t.getAttribute && t.getAttribute('data-act');
    if (!act) { return; }
    closeModal();
    if (act === 'retry') { startGame(state.idx); }
    if (act === 'next') { startGame(Math.min(state.idx + 1, STAGES.length - 1)); }
  });

  /* ---------------- 이벤트 연결 ---------------- */
  function bind() {
    $('stageList').addEventListener('click', function (ev) {
      var card = ev.target.closest ? ev.target.closest('.stage-card') : null;
      if (!card) { return; }
      Sfx.unlock();
      startGame(parseInt(card.getAttribute('data-idx'), 10));
    });

    $('backBtn').addEventListener('click', function () {
      state.running = false;
      pauseTimer();
      renderHome();
      showScreen('home');
    });

    $('hintBtn').addEventListener('click', useHint);

    $('soundToggleHome').addEventListener('click', toggleSound);
    $('soundToggleGame').addEventListener('click', toggleSound);

    $('resetBtn').addEventListener('click', function () {
      openModal('' +
        '<div class="modal-emoji">🧹</div><h2>기록을 지울까요?</h2>' +
        '<p class="sub">저장된 별점과 최고 기록이 모두 사라져요.</p>' +
        '<div class="modal-actions">' +
          '<button class="btn btn-primary" data-act="reset-yes">지우기</button>' +
          '<button class="btn btn-ghost" data-close="1">취소</button>' +
        '</div>');
    });

    document.addEventListener('click', function (ev) {
      var t = ev.target;
      if (t.getAttribute && t.getAttribute('data-act') === 'reset-yes') {
        state.records = {};
        saveRecords({});
        closeModal();
        renderHome();
      }
    });

    ['panelA', 'panelB'].forEach(function (id) {
      var el = $(id);
      el.addEventListener('pointerdown', function (ev) {
        if (ev.pointerType === 'mouse' && ev.button !== 0) { return; }
        ev.preventDefault();
        Sfx.unlock();
        onPanelTap(ev);
      });
      if (!('onpointerdown' in window)) {
        el.addEventListener('touchstart', function (ev) {
          var t = ev.changedTouches[0];
          onPanelTap({ currentTarget: el, clientX: t.clientX, clientY: t.clientY });
          ev.preventDefault();
        }, { passive: false });
      }
    });

    window.addEventListener('resize', function () {
      if ($('screenGame').classList.contains('is-active')) { layoutBoard(); }
    });
    window.addEventListener('orientationchange', function () {
      setTimeout(function () {
        if ($('screenGame').classList.contains('is-active')) { layoutBoard(); }
      }, 260);
    });

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { pauseTimer(); }
      else { resumeTimer(); }
    });

    document.addEventListener('gesturestart', function (e) { e.preventDefault(); });
    document.addEventListener('dblclick', function (e) { e.preventDefault(); }, { passive: false });
  }

  /* ---------------- 시작 ---------------- */
  function boot() {
    applySound();
    renderHome();
    bind();
    layoutBoard();

    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function () {
        navigator.serviceWorker.register('sw.js').catch(function () {});
      });
    }

    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      window.__installPrompt = e;
      var foot = document.querySelector('.foot-note');
      if (foot) {
        foot.innerHTML = '설치하면 오프라인에서도 플레이 ' +
          '<button class="text-btn" id="installBtn" type="button">앱으로 설치</button>';
        var b = $('installBtn');
        if (b) {
          b.addEventListener('click', function () {
            if (window.__installPrompt) {
              window.__installPrompt.prompt();
              window.__installPrompt = null;
            }
          });
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
