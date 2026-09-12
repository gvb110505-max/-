/* ==========================================================================
   Strukt storefront behaviour: catalogue filtering, AJAX add-to-cart,
   the slide-in cart drawer, variant pickers and the toast.

   The drawer's markup stays in Liquid — after every cart mutation the
   section is re-fetched through the Section Rendering API, so prices and
   line items are always formatted by Shopify, never by this file.
   ========================================================================== */
(function () {
  if (window.__struktInit) return;
  window.__struktInit = true;

  var DRAWER_SECTION = 'strukt-cart-drawer';
  var routeRoot = (window.Shopify && window.Shopify.routes && window.Shopify.routes.root) || '/';

  /* — money ————————————————————————————————————————————————— */
  function formatMoney(cents, format) {
    if (!format) return (cents / 100).toFixed(2);
    function group(num, decimals, thousands, decimal) {
      var parts = (Math.abs(num) / 100).toFixed(decimals).split('.');
      var whole = parts[0].replace(/(\d)(?=(\d\d\d)+$)/g, '$1' + thousands);
      return parts[1] ? whole + decimal + parts[1] : whole;
    }
    return format.replace(/\{\{\s*(\w+)\s*\}\}/, function (_, name) {
      switch (name) {
        case 'amount': return group(cents, 2, ',', '.');
        case 'amount_no_decimals': return group(cents, 0, ',', '.');
        case 'amount_with_comma_separator': return group(cents, 2, '.', ',');
        case 'amount_no_decimals_with_comma_separator': return group(cents, 0, '.', ',');
        case 'amount_with_space_separator': return group(cents, 2, ' ', ',');
        case 'amount_no_decimals_with_space_separator': return group(cents, 0, ' ', ',');
        case 'amount_with_apostrophe_separator': return group(cents, 2, "'", '.');
        default: return group(cents, 2, ',', '.');
      }
    });
  }
  window.StruktMoney = formatMoney;

  /* — toast —————————————————————————————————————————————————— */
  var toastTimer;
  function toast(message) {
    var el = document.querySelector('[data-strukt-toast]');
    if (!el) {
      el = document.createElement('div');
      el.className = 'strukt';
      el.innerHTML = '<div class="strukt-toast" data-strukt-toast role="status" aria-live="polite"></div>';
      document.body.appendChild(el);
      el = el.querySelector('[data-strukt-toast]');
    }
    el.textContent = message;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, 2200);
  }

  /* — cart ——————————————————————————————————————————————————— */
  function drawer() { return document.querySelector('[data-strukt-drawer]'); }

  function setCount(count) {
    document.querySelectorAll('[data-strukt-cart-count]').forEach(function (node) {
      node.textContent = count;
    });
  }

  function openDrawer() {
    var el = drawer();
    if (!el) { window.location.href = routeRoot + 'cart'; return; }
    el.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    var close = el.querySelector('[data-strukt-cart-close]');
    if (close) close.focus();
  }

  function closeDrawer() {
    var el = drawer();
    if (!el) return;
    el.hidden = true;
    document.documentElement.style.overflow = '';
  }

  function refreshDrawer(keepOpen) {
    return fetch(routeRoot + '?section_id=' + DRAWER_SECTION, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (res) { return res.ok ? res.text() : null; })
      .then(function (html) {
        if (!html) return;
        var host = document.getElementById('shopify-section-' + DRAWER_SECTION);
        if (!host) return;
        var parsed = new DOMParser().parseFromString(html, 'text/html');
        var fresh = parsed.getElementById('shopify-section-' + DRAWER_SECTION) || parsed.body;
        host.innerHTML = fresh.innerHTML;
        if (keepOpen) {
          var el = drawer();
          if (el) el.hidden = false;
        }
      });
  }

  function syncCart(keepOpen) {
    return fetch(routeRoot + 'cart.js', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        setCount(cart.item_count);
        return refreshDrawer(keepOpen);
      });
  }

  function busy(state) {
    var el = drawer();
    if (el) el.classList.toggle('is-busy', !!state);
  }

  function changeLine(line, quantity) {
    busy(true);
    return fetch(routeRoot + 'cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ line: line, quantity: quantity })
    })
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        setCount(cart.item_count);
        return refreshDrawer(true);
      })
      .catch(function () { toast('Could not update the cart.'); })
      .then(function () { busy(false); });
  }

  function addToCart(form) {
    var button = form.querySelector('[type="submit"]');
    if (button) button.disabled = true;

    return fetch(routeRoot + 'cart/add.js', {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body: new FormData(form)
    })
      .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, body: body }; }); })
      .then(function (result) {
        if (!result.ok) {
          toast(result.body.description || result.body.message || 'Could not add that item.');
          return;
        }
        var name = result.body.product_title || result.body.title || 'Item';
        var variant = result.body.variant_title;
        toast(variant && variant !== 'Default Title' ? name + ' — ' + variant + ' added' : name + ' added');
        return syncCart(true).then(openDrawer);
      })
      .catch(function () { toast('Could not add that item.'); })
      .then(function () { if (button) button.disabled = false; });
  }

  /* — variant picker (product page) ——————————————————————————— */
  function updateVariant(scope) {
    var dataEl = scope.querySelector('[data-strukt-variants]');
    if (!dataEl) return;

    var variants;
    try { variants = JSON.parse(dataEl.textContent); } catch (e) { return; }

    var chosen = [];
    scope.querySelectorAll('[data-strukt-option-group]').forEach(function (group) {
      var active = group.querySelector('[aria-checked="true"]');
      chosen.push(active ? active.getAttribute('data-strukt-option-value') : null);
    });

    var match = variants.find(function (v) {
      return chosen.every(function (value, i) { return value === null || v.options[i] === value; });
    });

    var idInput = scope.querySelector('[data-strukt-variant-id]');
    var priceEl = scope.querySelector('[data-strukt-price]');
    var compareEl = scope.querySelector('[data-strukt-compare]');
    var submit = scope.querySelector('[data-strukt-submit]');
    var note = scope.querySelector('[data-strukt-note]');
    var qtyInput = scope.querySelector('[data-strukt-qty]');
    var format = scope.getAttribute('data-money-format');

    if (!match) {
      if (submit) { submit.disabled = true; submit.textContent = submit.getAttribute('data-unavailable-label') || 'Unavailable'; }
      if (note) note.textContent = '';
      return;
    }

    if (idInput) idInput.value = match.id;
    if (priceEl) priceEl.textContent = match.price;
    if (compareEl) {
      compareEl.textContent = match.hasCompare ? match.compare : '';
      compareEl.hidden = !match.hasCompare;
    }

    if (submit) {
      if (!match.available) {
        submit.disabled = true;
        submit.textContent = submit.getAttribute('data-soldout-label') || 'Sold out';
      } else {
        submit.disabled = false;
        var qty = qtyInput ? parseInt(qtyInput.value, 10) || 1 : 1;
        var label = submit.getAttribute('data-add-label') || 'Add to cart';
        submit.textContent = label + ' — ' + formatMoney(match.priceCents * qty, format);
      }
    }

    if (note) note.textContent = match.available && match.backorder ? (note.getAttribute('data-backorder-note') || '') : '';

    // Keep the URL shareable, the way Shopify's own variant pickers do.
    if (history.replaceState && match.available !== undefined) {
      var url = new URL(window.location.href);
      url.searchParams.set('variant', match.id);
      history.replaceState({}, '', url.toString());
    }
  }

  /* — events ————————————————————————————————————————————————— */
  document.addEventListener('click', function (event) {
    var openBtn = event.target.closest('[data-strukt-cart-open]');
    if (openBtn) { event.preventDefault(); openDrawer(); return; }

    var closeBtn = event.target.closest('[data-strukt-cart-close]');
    if (closeBtn) { event.preventDefault(); closeDrawer(); return; }

    var step = event.target.closest('[data-strukt-line-change]');
    if (step) {
      event.preventDefault();
      changeLine(parseInt(step.getAttribute('data-line'), 10), parseInt(step.getAttribute('data-strukt-line-change'), 10));
      return;
    }

    var filter = event.target.closest('[data-strukt-filter]');
    if (filter) {
      event.preventDefault();
      var value = filter.getAttribute('data-strukt-filter');
      var bar = filter.closest('[data-strukt-filters]');
      var section = filter.closest('.strukt');
      bar.querySelectorAll('[data-strukt-filter]').forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn === filter ? 'true' : 'false');
      });
      section.querySelectorAll('[data-strukt-grid] .strukt-card').forEach(function (card) {
        card.hidden = value !== '*' && card.getAttribute('data-strukt-type') !== value;
      });
      return;
    }

    var option = event.target.closest('[data-strukt-option-value]');
    if (option) {
      event.preventDefault();
      var group = option.closest('[data-strukt-option-group]');
      group.querySelectorAll('[data-strukt-option-value]').forEach(function (btn) {
        btn.setAttribute('aria-checked', btn === option ? 'true' : 'false');
      });
      updateVariant(option.closest('[data-strukt-product]'));
      return;
    }

    var qtyBtn = event.target.closest('[data-strukt-qty-step]');
    if (qtyBtn) {
      event.preventDefault();
      var scope = qtyBtn.closest('[data-strukt-product]');
      var input = scope.querySelector('[data-strukt-qty]');
      var next = (parseInt(input.value, 10) || 1) + parseInt(qtyBtn.getAttribute('data-strukt-qty-step'), 10);
      input.value = Math.max(parseInt(input.min, 10) || 1, next);
      updateVariant(scope);
    }
  });

  document.addEventListener('input', function (event) {
    if (event.target.matches('[data-strukt-qty]')) {
      updateVariant(event.target.closest('[data-strukt-product]'));
    }
  });

  document.addEventListener('submit', function (event) {
    var form = event.target.closest('.strukt-js-add');
    if (!form) return;
    event.preventDefault();
    addToCart(form);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      var el = drawer();
      if (el && !el.hidden) closeDrawer();
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-strukt-product]').forEach(updateVariant);
  });
  if (document.readyState !== 'loading') {
    document.querySelectorAll('[data-strukt-product]').forEach(updateVariant);
  }

  // The theme editor re-renders sections in place; re-bind derived state.
  document.addEventListener('shopify:section:load', function (event) {
    event.target.querySelectorAll('[data-strukt-product]').forEach(updateVariant);
  });
})();
