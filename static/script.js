(function() {
    'use strict';

    var searchInput = document.getElementById('searchInput');
    var searchBtn = document.getElementById('searchBtn');
    var autocompleteEl = document.getElementById('autocomplete');
    var themeToggle = document.getElementById('themeToggle');
    var loadingEl = document.getElementById('loading');
    var resultEl = document.getElementById('result');
    var errorEl = document.getElementById('error');
    var agentResultsEl = document.getElementById('agentResults');
    var alertToggleBtn = document.getElementById('alertToggleBtn');
    var alertFormEl = document.getElementById('alertForm');
    var alertTargetInput = document.getElementById('alertTargetInput');
    var alertDirectionSelect = document.getElementById('alertDirectionSelect');
    var alertSetBtn = document.getElementById('alertSetBtn');
    var alertTagsEl = document.getElementById('alertTags');
    var alertNotificationEl = document.getElementById('alertNotification');
    var alertNotificationTextEl = document.getElementById('alertNotificationText');
    var alertNotificationCloseBtn = document.getElementById('alertNotificationClose');

    window.currentStockName = '';
    var chartData = [];
    var chart = null;
    var candleSeries = null;
    var volumeSeries = null;
    var smaLines = {};
    var debounceTimer = null;
    var ALERTS_STORAGE_KEY = 'flowsense_alerts';
    var MAX_ALERTS = 10;

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    function formatDateKR(str) {
        if (!str) return '';
        var m = String(str).match(/^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})/);
        if (m) return m[1] + '년 ' + m[2] + '월 ' + m[3] + '일';
        return str;
    }

    function initTheme() {
        var saved = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', saved);
        themeToggle.textContent = saved === 'dark' ? '라이트' : '다크';
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        themeToggle.textContent = next === 'dark' ? '라이트' : '다크';
        if (chart) updateChartColors();
    }

    function getChartColors() {
        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return {
            bg: isDark ? '#21212a' : '#ffffff',
            text: isDark ? '#8b8b9a' : '#8b95a1',
            grid: isDark ? '#2e2e3a' : '#f0f0f0',
            border: isDark ? '#2e2e3a' : '#e5e8eb',
            up: '#f04452',
            down: '#3182f6',
        };
    }

    function updateChartColors() {
        if (!chart) return;
        var c = getChartColors();
        chart.applyOptions({
            layout: { background: { color: c.bg }, textColor: c.text },
            grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } },
        });
        if (candleSeries) {
            candleSeries.applyOptions({ upColor: c.up, downColor: c.down, borderUpColor: c.up, borderDownColor: c.down, wickUpColor: c.up, wickDownColor: c.down });
        }
        if (volumeSeries) {
            volumeSeries.applyOptions({ color: 'rgba(49,130,246,0.15)' });
        }
    }

    function initChart() {
        var container = document.getElementById('chartContainer');
        container.innerHTML = '';
        var c = getChartColors();

        chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 360,
            layout: { background: { color: c.bg }, textColor: c.text },
            grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { borderColor: c.border },
            timeScale: { borderColor: c.border, timeVisible: false },
        });

        candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
            upColor: c.up, downColor: c.down,
            borderUpColor: c.up, borderDownColor: c.down,
            wickUpColor: c.up, wickDownColor: c.down,
        });

        volumeSeries = chart.addSeries(LightweightCharts.HistogramSeries, {
            color: 'rgba(49,130,246,0.15)',
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
        });

        chart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.85, bottom: 0 },
        });

        smaLines.sma5 = chart.addSeries(LightweightCharts.LineSeries, { color: '#3182f6', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        smaLines.sma20 = chart.addSeries(LightweightCharts.LineSeries, { color: '#f59f00', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        smaLines.sma60 = chart.addSeries(LightweightCharts.LineSeries, { color: '#f04452', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });

        new ResizeObserver(function() {
            if (chart) chart.applyOptions({ width: container.clientWidth });
        }).observe(container);
    }

    function calcSMA(data, period) {
        var result = [];
        for (var i = period - 1; i < data.length; i++) {
            var sum = 0;
            for (var j = i - period + 1; j <= i; j++) sum += data[j].close;
            result.push({ time: data[i].date, value: Math.round(sum / period) });
        }
        return result;
    }

    function getISOWeekKey(dateStr) {
        var d = new Date(dateStr);
        d.setHours(0, 0, 0, 0);
        d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7));
        var yearStart = new Date(d.getFullYear(), 0, 4);
        var weekNum = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
        return d.getFullYear() + '-W' + (weekNum < 10 ? '0' : '') + weekNum;
    }

    function aggregateCandles(data, keyFn) {
        var groups = {};
        var order = [];
        for (var i = 0; i < data.length; i++) {
            var key = keyFn(data[i].date);
            if (!groups[key]) {
                groups[key] = [];
                order.push(key);
            }
            groups[key].push(data[i]);
        }
        var result = [];
        for (var j = 0; j < order.length; j++) {
            var items = groups[order[j]];
            var first = items[0];
            var last = items[items.length - 1];
            var high = first.high;
            var low = first.low;
            var vol = 0;
            for (var k = 0; k < items.length; k++) {
                if (items[k].high > high) high = items[k].high;
                if (items[k].low < low) low = items[k].low;
                vol += items[k].volume;
            }
            result.push({
                date: first.date,
                open: first.open,
                high: high,
                low: low,
                close: last.close,
                volume: vol
            });
        }
        return result;
    }

    function renderChart(interval) {
        if (!chartData.length || !chart) return;

        var data;
        if (interval === 'weekly') {
            data = aggregateCandles(chartData, getISOWeekKey);
        } else if (interval === 'monthly') {
            data = aggregateCandles(chartData, function(d) { return d.substring(0, 7); });
        } else {
            data = chartData;
        }

        var candles = data.map(function(d) { return { time: d.date, open: d.open, high: d.high, low: d.low, close: d.close }; });
        var volumes = data.map(function(d) { return { time: d.date, value: d.volume, color: d.close >= d.open ? 'rgba(240,68,82,0.2)' : 'rgba(49,130,246,0.2)' }; });

        candleSeries.setData(candles);
        volumeSeries.setData(volumes);

        smaLines.sma5.setData(calcSMA(data, 5));
        smaLines.sma20.setData(calcSMA(data, 20));
        smaLines.sma60.setData(calcSMA(data, 60));

        chart.timeScale().fitContent();
    }

    async function searchStocks(query) {
        if (query.length < 1) { autocompleteEl.classList.remove('show'); return; }
        try {
            var resp = await fetch('/api/search?q=' + encodeURIComponent(query));
            var stocks = await resp.json();
            if (stocks.length > 0) {
                autocompleteEl.innerHTML = stocks.map(function(s) {
                    return '<div class="autocomplete-item" data-name="' + escapeHtml(s.name) + '">'
                        + '<span class="name">' + escapeHtml(s.name) + '</span>'
                        + '<span class="market">' + escapeHtml(s.market) + '</span></div>';
                }).join('');
                autocompleteEl.classList.add('show');
            } else {
                autocompleteEl.classList.remove('show');
            }
        } catch (e) {
            autocompleteEl.classList.remove('show');
        }
    }

    function parsePriceNumber(value) {
        if (value === null || value === undefined || value === '') return null;
        var normalized = String(value).replace(/,/g, '');
        var num = Number(normalized);
        if (!isFinite(num)) return null;
        return Math.round(num);
    }

    function loadAlerts() {
        try {
            var parsed = JSON.parse(localStorage.getItem(ALERTS_STORAGE_KEY) || '[]');
            if (!Array.isArray(parsed)) return [];
            return parsed.filter(function(item) {
                return item
                    && item.stock_name
                    && item.stock_code
                    && isFinite(Number(item.target_price))
                    && (item.direction === 'above' || item.direction === 'below');
            }).map(function(item) {
                return {
                    stock_name: String(item.stock_name),
                    stock_code: String(item.stock_code),
                    target_price: Math.round(Number(item.target_price)),
                    direction: item.direction,
                    created_at: String(item.created_at || new Date().toISOString())
                };
            });
        } catch (e) {
            return [];
        }
    }

    function saveAlerts(alerts) {
        localStorage.setItem(ALERTS_STORAGE_KEY, JSON.stringify(alerts || []));
    }

    function getCurrentStockCode() {
        var codeEl = document.getElementById('stockCode');
        return codeEl ? (codeEl.textContent || '').trim() : '';
    }

    function formatAlertLabel(alert) {
        var symbol = alert.direction === 'above' ? '≥' : '≤';
        return (alert.stock_name || '') + ' ' + symbol + ' ' + Number(alert.target_price || 0).toLocaleString() + '원';
    }

    function renderAlertTags() {
        if (!alertTagsEl) return;
        alertTagsEl.textContent = '';

        var stockCode = getCurrentStockCode();
        if (!stockCode) return;

        var alerts = loadAlerts().filter(function(alert) {
            return alert.stock_code === stockCode;
        });
        if (!alerts.length) return;

        alerts.forEach(function(alert) {
            var tag = document.createElement('span');
            tag.className = 'alert-tag';

            var label = document.createElement('span');
            label.className = 'alert-tag-text';
            label.textContent = formatAlertLabel(alert);

            var removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'alert-remove-btn';
            removeBtn.dataset.createdAt = alert.created_at;
            removeBtn.textContent = 'X';

            tag.appendChild(label);
            tag.appendChild(removeBtn);
            alertTagsEl.appendChild(tag);
        });
    }

    function hideAlertNotification() {
        if (!alertNotificationEl || !alertNotificationTextEl) return;
        alertNotificationTextEl.textContent = '';
        alertNotificationEl.classList.add('hidden');
    }

    function showAlertNotification(message) {
        if (!alertNotificationEl || !alertNotificationTextEl) return;
        alertNotificationTextEl.textContent = message;
        alertNotificationEl.classList.remove('hidden');
    }

    function removeAlertByCreatedAt(createdAt) {
        if (!createdAt) return;
        var alerts = loadAlerts().filter(function(alert) {
            return alert.created_at !== createdAt;
        });
        saveAlerts(alerts);
        renderAlertTags();
    }

    function addPriceAlert() {
        var stockName = (document.getElementById('stockName').textContent || '').trim();
        var stockCode = getCurrentStockCode();
        var targetPrice = parsePriceNumber(alertTargetInput && alertTargetInput.value);
        var direction = alertDirectionSelect ? alertDirectionSelect.value : 'above';

        if (!stockName || !stockCode) {
            showError('먼저 종목을 분석해주세요');
            return;
        }
        if (!targetPrice || targetPrice <= 0) {
            showError('목표가는 0보다 큰 숫자여야 합니다');
            return;
        }

        var alerts = loadAlerts();
        if (alerts.length >= MAX_ALERTS) {
            showError('알림은 최대 10개까지 설정할 수 있습니다');
            return;
        }

        alerts.push({
            stock_name: stockName,
            stock_code: stockCode,
            target_price: targetPrice,
            direction: direction === 'below' ? 'below' : 'above',
            created_at: new Date().toISOString()
        });
        saveAlerts(alerts);
        if (alertTargetInput) alertTargetInput.value = '';
        renderAlertTags();
        errorEl.classList.add('hidden');
    }

    function checkPriceAlerts(data) {
        if (!data) return;
        var stockCode = data.stock_code || '';
        var currentPrice = parsePriceNumber(data.price && data.price.current_price);
        if (!stockCode || currentPrice === null) return;

        var alerts = loadAlerts();
        var triggered = [];
        var remained = [];

        alerts.forEach(function(alert) {
            if (alert.stock_code !== stockCode) {
                remained.push(alert);
                return;
            }
            if (alert.direction === 'above' && currentPrice >= alert.target_price) {
                triggered.push(alert);
                return;
            }
            if (alert.direction === 'below' && currentPrice <= alert.target_price) {
                triggered.push(alert);
                return;
            }
            remained.push(alert);
        });

        if (!triggered.length) {
            hideAlertNotification();
            renderAlertTags();
            return;
        }

        saveAlerts(remained);
        var first = triggered[0];
        var dirLabel = first.direction === 'above' ? '이상' : '이하';
        showAlertNotification('🔔 ' + first.stock_name + '이(가) 목표가 ' + Number(first.target_price).toLocaleString() + '원 ' + dirLabel + '에 도달했습니다! (현재가: ' + currentPrice.toLocaleString() + '원)');
        renderAlertTags();
    }

    autocompleteEl.addEventListener('click', function(e) {
        var item = e.target.closest('.autocomplete-item');
        if (item) {
            searchInput.value = item.dataset.name;
            autocompleteEl.classList.remove('show');
        }
    });

    async function analyzeStock() {
        var name = searchInput.value.trim();
        if (!name) { showError('종목명을 입력해주세요'); return; }

        errorEl.classList.add('hidden');
        resultEl.classList.add('hidden');
        loadingEl.classList.remove('hidden');
        searchBtn.disabled = true;
        agentResultsEl.innerHTML = '';

        try {
            var resp = await fetch('/api/stock?name=' + encodeURIComponent(name));
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.error || '오류가 발생했습니다');

            window.currentStockName = data.stock_name;
            renderStockData(data);
            checkPriceAlerts(data);
        } catch (e) {
            showError(e.message);
        } finally {
            loadingEl.classList.add('hidden');
            searchBtn.disabled = false;
        }
    }

    function renderStockData(data) {
        hideAlertNotification();

        document.getElementById('stockName').textContent = data.stock_name;
        document.getElementById('stockCode').textContent = data.stock_code;
        document.getElementById('stockMarket').textContent = data.market || '';

        var price = data.price || {};
        if (price.current_price) {
            document.getElementById('currentPrice').textContent = price.current_price.toLocaleString() + '원';
            var changeEl = document.getElementById('changeRate');
            var rate = price.change_rate || 0;
            changeEl.textContent = (rate >= 0 ? '+' : '') + rate + '%';
            changeEl.className = 'change ' + (rate > 0 ? 'up' : rate < 0 ? 'down' : 'flat');
        }

        var mc = data.market_cap || {};
        var fund = data.fundamental || {};
        var ind = data.indicators || {};

        document.getElementById('marketCap').textContent = mc.market_cap_text || '-';
        document.getElementById('perValue').textContent = fund.per ? fund.per + '배' : '-';
        document.getElementById('pbrValue').textContent = fund.pbr ? fund.pbr + '배' : '-';
        document.getElementById('divValue').textContent = fund.div_yield ? fund.div_yield + '%' : '-';

        document.getElementById('sma5').textContent = ind.sma5 ? ind.sma5.toLocaleString() : '-';
        document.getElementById('sma20').textContent = ind.sma20 ? ind.sma20.toLocaleString() : '-';
        document.getElementById('sma60').textContent = ind.sma60 ? ind.sma60.toLocaleString() : '-';
        document.getElementById('rsi14').textContent = ind.rsi14 || '-';
        document.getElementById('volRatio').textContent = ind.volume_ratio ? ind.volume_ratio + 'x' : '-';
        document.getElementById('high52').textContent = ind.high_52w ? ind.high_52w.toLocaleString() : '-';
        document.getElementById('low52').textContent = ind.low_52w ? ind.low_52w.toLocaleString() : '-';

        var newsList = document.getElementById('newsList');
        var news = data.news || [];
        if (news.length) {
            newsList.innerHTML = news.map(function(n) {
                var li = '<li><a href="' + escapeHtml(n.url) + '" target="_blank">'
                    + escapeHtml(n.title) + '</a><div class="meta">'
                    + escapeHtml(formatDateKR(n.date)) + '</div></li>';
                return li;
            }).join('');
        } else {
            newsList.innerHTML = '<li>뉴스가 없습니다</li>';
        }

        var discList = document.getElementById('disclosureList');
        var discs = data.disclosures || [];
        if (discs.length) {
            discList.innerHTML = discs.map(function(d) {
                var li = '<li><a href="' + escapeHtml(d.url) + '" target="_blank">'
                    + escapeHtml(d.title) + '</a><div class="meta">'
                    + escapeHtml(formatDateKR(d.date)) + '</div></li>';
                return li;
            }).join('');
        } else {
            discList.innerHTML = '<li>공시가 없습니다</li>';
        }

        chartData = data.chart_data || [];
        initChart();
        var activeBtn = document.querySelector('.period-btn.active');
        renderChart(activeBtn ? activeBtn.dataset.interval : 'daily');

        renderAlertTags();

        resultEl.classList.remove('hidden');
    }

    function getSignalClass(signal) {
        if (signal === '매수' || signal === '안전') return 'positive';
        if (signal === '매도' || signal === '위험') return 'negative';
        return 'neutral';
    }

    async function judgeAgent(agentId) {
        if (!window.currentStockName) return;

        var existing = document.getElementById('result-' + agentId);
        if (existing) existing.remove();

        var card = document.createElement('div');
        card.id = 'result-' + agentId;
        card.className = 'agent-result-card';
        card.innerHTML = '<div class="agent-loading"><div class="progress-text">데이터 수집중...</div><div class="progress-bar"><div class="progress-bar-fill"></div></div></div>';
        agentResultsEl.prepend(card);

        var btn = document.querySelector('[data-agent="' + agentId + '"]');
        if (btn) btn.disabled = true;

        setTimeout(function() {
            var pt = card.querySelector('.progress-text');
            if (pt) pt.textContent = '판단 진행중...';
        }, 2000);

        try {
            var resp = await fetch('/api/judge?agent=' + agentId + '&name=' + encodeURIComponent(window.currentStockName));
            var data = await resp.json();

            var signalClass = getSignalClass(data.signal);
            var checklist = (data.checklist || []).map(function(c) {
                var dotClass = c.pass ? 'pass' : 'fail';
                return '<li class="checklist-item"><span class="check-dot ' + dotClass + '"></span>'
                    + '<div class="check-text"><div class="check-label">' + escapeHtml(c.item) + '</div>'
                    + '<div class="check-reason">' + escapeHtml(c.reason || '') + '</div></div></li>';
            }).join('');

            var html = '<div class="agent-result-header">'
                + '<span class="agent-result-name">' + escapeHtml(data.agent_name || agentId) + '</span>'
                + '<span class="signal-badge ' + signalClass + '"><span class="signal-dot ' + signalClass + '"></span>'
                + escapeHtml(data.signal || '관망') + '</span></div>';

            if (data.confidence) {
                html += '<span class="confidence-tag">확신도: ' + escapeHtml(data.confidence) + '</span>';
            }

            if (checklist) {
                html += '<ul class="checklist">' + checklist + '</ul>';
            }

            if (data.verdict) {
                html += '<div class="verdict-text">' + escapeHtml(data.verdict) + '</div>';
            }

            if (data.psychology_warning) {
                html += '<div class="psychology-warning">' + escapeHtml(data.psychology_warning) + '</div>';
            }

            card.innerHTML = html;
        } catch (e) {
            card.innerHTML = '<div class="agent-result-header"><span class="agent-result-name">'
                + escapeHtml(agentId) + '</span></div>'
                + '<div class="verdict-text">분석 중 오류가 발생했습니다: ' + escapeHtml(e.message) + '</div>';
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function showError(msg) {
        errorEl.textContent = msg;
        errorEl.classList.remove('hidden');
    }

    themeToggle.addEventListener('click', toggleTheme);

    searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function() { searchStocks(e.target.value); }, 200);
    });

    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') { autocompleteEl.classList.remove('show'); analyzeStock(); }
    });

    searchBtn.addEventListener('click', function() {
        autocompleteEl.classList.remove('show');
        analyzeStock();
    });

    if (alertToggleBtn && alertFormEl) {
        alertToggleBtn.addEventListener('click', function() {
            alertFormEl.classList.toggle('hidden');
            if (!alertFormEl.classList.contains('hidden') && alertTargetInput) {
                alertTargetInput.focus();
            }
        });
    }

    if (alertSetBtn) {
        alertSetBtn.addEventListener('click', addPriceAlert);
    }

    if (alertTargetInput) {
        alertTargetInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') addPriceAlert();
        });
    }

    if (alertTagsEl) {
        alertTagsEl.addEventListener('click', function(e) {
            var removeBtn = e.target.closest('.alert-remove-btn');
            if (!removeBtn) return;
            removeAlertByCreatedAt(removeBtn.dataset.createdAt || '');
        });
    }

    if (alertNotificationCloseBtn) {
        alertNotificationCloseBtn.addEventListener('click', hideAlertNotification);
    }

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-wrapper')) autocompleteEl.classList.remove('show');
    });

    document.querySelectorAll('.period-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.period-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            renderChart(btn.dataset.interval);
        });
    });

    document.querySelectorAll('.agent-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            judgeAgent(btn.dataset.agent);
        });
    });

    initTheme();

    // Tooltip for financial terms
    (function() {
        var activeTooltip = null;
        document.addEventListener('click', function(e) {
            var target = e.target.closest('.has-tooltip');
            if (target) {
                e.stopPropagation();
                if (activeTooltip && activeTooltip.parentElement === target) {
                    activeTooltip.remove();
                    activeTooltip = null;
                    return;
                }
                if (activeTooltip) {
                    activeTooltip.remove();
                    activeTooltip = null;
                }
                var text = target.getAttribute('data-tooltip');
                if (!text) return;
                var popup = document.createElement('div');
                popup.className = 'tooltip-popup';
                popup.textContent = text;
                target.appendChild(popup);
                activeTooltip = popup;
            } else if (activeTooltip) {
                activeTooltip.remove();
                activeTooltip = null;
            }
        });
    })();

    (function() {
        var params = new URLSearchParams(window.location.search);
        var name = params.get('name');
        if (name) {
            searchInput.value = name;
            analyzeStock();
        }
    })();
})();
