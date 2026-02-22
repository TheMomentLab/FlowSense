(function() {
    'use strict';

    function formatDateKR(str) {
        if (!str) return '';
        var m = String(str).match(/^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})/);
        if (m) return m[1] + '년 ' + m[2] + '월 ' + m[3] + '일';
        return str;
    }

    var searchInput = document.getElementById('searchInput');
    var searchBtn = document.getElementById('searchBtn');
    var autocompleteEl = document.getElementById('autocomplete');
    var themeToggle = document.getElementById('themeToggle');
    var popularGrid = document.getElementById('popularGrid');
    var popularLoading = document.getElementById('popularLoading');
    var heatmapGrid = document.getElementById('heatmapGrid');
    var heatmapState = document.getElementById('heatmapState');
    var digestTextEl = document.getElementById('digestText');
    var digestTopSectorsEl = document.getElementById('digestTopSectors');
    var digestBottomSectorsEl = document.getElementById('digestBottomSectors');
    var digestRefreshBtn = document.getElementById('digestRefreshBtn');
    var whatifStockInput = document.getElementById('whatifStockInput');
    var whatifAmountInput = document.getElementById('whatifAmountInput');
    var whatifDateInput = document.getElementById('whatifDateInput');
    var whatifBtn = document.getElementById('whatifBtn');
    var whatifResult = document.getElementById('whatifResult');
    var whatifAutocompleteEl = document.getElementById('whatifAutocomplete');
    var portfolioSearchInput = document.getElementById('portfolioStockInput');
    var portfolioQtyInput = document.getElementById('portfolioQtyInput');
    var portfolioBuyBtn = document.getElementById('portfolioBuyBtn');
    var portfolioResetBtn = document.getElementById('portfolioResetBtn');
    var portfolioMessage = document.getElementById('portfolioMessage');
    var portfolioCashEl = document.getElementById('portfolioCash');
    var portfolioStockValueEl = document.getElementById('portfolioStockValue');
    var portfolioProfitEl = document.getElementById('portfolioProfit');
    var portfolioHoldingsEl = document.getElementById('portfolioHoldings');
    var portfolioAutocompleteEl = document.getElementById('portfolioAutocomplete');
    var debounceTimer = null;
    var whatifDebounceTimer = null;
    var portfolioDebounceTimer = null;
    var currentCategory = 'volume_top';
    var PORTFOLIO_STORAGE_KEY = 'flowsense_portfolio';
    var INITIAL_CAPITAL = 10000000;

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
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
    }

    function goToAnalyze(name) {
        window.location.href = '/analyze?name=' + encodeURIComponent(name);
    }

    function formatWon(value) {
        return Number(value || 0).toLocaleString() + '원';
    }

    function setHeatmapState(message, isError) {
        if (!heatmapState) return;
        heatmapState.textContent = message || '';
        heatmapState.classList.toggle('error', !!isError);
    }

    function heatmapOpacity(changeRate) {
        var magnitude = Math.min(Math.abs(Number(changeRate) || 0), 5);
        return Math.max(0.2, Math.min(0.8, 0.2 + magnitude * 0.12));
    }

    function setDigestLoading(isLoading) {
        if (!digestRefreshBtn) return;
        digestRefreshBtn.disabled = !!isLoading;
        digestRefreshBtn.textContent = isLoading ? '생성 중...' : '새로 생성';
    }

    function renderDigestTags(container, sectors, typeClass) {
        if (!container) return;
        container.textContent = '';

        if (!Array.isArray(sectors) || !sectors.length) {
            var emptyTag = document.createElement('span');
            emptyTag.className = 'digest-tag ' + typeClass;
            emptyTag.textContent = '데이터 없음';
            container.appendChild(emptyTag);
            return;
        }

        sectors.forEach(function(sector) {
            var tag = document.createElement('span');
            tag.className = 'digest-tag ' + typeClass;
            var name = sector && sector.name ? String(sector.name) : '-';
            var change = Number(sector && sector.change_rate || 0).toFixed(2);
            var sign = Number(change) > 0 ? '+' : '';
            tag.textContent = name + ' ' + sign + change + '%';
            container.appendChild(tag);
        });
    }

    function renderDigestError() {
        if (digestTextEl) digestTextEl.textContent = '시장 요약을 불러올 수 없습니다';
        renderDigestTags(digestTopSectorsEl, [], 'up');
        renderDigestTags(digestBottomSectorsEl, [], 'down');
    }

    async function loadMarketDigest(forceRefresh) {
        if (!digestTextEl) return;
        setDigestLoading(true);
        digestTextEl.textContent = '시장 요약을 생성하는 중...';

        try {
            var url = '/api/digest';
            if (forceRefresh) url += '?no_cache=1';
            var resp = await fetch(url);
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.error || '시장 요약을 불러올 수 없습니다');

            var digestText = data.digest || '시장 요약을 불러올 수 없습니다';
            var generatedAt = data.generated_at || '';
            digestTextEl.textContent = digestText + (generatedAt ? ' (생성: ' + generatedAt + ')' : '');
            renderDigestTags(digestTopSectorsEl, data.top_sectors || [], 'up');
            renderDigestTags(digestBottomSectorsEl, data.bottom_sectors || [], 'down');
        } catch (e) {
            renderDigestError();
        } finally {
            setDigestLoading(false);
        }
    }

    function renderSectorHeatmap(sectors) {
        if (!heatmapGrid) return;
        heatmapGrid.textContent = '';

        if (!Array.isArray(sectors) || !sectors.length) {
            setHeatmapState('표시할 업종 데이터가 없습니다', false);
            return;
        }

        sectors.forEach(function(sector) {
            var changeRate = Number(sector.change_rate || 0);
            var tile = document.createElement('button');
            tile.type = 'button';
            tile.className = 'heatmap-tile';
            tile.classList.add(changeRate > 0 ? 'up' : changeRate < 0 ? 'down' : 'flat');
            tile.style.opacity = String(heatmapOpacity(changeRate));

            var nameEl = document.createElement('span');
            nameEl.className = 'heatmap-name';
            nameEl.textContent = sector.name || '-';

            var changeEl = document.createElement('span');
            changeEl.className = 'heatmap-change';
            changeEl.textContent = (changeRate > 0 ? '+' : '') + changeRate.toFixed(2) + '%';

            tile.appendChild(nameEl);
            tile.appendChild(changeEl);
            heatmapGrid.appendChild(tile);
        });

        setHeatmapState('');
    }

    async function loadSectorHeatmap() {
        if (!heatmapGrid) return;
        setHeatmapState('업종 데이터를 불러오는 중...', false);
        heatmapGrid.textContent = '';

        try {
            var resp = await fetch('/api/sectors');
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.error || '업종 데이터를 불러오지 못했습니다');
            renderSectorHeatmap(data.sectors || []);
        } catch (e) {
            setHeatmapState('업종 데이터를 불러오지 못했습니다', true);
        }
    }

    function setDefaultWhatifDate() {
        if (!whatifDateInput) return;
        var today = new Date();
        var oneYearAgo = new Date();
        oneYearAgo.setFullYear(today.getFullYear() - 1);
        whatifDateInput.max = today.toISOString().slice(0, 10);
        whatifDateInput.value = oneYearAgo.toISOString().slice(0, 10);
    }

    function clearWhatifAutocomplete() {
        if (!whatifAutocompleteEl) return;
        whatifAutocompleteEl.classList.remove('show');
        whatifAutocompleteEl.textContent = '';
    }

    function clearPortfolioAutocomplete() {
        if (!portfolioAutocompleteEl) return;
        portfolioAutocompleteEl.classList.remove('show');
        portfolioAutocompleteEl.textContent = '';
    }

    function setPortfolioMessage(message, isError) {
        if (!portfolioMessage) return;
        portfolioMessage.textContent = message || '';
        portfolioMessage.classList.toggle('error', !!isError);
    }

    async function searchWhatifStocks(query) {
        if (!whatifAutocompleteEl) return;
        if (query.length < 1) {
            clearWhatifAutocomplete();
            return;
        }
        try {
            var resp = await fetch('/api/search?q=' + encodeURIComponent(query));
            var stocks = await resp.json();
            whatifAutocompleteEl.textContent = '';
            if (!stocks.length) {
                whatifAutocompleteEl.classList.remove('show');
                return;
            }

            stocks.forEach(function(s) {
                var item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.dataset.name = s.name || '';

                var nameEl = document.createElement('span');
                nameEl.className = 'name';
                nameEl.textContent = s.name || '';

                var marketEl = document.createElement('span');
                marketEl.className = 'market';
                marketEl.textContent = s.market || '';

                item.appendChild(nameEl);
                item.appendChild(marketEl);
                whatifAutocompleteEl.appendChild(item);
            });

            whatifAutocompleteEl.classList.add('show');
        } catch (e) {
            clearWhatifAutocomplete();
        }
    }

    async function searchPortfolioStocks(query) {
        if (!portfolioAutocompleteEl) return;
        if (query.length < 1) {
            clearPortfolioAutocomplete();
            return;
        }
        try {
            var resp = await fetch('/api/search?q=' + encodeURIComponent(query));
            var stocks = await resp.json();
            portfolioAutocompleteEl.textContent = '';
            if (!stocks.length) {
                portfolioAutocompleteEl.classList.remove('show');
                return;
            }

            stocks.forEach(function(s) {
                var item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.dataset.name = s.name || '';

                var nameEl = document.createElement('span');
                nameEl.className = 'name';
                nameEl.textContent = s.name || '';

                var marketEl = document.createElement('span');
                marketEl.className = 'market';
                marketEl.textContent = s.market || '';

                item.appendChild(nameEl);
                item.appendChild(marketEl);
                portfolioAutocompleteEl.appendChild(item);
            });

            portfolioAutocompleteEl.classList.add('show');
        } catch (e) {
            clearPortfolioAutocomplete();
        }
    }

    function renderWhatifError(message) {
        if (!whatifResult) return;
        whatifResult.classList.add('show');
        whatifResult.textContent = '';

        var errorEl = document.createElement('p');
        errorEl.className = 'whatif-error';
        errorEl.textContent = escapeHtml(message || '계산 중 오류가 발생했습니다');
        whatifResult.appendChild(errorEl);
    }

    function renderWhatifResult(data) {
        if (!whatifResult) return;
        whatifResult.classList.add('show');
        whatifResult.textContent = '';

        var title = document.createElement('h4');
        title.className = 'whatif-result-title';
        title.textContent = (data.stock_name || '') + ' | ' + formatDateKR(data.invest_date || '');

        var rows = document.createElement('div');
        rows.className = 'whatif-result-grid';

        function appendRow(label, value, className) {
            var row = document.createElement('div');
            row.className = 'whatif-row';

            var labelEl = document.createElement('span');
            labelEl.className = 'whatif-label';
            labelEl.textContent = label;

            var valueEl = document.createElement('span');
            valueEl.className = className || 'whatif-value';
            valueEl.textContent = value;

            row.appendChild(labelEl);
            row.appendChild(valueEl);
            rows.appendChild(row);
        }

        var profit = Number(data.profit || 0);
        var isUp = profit >= 0;
        var sign = isUp ? '+' : '';

        appendRow('원금', formatWon(data.invest_amount));
        appendRow('현재 가치', formatWon(data.current_value));
        appendRow('수익/손실', sign + formatWon(profit), 'whatif-profit ' + (isUp ? 'up' : 'down'));
        appendRow('수익률', sign + Number(data.profit_rate || 0).toFixed(2) + '%', 'whatif-profit ' + (isUp ? 'up' : 'down'));

        whatifResult.appendChild(title);
        whatifResult.appendChild(rows);
    }

    async function calculateWhatif() {
        if (!whatifStockInput || !whatifAmountInput || !whatifDateInput) return;

        var name = whatifStockInput.value.trim();
        var amount = parseInt(whatifAmountInput.value, 10);
        var date = whatifDateInput.value;

        if (!name) {
            renderWhatifError('종목명을 입력해주세요');
            return;
        }
        if (!amount || amount <= 0) {
            renderWhatifError('투자 금액은 0보다 큰 숫자여야 합니다');
            return;
        }
        if (!date) {
            renderWhatifError('투자 시작 날짜를 선택해주세요');
            return;
        }

        whatifBtn.disabled = true;
        whatifBtn.textContent = '계산 중...';

        try {
            var url = '/api/whatif?name=' + encodeURIComponent(name)
                + '&amount=' + encodeURIComponent(String(amount))
                + '&date=' + encodeURIComponent(date);
            var resp = await fetch(url);
            var data = await resp.json();

            if (!resp.ok) {
                renderWhatifError(data.error || '계산 중 오류가 발생했습니다');
                return;
            }

            renderWhatifResult(data);
        } catch (e) {
            renderWhatifError('네트워크 오류가 발생했습니다');
        } finally {
            whatifBtn.disabled = false;
            whatifBtn.textContent = '계산하기';
        }
    }

    function getDefaultPortfolio() {
        return {
            cash: INITIAL_CAPITAL,
            holdings: []
        };
    }

    function sanitizePortfolio(raw) {
        if (!raw || typeof raw !== 'object') return getDefaultPortfolio();
        var cash = Number(raw.cash);
        if (!isFinite(cash) || cash < 0) cash = INITIAL_CAPITAL;
        var holdings = Array.isArray(raw.holdings) ? raw.holdings : [];
        holdings = holdings.filter(function(h) {
            return h && h.code && h.name && Number(h.quantity) > 0 && Number(h.avg_price) > 0;
        }).map(function(h) {
            return {
                code: String(h.code),
                name: String(h.name),
                quantity: Math.floor(Number(h.quantity)),
                avg_price: Number(h.avg_price)
            };
        });
        return { cash: cash, holdings: holdings };
    }

    function loadPortfolio() {
        try {
            var parsed = JSON.parse(localStorage.getItem(PORTFOLIO_STORAGE_KEY) || 'null');
            return sanitizePortfolio(parsed);
        } catch (e) {
            return getDefaultPortfolio();
        }
    }

    function savePortfolio(portfolio) {
        localStorage.setItem(PORTFOLIO_STORAGE_KEY, JSON.stringify(portfolio));
    }

    async function fetchStockByName(name) {
        var resp = await fetch('/api/stock?name=' + encodeURIComponent(name));
        var data = await resp.json();
        if (!resp.ok) throw new Error(data.error || '종목 정보를 불러오지 못했습니다');

        var currentPrice = Number(data.price && data.price.current_price);
        if (!isFinite(currentPrice) || currentPrice <= 0) {
            throw new Error('현재가를 확인할 수 없습니다');
        }
        return {
            code: data.stock_code || '',
            name: data.stock_name || name,
            currentPrice: currentPrice
        };
    }

    async function fetchCurrentPriceByHolding(holding) {
        try {
            var stock = await fetchStockByName(holding.name);
            return stock.currentPrice;
        } catch (e) {
            return Number(holding.avg_price || 0);
        }
    }

    async function renderPortfolio() {
        if (!portfolioHoldingsEl) return;
        var portfolio = loadPortfolio();
        var totalStockValue = 0;
        portfolioHoldingsEl.textContent = '';

        if (!portfolio.holdings.length) {
            var emptyEl = document.createElement('p');
            emptyEl.className = 'portfolio-empty';
            emptyEl.textContent = '포트폴리오가 비어있습니다';
            portfolioHoldingsEl.appendChild(emptyEl);
        } else {
            for (var i = 0; i < portfolio.holdings.length; i++) {
                var holding = portfolio.holdings[i];
                var currentPrice = await fetchCurrentPriceByHolding(holding);
                var quantity = Number(holding.quantity || 0);
                var stockValue = currentPrice * quantity;
                var costBasis = Number(holding.avg_price || 0) * quantity;
                var pnl = stockValue - costBasis;
                totalStockValue += stockValue;

                var card = document.createElement('div');
                card.className = 'portfolio-holding';

                var top = document.createElement('div');
                top.className = 'portfolio-holding-top';

                var nameWrap = document.createElement('div');
                nameWrap.className = 'portfolio-holding-name-wrap';

                var nameEl = document.createElement('h4');
                nameEl.className = 'portfolio-holding-name';
                nameEl.textContent = holding.name;

                var metaEl = document.createElement('p');
                metaEl.className = 'portfolio-holding-meta';
                metaEl.textContent = '보유 ' + quantity.toLocaleString() + '주 | 평균가 ' + formatWon(holding.avg_price);

                nameWrap.appendChild(nameEl);
                nameWrap.appendChild(metaEl);

                var sellBtn = document.createElement('button');
                sellBtn.type = 'button';
                sellBtn.className = 'portfolio-sell-btn';
                sellBtn.dataset.code = holding.code;
                sellBtn.textContent = '매도';

                top.appendChild(nameWrap);
                top.appendChild(sellBtn);

                var stats = document.createElement('div');
                stats.className = 'portfolio-holding-stats';

                function createStat(label, value, extraClass) {
                    var stat = document.createElement('div');
                    stat.className = 'portfolio-stat';

                    var labelEl = document.createElement('span');
                    labelEl.className = 'portfolio-stat-label';
                    labelEl.textContent = label;

                    var valueEl = document.createElement('span');
                    valueEl.className = 'portfolio-stat-value' + (extraClass ? ' ' + extraClass : '');
                    valueEl.textContent = value;

                    stat.appendChild(labelEl);
                    stat.appendChild(valueEl);
                    return stat;
                }

                var pnlClass = pnl >= 0 ? 'up' : 'down';
                var sign = pnl >= 0 ? '+' : '';
                stats.appendChild(createStat('현재가', formatWon(currentPrice)));
                stats.appendChild(createStat('평가금액', formatWon(stockValue)));
                stats.appendChild(createStat('손익', sign + formatWon(pnl), pnlClass));

                card.appendChild(top);
                card.appendChild(stats);
                portfolioHoldingsEl.appendChild(card);
            }
        }

        var totalAsset = portfolio.cash + totalStockValue;
        var totalPnl = totalAsset - INITIAL_CAPITAL;
        var totalSign = totalPnl >= 0 ? '+' : '';
        var totalClass = totalPnl >= 0 ? 'up' : 'down';

        if (portfolioCashEl) portfolioCashEl.textContent = formatWon(portfolio.cash);
        if (portfolioStockValueEl) portfolioStockValueEl.textContent = formatWon(totalStockValue);
        if (portfolioProfitEl) {
            portfolioProfitEl.textContent = totalSign + formatWon(totalPnl);
            portfolioProfitEl.classList.remove('up', 'down');
            portfolioProfitEl.classList.add(totalClass);
        }
    }

    async function buyPortfolioStock() {
        if (!portfolioSearchInput || !portfolioQtyInput) return;

        var name = portfolioSearchInput.value.trim();
        var quantity = parseInt(portfolioQtyInput.value, 10);
        if (!name) {
            setPortfolioMessage('종목명을 입력해주세요', true);
            return;
        }
        if (!quantity || quantity <= 0) {
            setPortfolioMessage('수량은 1주 이상 입력해주세요', true);
            return;
        }

        if (portfolioBuyBtn) {
            portfolioBuyBtn.disabled = true;
            portfolioBuyBtn.textContent = '매수 중...';
        }

        try {
            var stock = await fetchStockByName(name);
            var portfolio = loadPortfolio();
            var cost = stock.currentPrice * quantity;

            if (portfolio.cash < cost) {
                setPortfolioMessage('현금이 부족합니다', true);
                return;
            }

            var existing = portfolio.holdings.find(function(h) { return h.code === stock.code; });
            if (existing) {
                var totalQty = Number(existing.quantity) + quantity;
                var totalCost = Number(existing.avg_price) * Number(existing.quantity) + cost;
                existing.quantity = totalQty;
                existing.avg_price = totalCost / totalQty;
                existing.name = stock.name;
            } else {
                portfolio.holdings.push({
                    code: stock.code,
                    name: stock.name,
                    quantity: quantity,
                    avg_price: stock.currentPrice
                });
            }

            portfolio.cash -= cost;
            savePortfolio(portfolio);
            setPortfolioMessage(stock.name + ' ' + quantity + '주 매수 완료', false);
            portfolioQtyInput.value = '1';
            clearPortfolioAutocomplete();
            await renderPortfolio();
        } catch (e) {
            setPortfolioMessage(e.message || '매수 중 오류가 발생했습니다', true);
        } finally {
            if (portfolioBuyBtn) {
                portfolioBuyBtn.disabled = false;
                portfolioBuyBtn.textContent = '매수';
            }
        }
    }

    async function sellPortfolioStock(code) {
        if (!code) return;
        var portfolio = loadPortfolio();
        var index = portfolio.holdings.findIndex(function(h) { return h.code === code; });
        if (index < 0) return;

        var holding = portfolio.holdings[index];
        var currentPrice = await fetchCurrentPriceByHolding(holding);
        var proceeds = currentPrice * Number(holding.quantity || 0);

        portfolio.cash += proceeds;
        portfolio.holdings.splice(index, 1);
        savePortfolio(portfolio);
        setPortfolioMessage(holding.name + ' 전량 매도 완료', false);
        await renderPortfolio();
    }

    function resetPortfolio() {
        savePortfolio(getDefaultPortfolio());
        setPortfolioMessage('포트폴리오를 초기화했습니다', false);
        renderPortfolio();
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

    function formatVolume(vol) {
        if (vol >= 10000) return Math.round(vol / 10000).toLocaleString() + '만';
        return vol.toLocaleString();
    }

    async function loadPopularSummary(code) {
        if (!code) return;
        var summaryEl = popularGrid.querySelector('.popular-card[data-code="' + code + '"] .popular-summary');
        if (!summaryEl) return;
        summaryEl.textContent = 'AI 요약 로딩중...';

        try {
            var resp = await fetch('/api/stock/summary?code=' + encodeURIComponent(code));
            if (!resp.ok) {
                summaryEl.textContent = '';
                return;
            }
            var data = await resp.json();
            if (data && data.summary) {
                summaryEl.textContent = data.summary;
            } else {
                summaryEl.textContent = '';
            }
        } catch (e) {
            summaryEl.textContent = '';
        }
    }

    function loadPopularSummaries(stocks) {
        if (!Array.isArray(stocks)) return;
        stocks.forEach(function(stock) {
            if (!stock || !stock.code) return;
            loadPopularSummary(stock.code);
        });
    }

    async function loadPopularStocks(category) {
        category = category || currentCategory;
        popularGrid.innerHTML = '';
        popularLoading.style.display = 'flex';
        try {
            var resp = await fetch('/api/popular?limit=10&category=' + category);
            var stocks = await resp.json();
            popularLoading.style.display = 'none';

            if (!stocks.length) {
                popularGrid.innerHTML = '<p class="popular-empty">인기 종목을 불러올 수 없습니다</p>';
                return;
            }

            popularGrid.innerHTML = stocks.map(function(s) {
                var sign = s.change_rate >= 0 ? '+' : '';
                var changeClass = s.change_rate > 0 ? 'up' : s.change_rate < 0 ? 'down' : 'flat';
                var rankClass = s.rank <= 3 ? 'top3' : 'other';
                return '<div class="popular-card" data-name="' + escapeHtml(s.name) + '" data-code="' + escapeHtml(s.code) + '">'
                    + '<div class="popular-card-top">'
                    +     '<span class="rank-badge ' + rankClass + '">' + s.rank + '</span>'
                    +     '<div class="popular-stock-info">'
                    +         '<span class="popular-stock-name">' + escapeHtml(s.name) + '</span>'
                    +         '<div class="popular-summary">AI 요약 로딩중...</div>'
                    +         '<span class="popular-stock-code">' + escapeHtml(s.code) + '</span>'
                    +     '</div>'
                    +     '<div class="popular-price-info">'
                    +         '<span class="popular-price">' + s.current_price.toLocaleString() + '원</span>'
                    +         '<span class="change-rate ' + changeClass + '">' + sign + s.change_rate + '%</span>'
                    +     '</div>'
                    + '</div>'
                    + '<div class="volume-bar-wrap">'
                    +     '<div class="volume-bar-bg"><div class="volume-bar-fill" style="width:' + s.volume_ratio + '%"></div></div>'
                    +     '<span class="volume-text">' + formatVolume(s.volume) + '</span>'
                    + '</div>'
                + '</div>';
            }).join('');
            loadPopularSummaries(stocks);
        } catch (e) {
            popularLoading.style.display = 'none';
            popularGrid.innerHTML = '<p class="popular-empty">인기 종목을 불러올 수 없습니다</p>';
        }
    }

    autocompleteEl.addEventListener('click', function(e) {
        var item = e.target.closest('.autocomplete-item');
        if (item) goToAnalyze(item.dataset.name);
    });

    if (whatifAutocompleteEl) {
        whatifAutocompleteEl.addEventListener('click', function(e) {
            var item = e.target.closest('.autocomplete-item');
            if (!item || !whatifStockInput) return;
            whatifStockInput.value = item.dataset.name || '';
            clearWhatifAutocomplete();
        });
    }

    if (portfolioAutocompleteEl) {
        portfolioAutocompleteEl.addEventListener('click', function(e) {
            var item = e.target.closest('.autocomplete-item');
            if (!item || !portfolioSearchInput) return;
            portfolioSearchInput.value = item.dataset.name || '';
            clearPortfolioAutocomplete();
        });
    }

    popularGrid.addEventListener('click', function(e) {
        var card = e.target.closest('.popular-card');
        if (card) goToAnalyze(card.dataset.name);
    });

    themeToggle.addEventListener('click', toggleTheme);

    searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function() { searchStocks(e.target.value); }, 200);
    });

    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            autocompleteEl.classList.remove('show');
            var name = searchInput.value.trim();
            if (name) goToAnalyze(name);
        }
    });

    searchBtn.addEventListener('click', function() {
        autocompleteEl.classList.remove('show');
        var name = searchInput.value.trim();
        if (name) goToAnalyze(name);
    });

    if (whatifStockInput) {
        whatifStockInput.addEventListener('input', function(e) {
            clearTimeout(whatifDebounceTimer);
            whatifDebounceTimer = setTimeout(function() { searchWhatifStocks(e.target.value.trim()); }, 200);
        });
        whatifStockInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                clearWhatifAutocomplete();
                calculateWhatif();
            }
        });
    }

    if (whatifAmountInput) {
        whatifAmountInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') calculateWhatif();
        });
    }

    if (whatifDateInput) {
        whatifDateInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') calculateWhatif();
        });
    }

    if (whatifBtn) {
        whatifBtn.addEventListener('click', function() {
            clearWhatifAutocomplete();
            calculateWhatif();
        });
    }

    if (portfolioSearchInput) {
        portfolioSearchInput.addEventListener('input', function(e) {
            clearTimeout(portfolioDebounceTimer);
            portfolioDebounceTimer = setTimeout(function() { searchPortfolioStocks(e.target.value.trim()); }, 200);
        });
        portfolioSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                clearPortfolioAutocomplete();
                buyPortfolioStock();
            }
        });
    }

    if (portfolioQtyInput) {
        portfolioQtyInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') buyPortfolioStock();
        });
    }

    if (portfolioBuyBtn) {
        portfolioBuyBtn.addEventListener('click', function() {
            clearPortfolioAutocomplete();
            buyPortfolioStock();
        });
    }

    if (portfolioResetBtn) {
        portfolioResetBtn.addEventListener('click', resetPortfolio);
    }

    if (digestRefreshBtn) {
        digestRefreshBtn.addEventListener('click', function() {
            loadMarketDigest(true);
        });
    }

    if (portfolioHoldingsEl) {
        portfolioHoldingsEl.addEventListener('click', function(e) {
            var btn = e.target.closest('.portfolio-sell-btn');
            if (!btn) return;
            sellPortfolioStock(btn.dataset.code || '');
        });
    }

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-wrapper')) autocompleteEl.classList.remove('show');
        if (!e.target.closest('.whatif-stock-wrap')) clearWhatifAutocomplete();
        if (!e.target.closest('.portfolio-stock-wrap')) clearPortfolioAutocomplete();
    });

    document.querySelectorAll('.popular-tab-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.popular-tab-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentCategory = btn.dataset.category;
            loadPopularStocks(currentCategory);
        });
    });

    initTheme();
    loadMarketDigest(false);
    loadSectorHeatmap();
    loadPopularStocks();
    setDefaultWhatifDate();
    renderPortfolio();
})();
