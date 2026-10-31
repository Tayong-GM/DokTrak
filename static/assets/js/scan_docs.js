/* Shared form behaviour: upload zone (name/size + image preview) and character counters. */
(function () {
  document.querySelectorAll('.dk-drop').forEach(function (drop) {
    var input = drop.querySelector('input[type=file]');
    var title = drop.querySelector('[data-title]');
    var hint = drop.querySelector('[data-hint]');
    var t0 = title.textContent, h0 = hint.textContent;
    var preview = null;

    function clearPreview() {
      if (preview) { URL.revokeObjectURL(preview.src); preview.remove(); preview = null; }
    }
    function reset() {
      title.textContent = t0; hint.textContent = h0;
      drop.classList.remove('has-file'); clearPreview();
    }

    input.addEventListener('change', function () {
      clearPreview();
      var f = input.files[0];
      if (!f) { reset(); return; }
      title.textContent = f.name;
      hint.textContent = (f.size / 1048576).toFixed(2) + ' MB';
      drop.classList.add('has-file');
      if (f.type && f.type.indexOf('image/') === 0) {
        preview = document.createElement('img');
        preview.className = 'dk-preview';
        preview.alt = 'Scan preview';
        preview.src = URL.createObjectURL(f);
        drop.insertAdjacentElement('afterend', preview);
      }
    });

    ['dragenter', 'dragover'].forEach(function (e) { input.addEventListener(e, function () { drop.classList.add('is-over'); }); });
    ['dragleave', 'drop'].forEach(function (e) { input.addEventListener(e, function () { drop.classList.remove('is-over'); }); });
    drop.closest('form').addEventListener('reset', reset);
  });

  document.querySelectorAll('.dk textarea[maxlength]').forEach(function (ta) {
    var c = document.createElement('div');
    c.className = 'dk-count';
    ta.insertAdjacentElement('afterend', c);
    var update = function () { c.textContent = ta.value.length + ' / ' + ta.maxLength; };
    ta.addEventListener('input', update);
    ta.closest('form').addEventListener('reset', function () { setTimeout(update, 0); });
    update();
  });
})();
