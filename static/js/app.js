/*
 * EPIConnect front-end behaviour.
 *
 * Inline event handlers (onclick="...", onsubmit="...") were moved here so the
 * Content-Security-Policy can forbid inline script (only nonce-tagged <script>
 * blocks run). Elements declare behaviour with data-* attributes instead.
 */
(function () {
    'use strict';

    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    // <form data-confirm="Delete this?"> asks before submitting
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (form.matches && form.matches('form[data-confirm]')) {
            if (!window.confirm(form.getAttribute('data-confirm'))) e.preventDefault();
        }
    }, true);

    document.addEventListener('click', function (e) {
        var el = e.target.closest('[data-action]');
        if (!el) return;
        var action = el.getAttribute('data-action');

        if (action === 'toggle-dark') {
            document.documentElement.classList.toggle('dark');
            try {
                localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
            } catch (err) { /* storage unavailable */ }
        } else if (action === 'toggle-menu') {
            var menu = document.getElementById('mobile-menu');
            if (menu) menu.classList.toggle('open');
        } else if (action === 'submit-with-confirm') {
            var target = document.getElementById(el.getAttribute('data-form'));
            if (target && window.confirm(el.getAttribute('data-confirm'))) target.submit();
        } else if (action === 'toggle-like') {
            toggleLike(el);
        }
    });

    function toggleLike(btn) {
        var postId = btn.getAttribute('data-post-id');
        fetch('/social/' + encodeURIComponent(postId) + '/like/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken() },
            credentials: 'same-origin',
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.error) { window.alert(data.error); return; }
                var svg = btn.querySelector('svg');
                var count = btn.querySelector('.like-count');
                if (count) count.textContent = data.count;
                if (data.liked) {
                    btn.classList.remove('text-gray-400', 'dark:text-slate-500');
                    btn.classList.add('text-red-500');
                    if (svg) svg.setAttribute('fill', 'currentColor');
                } else {
                    btn.classList.remove('text-red-500');
                    btn.classList.add('text-gray-400', 'dark:text-slate-500');
                    if (svg) svg.setAttribute('fill', 'none');
                }
            });
    }

    // Navbar notification dropdown (authenticated users only)
    var notifList = document.getElementById('notification-list');
    if (notifList) {
        var icons = {
            message: { bg: 'bg-blue-500/10', color: 'text-blue-500', path: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
            comment: { bg: 'bg-emerald-500/10', color: 'text-emerald-500', path: 'M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z' },
            like: { bg: 'bg-pink-500/10', color: 'text-pink-500', path: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z' },
            alert: { bg: 'bg-amber-500/10', color: 'text-amber-500', path: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
        };

        var loadNotifications = function () {
            fetch('/notifications/dropdown/', { credentials: 'same-origin' })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.notifications || !data.notifications.length) {
                        notifList.innerHTML = '<p class="p-6 text-gray-400 dark:text-slate-500 text-sm text-center">All caught up!</p>';
                        return;
                    }
                    var html = '';
                    data.notifications.forEach(function (n) {
                        var t = icons[n.type] || icons.alert;
                        var fill = n.type === 'like' ? 'currentColor' : 'none';
                        // n.content contains user-supplied text (e.g. item titles): always escaped.
                        html += '<a href="' + escapeHtml(n.link) + '" class="flex items-center p-3.5 hover:bg-stone-100 dark:hover:bg-slate-700/50 ' + (!n.is_read ? 'bg-primary-50/50 dark:bg-primary-500/5' : '') + '">' +
                            '<div class="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ' + t.bg + '"><svg class="w-4.5 h-4.5 ' + t.color + '" fill="' + fill + '" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="' + t.path + '"></path></svg></div>' +
                            '<div class="ml-3 flex-1 min-w-0"><p class="text-sm ' + (!n.is_read ? 'text-gray-900 dark:text-slate-100 font-medium' : 'text-gray-500 dark:text-slate-400') + ' truncate">' + escapeHtml(n.content) + '</p><p class="text-xs text-gray-400 dark:text-slate-500 mt-0.5">' + escapeHtml(n.time) + '</p></div>' +
                            (!n.is_read ? '<div class="w-2 h-2 bg-primary-500 rounded-full flex-shrink-0 ml-2"></div>' : '') +
                            '</a>';
                    });
                    notifList.innerHTML = html;
                })
                .catch(function () {
                    notifList.innerHTML = '<p class="p-4 text-gray-400 text-sm text-center">Could not load</p>';
                });
        };

        var dropdown = notifList.closest('.dropdown');
        if (dropdown) {
            var loaded = false;
            dropdown.addEventListener('mouseenter', function () {
                if (!loaded) { loadNotifications(); loaded = true; }
            });
            setInterval(function () { loaded = false; }, 30000);
        }
    }
})();
