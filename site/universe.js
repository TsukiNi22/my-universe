/* my-universe - catalog: filters (category, format, text), stable / pre channel, the same distribution in every card */
(function () {
  'use strict';
  var root = document.documentElement;
  var key = (root.getAttribute('data-storage-key') || 'my-universe') + '-';
  var Q = new URLSearchParams(location.search);
  function load(name) { try { return localStorage.getItem(key + name); } catch (e) { return null; } }
  function save(name, value) { try { localStorage.setItem(key + name, value); } catch (e) { /* storage unavailable */ } }
  if (window.DOC_FR) {
    var words = { 'Search a package': 'Rechercher un paquet', 'Filter the packages': 'Filtrer les paquets', 'Category': 'Catégorie', 'Channel': 'Canal' };
    for (var w in words) if (!Object.prototype.hasOwnProperty.call(window.DOC_FR, w)) window.DOC_FR[w] = words[w];
  }

  // Filters
  var state = { category: 'all', format: 'all', text: '' };
  var cards = Array.prototype.slice.call(document.querySelectorAll('.pkg'));
  var groups = Array.prototype.slice.call(document.querySelectorAll('.cat-group'));
  var empty = document.querySelector('.empty-filter');
  function apply() {
    var shown = 0, words = state.text.toLowerCase().split(/\s+/).filter(Boolean);
    cards.forEach(function (c) {
      var text = (c.getAttribute('data-search') || '').toLowerCase();
      var ok = (state.category === 'all' || c.getAttribute('data-category') === state.category) &&
        (state.format === 'all' || (' ' + c.getAttribute('data-formats') + ' ').indexOf(' ' + state.format + ' ') >= 0) &&
        words.every(function (x) { return text.indexOf(x) >= 0; });
      c.hidden = !ok;
      if (ok) shown++;
    });
    groups.forEach(function (g) {
      var filtered = state.category !== 'all' || state.format !== 'all' || words.length;
      g.hidden = (state.category !== 'all' && g.getAttribute('data-category') !== state.category) ||
        (filtered && !g.querySelector('.pkg:not([hidden])'));
    });
    if (empty) empty.hidden = shown > 0;
  }
  function setChannel(value) {
    root.setAttribute('data-channel-view', value === 'pre' ? 'pre' : 'stable');
    save('channel', root.getAttribute('data-channel-view'));
  }
  document.querySelectorAll('.seg[data-filter]').forEach(function (seg) {
    var name = seg.getAttribute('data-filter');
    function select(value) {
      seg.querySelectorAll('button').forEach(function (b) {
        var on = b.getAttribute('data-value') === value;
        b.classList.toggle('on', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      if (name === 'channel') setChannel(value);
      else { state[name] = value; apply(); }
    }
    seg.addEventListener('click', function (ev) {
      var b = ev.target.closest('button');
      if (b) select(b.getAttribute('data-value'));
    });
    if (name === 'channel') select(Q.get('channel') || load('channel') || 'stable');
    else if (Q.get(name)) select(Q.get(name));
  });
  var filter = document.querySelector('.pkg-filter');
  if (filter) filter.addEventListener('input', function () { state.text = filter.value.trim(); apply(); });

  // The distribution chosen in one card is shown in every card (and kept)
  var syncing = false;
  function showDistro(tab) {
    syncing = true;
    document.querySelectorAll('.ctabs[data-distro] button[data-tab="' + tab + '"]').forEach(function (b) { b.click(); });
    syncing = false;
  }
  document.querySelectorAll('.ctabs[data-distro]').forEach(function (bar) {
    bar.addEventListener('click', function (ev) {
      var b = ev.target.closest('button');
      if (!b || syncing) return;
      save('distro', b.getAttribute('data-tab'));
      showDistro(b.getAttribute('data-tab'));
    });
  });
  if (load('distro')) showDistro(load('distro'));
  apply();
})();
