/* Live camera for the Scan Document page.
 * Adds a "Take photo with camera" button under every upload box (.dk-drop).
 * The captured photo is placed into the page's file input, so the form submits it like a normal upload.
 * Features: live preview, capture, flip camera, flash, zoom, guide grid, scan mode (B&W),
 *           rotate, retake, and QR/barcode reading that fills the "reference_no" field.
 * Needs HTTPS or localhost (browser rule for camera access). */
(function () {
  'use strict';

  var CODE_FIELD = '[name="reference_no"]';   // field filled when a QR/barcode is read
  var JPEG_QUALITY = 0.92;

  var STYLE = [
    '.dkcam{position:fixed;inset:0;z-index:2000;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(15,23,42,.72)}',
    '.dkcam[hidden],.dkcam [hidden]{display:none!important}',
    '.dkcam-panel{width:100%;max-width:720px;max-height:100%;overflow:auto;background:#fff;border-radius:1rem;box-shadow:0 25px 60px rgba(0,0,0,.4)}',
    '.dkcam-head{display:flex;align-items:center;justify-content:space-between;padding:.85rem 1.1rem;font-size:.9rem;font-weight:700;color:#344767}',
    '.dkcam-head i{margin-right:.4rem;color:var(--dk-primary,#0d9488)}',
    '.dkcam-x{border:0;background:transparent;font-size:1.1rem;color:#67748e;cursor:pointer}',
    '.dkcam-stage{position:relative;display:flex;align-items:center;justify-content:center;height:min(62vh,520px);min-height:260px;background:#000;overflow:hidden}',
    '.dkcam-stage video,.dkcam-stage canvas{width:100%;height:100%;object-fit:contain}',
    '.dkcam.review video{display:none}',
    '.dkcam:not(.review) canvas{display:none}',
    '.dkcam-scan{filter:grayscale(1) contrast(1.6) brightness(1.05)}',
    '.dkcam-grid{position:absolute;inset:0;pointer-events:none;background:' +
      'linear-gradient(rgba(255,255,255,.35),rgba(255,255,255,.35)) 33.33% 0/1px 100% no-repeat,' +
      'linear-gradient(rgba(255,255,255,.35),rgba(255,255,255,.35)) 66.66% 0/1px 100% no-repeat,' +
      'linear-gradient(rgba(255,255,255,.35),rgba(255,255,255,.35)) 0 33.33%/100% 1px no-repeat,' +
      'linear-gradient(rgba(255,255,255,.35),rgba(255,255,255,.35)) 0 66.66%/100% 1px no-repeat}',
    '.dkcam-grid::after{content:"";position:absolute;inset:7%;border:2px dashed rgba(45,212,191,.9);border-radius:.5rem}',
    '.dkcam-stage.no-grid .dkcam-grid,.dkcam.review .dkcam-grid{display:none}',
    '.dkcam-msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:1.5rem;text-align:center;font-size:.9rem;color:#fff;background:rgba(0,0,0,.6)}',
    '.dkcam-zoom{display:flex;align-items:center;gap:.6rem;padding:.7rem 1.2rem 0;color:#67748e}',
    '.dkcam-zoom input{flex:1;accent-color:#0d9488}',
    '.dkcam-tools{display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem;padding:.8rem 1rem 0}',
    '.dkcam-tool{display:flex;flex-direction:column;align-items:center;gap:.2rem;min-width:64px;padding:.45rem .6rem;border:1px solid #d2d6da;border-radius:.6rem;background:#fff;font-size:.68rem;font-weight:600;color:#67748e;cursor:pointer}',
    '.dkcam-tool.on{border-color:transparent;color:#fff;background-image:linear-gradient(310deg,#0d9488,#2dd4bf)}',
    '.dkcam-actions{display:flex;align-items:center;justify-content:center;gap:.6rem;padding:1rem}',
    '.dkcam-shutter{width:64px;height:64px;border-radius:50%;border:4px solid #0d9488;background:radial-gradient(circle,#2dd4bf 0 55%,#fff 56%);cursor:pointer}',
    '.dkcam-shutter:active{transform:scale(.94)}',
    '.dkcam.review [data-live]{display:none!important}',
    '.dkcam:not(.review) [data-review]{display:none!important}',
    '.dkcam-row{margin-top:.75rem}',
    '.dkcam-note{margin-top:.4rem;font-size:.72rem;color:#67748e}',
    '@media(max-width:576px){.dkcam{padding:0}.dkcam-panel{max-width:none;height:100%;border-radius:0}.dkcam-stage{height:56vh}}'
  ].join('');

  var supported = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  var modal, video, canvas, stage, msgBox, zoomWrap, zoomInput, shutter;
  var stream = null, track = null, facing = 'environment', targetInput = null;
  var state = { torch: false, grid: true, scan: false, code: false };
  var detector = null, timer = null;

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function tool(act, icon, label) {
    return '<button type="button" class="dkcam-tool' + (act === 'grid' ? ' on' : '') + '" data-act="' + act + '"><i class="fas ' + icon + '"></i><span>' + label + '</span></button>';
  }
  function btn(act) { return modal.querySelector('[data-act="' + act + '"]'); }

  function build() {
    var style = document.createElement('style');
    style.textContent = STYLE;
    document.head.appendChild(style);

    modal = el('div', 'dkcam');
    modal.hidden = true;
    modal.innerHTML =
      '<div class="dkcam-panel" role="dialog" aria-modal="true" aria-label="Camera">' +
        '<div class="dkcam-head"><span><i class="fas fa-camera"></i>Take a photo</span>' +
          '<button type="button" class="dkcam-x" data-act="close" aria-label="Close"><i class="fas fa-times"></i></button></div>' +
        '<div class="dkcam-stage"><video autoplay playsinline muted></video><canvas></canvas>' +
          '<div class="dkcam-grid"></div><div class="dkcam-msg" hidden></div></div>' +
        '<div class="dkcam-zoom" data-live hidden><i class="fas fa-search-minus"></i>' +
          '<input type="range" min="1" max="1" step="0.1" value="1" aria-label="Zoom"><i class="fas fa-search-plus"></i></div>' +
        '<div class="dkcam-tools" data-live>' +
          tool('switch', 'fa-sync-alt', 'Flip') + tool('torch', 'fa-bolt', 'Flash') +
          tool('grid', 'fa-border-all', 'Guide') + tool('scan', 'fa-adjust', 'Scan mode') +
          tool('code', 'fa-qrcode', 'Read code') + '</div>' +
        '<div class="dkcam-actions" data-live><button type="button" class="dkcam-shutter" data-act="shoot" aria-label="Take photo"></button></div>' +
        '<div class="dkcam-actions" data-review>' +
          '<button type="button" class="dk-btn dk-btn-ghost" data-act="retake">Retake</button>' +
          '<button type="button" class="dk-btn dk-btn-ghost" data-act="rotate"><i class="fas fa-redo"></i> Rotate</button>' +
          '<button type="button" class="dk-btn" data-act="use">Use photo</button></div>' +
      '</div>';
    document.body.appendChild(modal);

    video = modal.querySelector('video');
    canvas = modal.querySelector('canvas');
    stage = modal.querySelector('.dkcam-stage');
    msgBox = modal.querySelector('.dkcam-msg');
    zoomWrap = modal.querySelector('.dkcam-zoom');
    zoomInput = zoomWrap.querySelector('input');
    shutter = btn('shoot');
    btn('code').hidden = !('BarcodeDetector' in window);

    var actions = {
      close: close, shoot: capture, retake: showLive, rotate: rotate, use: usePhoto,
      switch: function () { facing = facing === 'environment' ? 'user' : 'environment'; start(); },
      torch: toggleTorch,
      grid: function (b) { state.grid = !state.grid; stage.classList.toggle('no-grid', !state.grid); b.classList.toggle('on', state.grid); },
      scan: function (b) { state.scan = !state.scan; video.classList.toggle('dkcam-scan', state.scan); b.classList.toggle('on', state.scan); },
      code: toggleCode
    };
    modal.addEventListener('click', function (e) {
      if (e.target === modal) { close(); return; }
      var b = e.target.closest('[data-act]');
      if (b && actions[b.getAttribute('data-act')]) actions[b.getAttribute('data-act')](b);
    });
    zoomInput.addEventListener('input', function () {
      if (track) track.applyConstraints({ advanced: [{ zoom: parseFloat(zoomInput.value) }] }).catch(function () {});
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !modal.hidden) close(); });
  }

  function setMsg(text) {
    msgBox.textContent = text || '';
    msgBox.hidden = !text;
  }

  function stopStream() {
    clearTimeout(timer);
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    stream = null; track = null;
  }

  function start() {
    stopStream();
    state.torch = false; btn('torch').classList.remove('on');
    shutter.disabled = true;
    setMsg('Starting camera...');
    var constraints = { audio: false, video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } } };
    return navigator.mediaDevices.getUserMedia(constraints).then(function (s) {
      stream = s; track = s.getVideoTracks()[0];
      video.srcObject = s;
      setMsg(''); shutter.disabled = false;
      setupCaps();
      if (state.code) loop();
      return navigator.mediaDevices.enumerateDevices();
    }).then(function (devices) {
      btn('switch').hidden = devices.filter(function (d) { return d.kind === 'videoinput'; }).length < 2;
    }).catch(onError);
  }

  function setupCaps() {
    var caps = track.getCapabilities ? track.getCapabilities() : {};
    btn('torch').hidden = !caps.torch;
    if (caps.zoom) {
      zoomInput.min = caps.zoom.min; zoomInput.max = caps.zoom.max; zoomInput.step = caps.zoom.step || 0.1;
      zoomInput.value = (track.getSettings && track.getSettings().zoom) || caps.zoom.min;
      zoomWrap.hidden = false;
    } else { zoomWrap.hidden = true; }
  }

  function onError(err) {
    var name = err && err.name;
    var text = 'Could not start the camera.';
    if (name === 'NotAllowedError' || name === 'SecurityError') text = 'Camera access was blocked. Allow the camera for this site in your browser settings, then try again.';
    else if (name === 'NotFoundError' || name === 'OverconstrainedError') text = 'No camera was found on this device.';
    else if (name === 'NotReadableError') text = 'The camera is being used by another app.';
    setMsg(text);
  }

  function toggleTorch(b) {
    if (!track) return;
    var next = !state.torch;
    track.applyConstraints({ advanced: [{ torch: next }] }).then(function () {
      state.torch = next; b.classList.toggle('on', next);
    }).catch(function () {});
  }

  /* ---- QR / barcode reading ---- */
  function toggleCode(b) {
    state.code = !state.code;
    b.classList.toggle('on', state.code);
    if (state.code) loop(); else clearTimeout(timer);
  }
  function loop() {
    if (!state.code || modal.hidden || !video.videoWidth && !stream) return;
    if (!detector) { try { detector = new window.BarcodeDetector(); } catch (e) { return; } }
    detector.detect(video).then(function (codes) {
      if (codes.length) onCode(codes[0].rawValue);
      else timer = setTimeout(loop, 350);
    }).catch(function () { timer = setTimeout(loop, 500); });
  }
  function onCode(value) {
    var field = document.querySelector(CODE_FIELD);
    if (field) { field.value = value; field.dispatchEvent(new Event('input', { bubbles: true })); }
    setMsg('Code read: ' + value);
    setTimeout(function () { setMsg(''); close(); }, 1000);
  }

  /* ---- capture / review ---- */
  function capture() {
    if (!video.videoWidth) return;
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    if (state.scan) enhance(ctx, canvas.width, canvas.height);
    modal.classList.add('review');
  }
  function enhance(ctx, w, h) {                 // grayscale + contrast boost, works in every browser
    var img = ctx.getImageData(0, 0, w, h), d = img.data;
    for (var i = 0; i < d.length; i += 4) {
      var g = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
      g = (g - 128) * 1.5 + 138;
      d[i] = d[i + 1] = d[i + 2] = g < 0 ? 0 : g > 255 ? 255 : g;
    }
    ctx.putImageData(img, 0, 0);
  }
  function showLive() { modal.classList.remove('review'); }
  function rotate() {
    var c2 = document.createElement('canvas');
    c2.width = canvas.height; c2.height = canvas.width;
    var x = c2.getContext('2d');
    x.translate(c2.width / 2, c2.height / 2);
    x.rotate(Math.PI / 2);
    x.drawImage(canvas, -canvas.width / 2, -canvas.height / 2);
    canvas.width = c2.width; canvas.height = c2.height;
    canvas.getContext('2d').drawImage(c2, 0, 0);
  }
  function stamp() {
    var d = new Date(), p = function (n) { return String(n).padStart(2, '0'); };
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds());
  }
  function usePhoto() {
    canvas.toBlob(function (blob) {
      if (!blob) return;
      var file = new File([blob], 'scan-' + stamp() + '.jpg', { type: 'image/jpeg' });
      try {
        var dt = new DataTransfer();
        dt.items.add(file);
        targetInput.files = dt.files;
      } catch (e) { alert('This browser cannot attach the photo. Please use the upload box instead.'); return; }
      targetInput.dispatchEvent(new Event('change', { bubbles: true }));
      close();
    }, 'image/jpeg', JPEG_QUALITY);
  }

  /* ---- open / close ---- */
  function open(input) {
    if (!modal) build();
    targetInput = input;
    modal.classList.remove('review');
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    start();
  }
  function close() {
    stopStream();
    state.code = false; btn('code').classList.remove('on');
    modal.hidden = true;
    document.body.style.overflow = '';
  }

  /* ---- add the button under each upload box ---- */
  function init() {
    document.querySelectorAll('.dk-drop').forEach(function (drop) {
      var input = drop.querySelector('input[type=file]');
      if (!input) return;
      var row = el('div', 'dkcam-row');
      var b = el('button', 'dk-btn dk-btn-ghost', '<i class="fas fa-camera me-1"></i> Take photo with camera');
      b.type = 'button';
      row.appendChild(b);
      if (supported) {
        b.addEventListener('click', function () { open(input); });
      } else {
        b.disabled = true;
        row.appendChild(el('div', 'dkcam-note', 'The camera needs a secure connection (HTTPS) or localhost.'));
      }
      drop.insertAdjacentElement('afterend', row);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();