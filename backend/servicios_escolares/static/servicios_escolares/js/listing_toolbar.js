/* Generic listing toolbar initializer for cards/table/list pages
   Expects a pane element (e.g., #pane-lista) that contains:
   - .ip-toolbar with controls: #ip-search, #ip-year-menu, .ip-year-option, #ip-year-label,
     .ip-status-option, #ip-status-label, .ip-sort-option, #ip-sort-label
   - Items with [data-term] and optional [data-anio] and [data-estado] or [data-activo]
   - Optional containers: #ip-grid or #pl-grid, #ip-list or #pl-list, #ip-table-wrap
*/
(function(global){
  function textNorm(s){ return (s||'').toString().toLowerCase(); }
  function pickSortKey(el){
    return el.getAttribute('data-fecha') || el.getAttribute('data-inicio') || el.getAttribute('data-fin') || '';
  }
  function selectAll(root, sel){ return Array.prototype.slice.call(root.querySelectorAll(sel)); }

  function init(pane){
    if (!pane) return;
    var input = pane.querySelector('#ip-search');
    var yearMenu = pane.querySelector('#ip-year-menu');
    var yearLabel = pane.querySelector('#ip-year-label');
    var statusLabel = pane.querySelector('#ip-status-label');
    var sortLabel = pane.querySelector('#ip-sort-label');

    var grid = pane.querySelector('#ip-grid, #pl-grid') || pane.querySelector('#pl-grid');
    var list = pane.querySelector('#ip-list, #pl-list') || pane.querySelector('#pl-list');
    var tableWrap = pane.querySelector('#ip-table-wrap');

    var yearValue = '', statusValue = '', sortValue = 'recientes';

    // Build year menu from data-anio
    if (yearMenu){
      var yrs = new Set();
      selectAll(pane, '[data-anio]').forEach(function(el){ var y = el.getAttribute('data-anio'); if (y) yrs.add(y); });
      Array.from(yrs).sort(function(a,b){ return b.localeCompare(a); }).forEach(function(y){
        var li = document.createElement('li');
        li.innerHTML = '<a class="dropdown-item ip-year-option" data-value="'+y+'">'+y+'</a>';
        yearMenu.appendChild(li);
      });
    }

    function match(el){
      var q = textNorm(input ? input.value : '');
      var hitText = textNorm(el.getAttribute('data-term')||'').includes(q);
      var hitYear = !yearValue || (el.getAttribute('data-anio') === yearValue);
      var stateAttr = el.hasAttribute('data-estado') ? 'data-estado' : (el.hasAttribute('data-activo') ? 'data-activo' : null);
      var hitStatus = !statusValue || (stateAttr && el.getAttribute(stateAttr) === statusValue);
      return hitText && hitYear && hitStatus;
    }

    function applyFilters(){
      if (grid){ selectAll(grid, '[data-term]').forEach(function(card){ card.style.display = match(card) ? '' : 'none'; }); }
      if (list){ selectAll(list, '[data-term]').forEach(function(li){ li.style.display = match(li) ? '' : 'none'; }); }
      if (tableWrap){ selectAll(tableWrap, 'tbody tr').forEach(function(tr){ tr.style.display = match(tr) ? '' : 'none'; }); }
    }

    function applySort(){
      var dir = sortValue === 'recientes' ? 'desc' : 'asc';
      var cmp = function(a,b){ var av=pickSortKey(a), bv=pickSortKey(b); return dir==='asc'? av.localeCompare(bv) : bv.localeCompare(av); };
      if (grid){ selectAll(grid, '[data-term]').sort(cmp).forEach(function(n){ grid.appendChild(n); }); }
      if (list){ selectAll(list, '[data-term]').sort(cmp).forEach(function(n){ list.appendChild(n); }); }
      if (tableWrap){ var tbody = tableWrap.querySelector('tbody'); if (tbody){ selectAll(tbody, 'tr').sort(cmp).forEach(function(r){ tbody.appendChild(r); }); } }
    }

    // Events
    if (input) input.addEventListener('input', applyFilters);
    pane.addEventListener('click', function(e){
      var y = e.target.closest && e.target.closest('.ip-year-option');
      if (y){ e.preventDefault(); selectAll(pane, '.ip-year-option').forEach(function(o){o.classList.remove('active')}); y.classList.add('active'); yearValue = y.getAttribute('data-value')||''; if (yearLabel){ yearLabel.textContent = yearValue ? ('Año: '+y.textContent.trim()) : 'Todos los años'; } applyFilters(); return; }
      var s = e.target.closest && e.target.closest('.ip-status-option');
      if (s){ e.preventDefault(); selectAll(pane, '.ip-status-option').forEach(function(o){o.classList.remove('active')}); s.classList.add('active'); statusValue = s.getAttribute('data-value')||''; if (statusLabel){ statusLabel.textContent = statusValue ? ('Estado: '+s.textContent.trim()) : 'Todos los estados'; } applyFilters(); return; }
      var o = e.target.closest && e.target.closest('.ip-sort-option');
      if (o){ e.preventDefault(); selectAll(pane, '.ip-sort-option').forEach(function(x){x.classList.remove('active')}); o.classList.add('active'); sortValue = o.getAttribute('data-value')||'recientes'; if (sortLabel){ sortLabel.textContent = o.textContent.trim(); } applySort(); return; }
    });

    // Initial
    applyFilters();
    applySort();
  }

  global.SEListing = { init: init };
})(window);
