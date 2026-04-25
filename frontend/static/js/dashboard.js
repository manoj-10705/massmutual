/**
 * MassMutual Financial Intelligence Dashboard
 * ============================================
 * Extracted from inline HTML. Handles:
 *  - Tab navigation
 *  - KPI loading with count-up animation
 *  - Chart rendering (candlestick, volatility, volume, returns, GDP)
 *  - WebSocket real-time price updates
 *  - AI chat panel
 *  - Alert feed
 *  - Command palette (Ctrl+K)
 */

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initCommandPalette();
    loadKPIs();
    loadDailyData();
    loadVolatilityData();
    loadMonthlyData();
    loadAlerts();
    checkAIStatus();
    initWebSocket();
    initAIChat();
    initTickerSelector();

    // Refresh alerts every 60s
    setInterval(loadAlerts, 60000);
});

// ============================================
// TAB NAVIGATION
// ============================================

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });

    // Handle URL hash
    const hash = window.location.hash.replace('#', '');
    if (hash) switchTab(hash);
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

    const btn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
    const panel = document.getElementById(`tab-${tab}`);

    if (btn) btn.classList.add('active');
    if (panel) panel.classList.add('active');
    window.location.hash = tab;

    // Load analysis charts on first visit
    if (tab === 'analysis' && !window._analysisLoaded) {
        loadAnalysisCharts();
        window._analysisLoaded = true;
    }
}

// ============================================
// KPI LOADING + COUNT-UP ANIMATION
// ============================================

function animateValue(el, start, end, duration, format) {
    el.classList.remove('skeleton');
    const range = end - start;
    const startTime = performance.now();

    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const current = start + range * eased;
        el.textContent = format(current);
        if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
}

function formatCurrency(n) {
    return 'RM ' + n.toFixed(2);
}

function formatBillions(n) {
    return (n / 1e9).toFixed(1) + 'B';
}

function formatPercent(n) {
    return n.toFixed(2) + '%';
}

function formatNumber(n) {
    return n.toLocaleString('en-MY', { maximumFractionDigits: 4 });
}

async function loadKPIs() {
    try {
        const res = await fetch('/api/kpis');
        const json = await res.json();
        if (json.status !== 'ok') throw new Error(json.message);

        const data = json.data;
        const years = {};

        // Group by year for YoY calculation
        for (const [metric, values] of Object.entries(data)) {
            for (const v of values) {
                if (!years[v.year]) years[v.year] = {};
                years[v.year][metric] = v.value;
            }
        }

        const sortedYears = Object.keys(years).sort((a, b) => b - a);
        const latest = years[sortedYears[0]] || {};
        const prev = years[sortedYears[1]] || {};

        // Populate year filter
        const filter = document.getElementById('yearFilter');
        sortedYears.forEach(y => {
            const opt = document.createElement('option');
            opt.value = y;
            opt.textContent = y;
            filter.appendChild(opt);
        });
        filter.addEventListener('change', () => {
            const selectedYear = filter.value;
            loadDailyData(selectedYear, currentTicker);
            loadVolatilityData(selectedYear, currentTicker);
            loadMonthlyData(selectedYear); // Monthly is global/aggregate for now
            loadAlerts(selectedYear, currentTicker);
            updateKPIs(selectedYear, years);
        });

        // Initialize KPIs with latest year
        updateKPIs(sortedYears[0], years);

    } catch (err) {
        console.error('Failed to load KPIs:', err);
        document.querySelectorAll('.kpi-value.skeleton').forEach(el => {
            el.classList.remove('skeleton');
            el.textContent = 'Error';
        });
    }
}

function updateKPIs(selectedYearStr, yearsData) {
    const sortedYears = Object.keys(yearsData).sort((a, b) => b - a);
    const selectedIdx = sortedYears.indexOf(selectedYearStr);
    
    const current = yearsData[selectedYearStr] || {};
    // Compare to the year before the selected year (if available)
    const prev = (selectedIdx !== -1 && selectedIdx + 1 < sortedYears.length) 
        ? yearsData[sortedYears[selectedIdx + 1]] 
        : {};

    const kpiMap = {
        'AVG_CLOSE': { el: 'kpiAvgCloseValue', change: 'kpiAvgCloseChange', fmt: formatCurrency },
        'AVG_GDP': { el: 'kpiGdpValue', change: 'kpiGdpChange', fmt: formatBillions },
        'AVG_INFLATION': { el: 'kpiInflationValue', change: 'kpiInflationChange', fmt: formatPercent },
        'YEARLY_VOLATILITY': { el: 'kpiVolatilityValue', change: 'kpiVolatilityChange', fmt: formatNumber },
    };

    for (const [metric, cfg] of Object.entries(kpiMap)) {
        const el = document.getElementById(cfg.el);
        const changeEl = document.getElementById(cfg.change);
        const val = current[metric];
        const prevVal = prev[metric];

        if (val !== undefined && val !== null) {
            animateValue(el, 0, val, 1200, cfg.fmt);

            if (prevVal) {
                const pctChange = ((val - prevVal) / Math.abs(prevVal)) * 100;
                const arrow = pctChange >= 0 ? '↑' : '↓';
                changeEl.textContent = `${arrow} ${Math.abs(pctChange).toFixed(1)}% YoY`;
                changeEl.className = `kpi-change ${pctChange >= 0 ? 'positive' : 'negative'}`;
            } else {
                changeEl.textContent = 'No prior data';
                changeEl.className = 'kpi-change';
            }
        } else {
            el.classList.remove('skeleton');
            el.textContent = '—';
            changeEl.textContent = '';
        }
    }
}

// ============================================
// CANDLESTICK CHART
// ============================================

let lwChart = null;
let candlestickSeries = null;
let volumeSeries = null;
let volatilityChart = null;
let vol7Series = null;
let vol30Series = null;
let chartDataRange = { first: null, last: null };

async function loadDailyData(year, ticker = '1155.KL') {
    try {
        // Always load ALL data for the ticker (no year filter to API).
        // Year navigation is handled client-side via setVisibleRange.
        const url = `/api/daily?ticker=${encodeURIComponent(ticker)}`;
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'ok') throw new Error(json.message);

        const container = document.getElementById('candlestickChart');

        if (!lwChart) {
            lwChart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: 400,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#94a3b8',
                    fontFamily: 'Inter, sans-serif',
                },
                grid: {
                    vertLines: { color: 'rgba(255,255,255,0.04)' },
                    horzLines: { color: 'rgba(255,255,255,0.04)' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                    vertLine: { color: 'rgba(0, 212, 170, 0.3)', style: 2 },
                    horzLine: { color: 'rgba(0, 212, 170, 0.3)', style: 2 },
                },
                timeScale: {
                    borderColor: 'rgba(255,255,255,0.08)',
                    timeVisible: true,
                    rightOffset: 5,
                },
                handleScroll: { mouseWheel: true, pressedMouseMove: true },
                handleScale: { mouseWheel: true, pinch: true },
            });

            candlestickSeries = lwChart.addCandlestickSeries({
                upColor: '#00d4aa',
                downColor: '#ef4444',
                borderDownColor: '#ef4444',
                borderUpColor: '#00d4aa',
                wickDownColor: '#ef4444',
                wickUpColor: '#00d4aa',
            });

            volumeSeries = lwChart.addHistogramSeries({
                color: '#26a69a',
                priceFormat: { type: 'volume' },
                priceScaleId: '',
            });

            lwChart.priceScale('').applyOptions({
                scaleMargins: { top: 0.8, bottom: 0 },
            });

            // Resize handler
            new ResizeObserver(entries => {
                if (entries.length > 0) {
                    lwChart.resize(entries[0].contentRect.width, 400);
                }
            }).observe(container);

            // Sync volatility chart when candlestick scrolls
            lwChart.timeScale().subscribeVisibleTimeRangeChange(range => {
                if (volatilityChart && range) {
                    try { volatilityChart.timeScale().setVisibleRange(range); } catch(e) {}
                }
            });
        }

        const candleData = json.data
            .filter(d => d.date && d.open != null && d.high != null && d.low != null && d.close != null)
            .map(d => ({
                time: d.date,
                open: d.open,
                high: d.high,
                low: d.low,
                close: d.close,
            }));

        const volData = json.data
            .filter(d => d.date && d.volume)
            .map(d => ({
                time: d.date,
                value: d.volume,
                color: (d.close >= d.open) ? 'rgba(0, 212, 170, 0.3)' : 'rgba(239, 68, 68, 0.3)',
            }));

        candlestickSeries.setData(candleData);
        volumeSeries.setData(volData);

        // Track actual data boundaries
        if (candleData.length > 0) {
            chartDataRange.first = candleData[0].time;
            chartDataRange.last = candleData[candleData.length - 1].time;
        }

        // Navigate to selected year — but clamp to actual data boundaries
        if (year && year !== '' && candleData.length > 0) {
            const firstYear = parseInt(chartDataRange.first.substring(0, 4));
            const lastYear = parseInt(chartDataRange.last.substring(0, 4));
            const requestedYear = parseInt(year);

            if (requestedYear > lastYear) {
                // Year is beyond data — show the last available year instead
                lwChart.timeScale().setVisibleRange({
                    from: `${lastYear}-01-01`,
                    to: chartDataRange.last,
                });
            } else if (requestedYear < firstYear) {
                // Year is before data — show the first available year
                lwChart.timeScale().setVisibleRange({
                    from: chartDataRange.first,
                    to: `${firstYear}-12-31`,
                });
            } else {
                // Year is within data — show it
                lwChart.timeScale().setVisibleRange({
                    from: `${year}-01-01`,
                    to: `${year}-12-31`,
                });
            }
        } else {
            lwChart.timeScale().fitContent();
        }

        document.getElementById('statusBatch').classList.add('status-ok');
    } catch (err) {
        console.error('Failed to load daily data:', err);
    }
}

// ============================================
// VOLATILITY CHART
// ============================================

async function loadVolatilityData(year, ticker = '1155.KL') {
    try {
        const url = ticker ? `/api/volatility?ticker=${ticker}` : '/api/volatility';
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'ok') throw new Error(json.message);

        const container = document.getElementById('volatilityChart');

        if (!volatilityChart) {
            volatilityChart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: 300,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#94a3b8',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                timeScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    timeVisible: true,
                },
            });

            vol7Series = volatilityChart.addLineSeries({ color: '#10b981', lineWidth: 2, title: '7-Day Vol' });
            vol30Series = volatilityChart.addLineSeries({ color: '#06b6d4', lineWidth: 2, title: '30-Day Vol' });

            // Sync logic
            volatilityChart.timeScale().subscribeVisibleTimeRangeChange(range => {
                if (lwChart && range) {
                    lwChart.timeScale().setVisibleRange(range);
                }
            });

            new ResizeObserver(entries => {
                if (entries.length > 0) {
                    volatilityChart.resize(entries[0].contentRect.width, 300);
                }
            }).observe(container);
        }

        const vol7Data = json.data.map(d => ({ time: d.date, value: d.vol_7d }));
        const vol30Data = json.data.map(d => ({ time: d.date, value: d.vol_30d }));

        vol7Series.setData(vol7Data);
        vol30Series.setData(vol30Data);

        if (year && year !== '') {
            volatilityChart.timeScale().setVisibleRange({
                from: `${year}-01-01`,
                to: `${year}-12-31`,
            });
        }
    } catch (err) {
        console.error('Failed to load volatility:', err);
    }
}

// ============================================
// MONTHLY VOLUME CHART
// ============================================

let volumeChartInstance = null;

async function loadMonthlyData(year) {
    try {
        const url = year ? `/api/monthly?year=${year}` : '/api/monthly';
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'ok') throw new Error(json.message);

        const ctx = document.getElementById('volumeChart');
        if (volumeChartInstance) volumeChartInstance.destroy();

        const months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const labels = json.data.map(d => `${months[d.month]} ${d.year}`);
        const volumes = json.data.map(d => d.total_volume);

        volumeChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Monthly Volume',
                    data: volumes,
                    backgroundColor: json.data.map((_, i) => {
                        const hue = 170 + (i % 12) * 10;
                        return `hsla(${hue}, 80%, 50%, 0.6)`;
                    }),
                    borderRadius: 4,
                    borderSkipped: false,
                }],
            },
            options: chartOptions('Volume'),
        });
    } catch (err) {
        console.error('Failed to load monthly:', err);
    }
}

// ============================================
// ANALYSIS TAB CHARTS
// ============================================

async function loadAnalysisCharts() {
    try {
        const res = await fetch('/api/daily');
        const json = await res.json();
        if (json.status !== 'ok') return;

        // Daily Returns Distribution (Histogram approximation)
        const returns = json.data
            .filter(d => d.daily_return !== null)
            .map(d => d.daily_return * 100);

        const bins = {};
        for (const r of returns) {
            const bin = (Math.round(r * 4) / 4).toFixed(2);
            bins[bin] = (bins[bin] || 0) + 1;
        }
        const sortedBins = Object.keys(bins).sort((a, b) => a - b);

        new Chart(document.getElementById('returnsChart'), {
            type: 'bar',
            data: {
                labels: sortedBins.map(b => b + '%'),
                datasets: [{
                    label: 'Frequency',
                    data: sortedBins.map(b => bins[b]),
                    backgroundColor: sortedBins.map(b =>
                        parseFloat(b) >= 0 ? 'rgba(0, 212, 170, 0.6)' : 'rgba(239, 68, 68, 0.6)'
                    ),
                    borderRadius: 2,
                }],
            },
            options: chartOptions('Count'),
        });

        // GDP vs Close
        const withGdp = json.data.filter(d => d.gdp && d.close);
        new Chart(document.getElementById('gdpChart'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'GDP vs Close Price',
                    data: withGdp.map(d => ({ x: d.gdp / 1e9, y: d.close })),
                    backgroundColor: 'rgba(139, 92, 246, 0.5)',
                    borderColor: '#8b5cf6',
                    pointRadius: 2,
                }],
            },
            options: {
                ...chartOptions('Close Price (RM)'),
                scales: {
                    x: {
                        title: { display: true, text: 'GDP (Billion RM)', color: '#94a3b8' },
                        ticks: { color: '#64748b' },
                        grid: { color: 'rgba(255,255,255,0.04)' },
                    },
                    y: {
                        title: { display: true, text: 'Close Price (RM)', color: '#94a3b8' },
                        ticks: { color: '#64748b' },
                        grid: { color: 'rgba(255,255,255,0.04)' },
                    },
                },
            },
        });
    } catch (err) {
        console.error('Failed to load analysis charts:', err);
    }
}

// ============================================
// SHARED CHART OPTIONS
// ============================================

function chartOptions(yLabel) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                labels: { color: '#94a3b8', font: { family: 'Inter' } },
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f1f5f9',
                bodyColor: '#94a3b8',
                borderColor: 'rgba(255,255,255,0.1)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
            },
        },
        scales: {
            x: {
                ticks: { color: '#64748b', maxTicksLimit: 12, font: { size: 10 } },
                grid: { color: 'rgba(255,255,255,0.04)' },
            },
            y: {
                title: { display: true, text: yLabel, color: '#94a3b8' },
                ticks: { color: '#64748b' },
                grid: { color: 'rgba(255,255,255,0.04)' },
            },
        },
    };
}

// ============================================
// ALERT FEED
// ============================================

async function loadAlerts(year, ticker = '1155.KL') {
    try {
        let url = `/api/anomalies?ticker=${ticker}`;
        if (year) url += `&year=${year}`;
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'ok') return;

        const feed = document.getElementById('alertFeed');

        if (!json.data || json.data.length === 0) {
            feed.innerHTML = '<div class="alert-empty"><span>No anomalies detected for ' + ticker + '</span></div>';
            return;
        }

        feed.innerHTML = json.data.map(a => {
            const icon = a.severity === 'critical' ? '🔴' : a.severity === 'warning' ? '⚠️' : 'ℹ️';
            const time = a.detected_at ? new Date(a.detected_at).toLocaleString() : '';
            return `
                <div class="alert-item ${a.severity}">
                    <div>${icon} ${a.message}</div>
                    <div class="alert-time">${time}</div>
                </div>`;
        }).join('');

    } catch (err) {
        // Silently fail — alerts are non-critical
    }
}

// ============================================
// AI STATUS
// ============================================

async function checkAIStatus() {
    try {
        const res = await fetch('/ready');
        const json = await res.json();
        const aiEl = document.getElementById('kpiAiStatusValue');
        const detailEl = document.getElementById('kpiAiStatusDetail');

        if (json.checks?.ai_analyst === 'available') {
            aiEl.textContent = '✅ Active';
            aiEl.style.color = '#00d4aa';
            detailEl.textContent = 'Ask anything about the data';
            document.getElementById('statusAi').classList.add('status-ok');
        } else {
            aiEl.textContent = '⚙️ Not configured';
            aiEl.style.color = '#f59e0b';
            detailEl.textContent = 'Set GEMINI_API_KEY in .env';
        }
    } catch {
        document.getElementById('kpiAiStatusValue').textContent = '—';
    }
}

// ============================================
// WEBSOCKET (Real-Time Prices)
// ============================================

function initWebSocket() {
    try {
        const socket = io({
            transports: ['websocket', 'polling'],
            reconnectionAttempts: 10,
            reconnectionDelay: 3000,
        });
        window.mmSocket = socket;
        console.log('WebSocket initialized');

        const badge = document.getElementById('liveBadge');
        const dot = badge.querySelector('.live-dot');
        const text = badge.querySelector('.live-text');

        socket.on('connect', () => {
            dot.classList.add('connected');
            text.textContent = 'Live';
            const ticker = document.getElementById('tickerSelector')?.value || '1155.KL';
            socket.emit('subscribe_prices', { ticker: ticker });
            document.getElementById('statusStream').classList.add('status-ok');
        });

        socket.on('disconnect', () => {
            dot.classList.remove('connected');
            text.textContent = 'Disconnected';
            document.getElementById('statusStream').classList.remove('status-ok');
        });

        socket.on('price_update', (data) => {
            if (data && data.price && candlestickSeries) {
                // Update candlestick with latest tick
                const now = new Date();
                const dateStr = now.toISOString().split('T')[0];
                candlestickSeries.update({
                    time: dateStr,
                    open: parseFloat(data.price),
                    high: parseFloat(data.price),
                    low: parseFloat(data.price),
                    close: parseFloat(data.price),
                });
            }
        });

    } catch (err) {
        console.warn('WebSocket init failed:', err);
    }
}

// ============================================
// AI CHAT
// ============================================

let aiChartInstance = null;

function initAIChat() {
    const input = document.getElementById('aiInput');
    const sendBtn = document.getElementById('aiSendBtn');

    sendBtn.addEventListener('click', () => sendAIQuery());
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendAIQuery();
    });

    // Suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            input.value = chip.dataset.question;
            sendAIQuery();
        });
    });
}

async function sendAIQuery() {
    const input = document.getElementById('aiInput');
    const question = input.value.trim();
    if (!question) return;

    const messages = document.getElementById('aiChatMessages');
    const sendBtn = document.getElementById('aiSendBtn');

    // Add user message
    messages.innerHTML += `
        <div class="ai-message user">
            <div class="ai-avatar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div class="ai-bubble"><p>${escapeHtml(question)}</p></div>
        </div>`;

    // Show typing indicator
    messages.innerHTML += `
        <div class="ai-message ai-typing-msg">
            <div class="ai-avatar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
            </div>
            <div class="ai-bubble">
                <div class="ai-typing"><span></span><span></span><span></span></div>
            </div>
        </div>`;

    messages.scrollTop = messages.scrollHeight;
    input.value = '';
    sendBtn.disabled = true;

    try {
        const res = await fetch('/api/ai/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });
        const json = await res.json();

        // Remove typing indicator
        const typingMsg = messages.querySelector('.ai-typing-msg');
        if (typingMsg) typingMsg.remove();

        // Optional: you can log the SQL to console if needed for debugging
        if (json.sql) console.debug('AI Executed SQL:', json.sql);

        const latency = json.latency_ms ? `<span style="color:#64748b;font-size:0.7rem">(${json.latency_ms}ms)</span>` : '';

        messages.innerHTML += `
            <div class="ai-message">
                <div class="ai-avatar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
                </div>
                <div class="ai-bubble">
                    <p>${formatAnalysis(json.analysis || json.message || 'No response')}</p>
                    ${latency}
                </div>
            </div>`;

        // Render chart if suggested
        if (json.chart) renderAIChart(json.chart);

    } catch (err) {
        const typingMsg = messages.querySelector('.ai-typing-msg');
        if (typingMsg) typingMsg.remove();

        messages.innerHTML += `
            <div class="ai-message">
                <div class="ai-avatar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
                </div>
                <div class="ai-bubble" style="border-color:rgba(239,68,68,0.3)">
                    <p>Sorry, I encountered an error: ${escapeHtml(err.message)}</p>
                </div>
            </div>`;
    }

    sendBtn.disabled = false;
    messages.scrollTop = messages.scrollHeight;
}

function renderAIChart(chart) {
    const panel = document.getElementById('aiChartPanel');
    const title = document.getElementById('aiChartTitle');
    const ctx = document.getElementById('aiChart');

    panel.style.display = 'block';
    title.textContent = chart.title || 'AI Generated Chart';

    if (aiChartInstance) aiChartInstance.destroy();

    aiChartInstance = new Chart(ctx, {
        type: chart.type || 'bar',
        data: {
            labels: chart.labels || [],
            datasets: [{
                label: chart.y_label || 'Value',
                data: chart.values || [],
                backgroundColor: 'rgba(6, 182, 212, 0.6)',
                borderColor: '#06b6d4',
                borderWidth: 1,
                borderRadius: 4,
            }],
        },
        options: chartOptions(chart.y_label || 'Value'),
    });
}

function formatAnalysis(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ============================================
// COMMAND PALETTE (Ctrl+K)
// ============================================

function initCommandPalette() {
    const overlay = document.getElementById('cmdPaletteOverlay');
    const input = document.getElementById('cmdPaletteInput');
    const btn = document.getElementById('cmdPaletteBtn');

    function toggle() {
        const visible = overlay.style.display !== 'none';
        overlay.style.display = visible ? 'none' : 'flex';
        if (!visible) {
            input.value = '';
            input.focus();
        }
    }

    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggle();
        }
        if (e.key === 'Escape') overlay.style.display = 'none';
    });

    btn.addEventListener('click', toggle);
    overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.style.display = 'none';
    });

    // Filter results
    input.addEventListener('input', () => {
        const query = input.value.toLowerCase();
        document.querySelectorAll('.cmd-result').forEach(r => {
            r.style.display = r.textContent.toLowerCase().includes(query) ? 'block' : 'none';
        });
    });

    // Handle result clicks
    document.querySelectorAll('.cmd-result').forEach(r => {
        r.addEventListener('click', () => {
            const action = r.dataset.action;
            overlay.style.display = 'none';

            if (action.startsWith('tab:')) {
                switchTab(action.split(':')[1]);
            } else if (action.startsWith('filter:')) {
                document.getElementById('yearFilter').value = action.split(':')[1];
                loadDailyData(action.split(':')[1]);
            }
        });
    });
}

let currentTicker = '1155.KL';

function initTickerSelector() {
    const selector = document.getElementById('tickerSelector');
    if (!selector) return;

    selector.addEventListener('change', () => {
        const newTicker = selector.value;
        const oldTicker = currentTicker;
        currentTicker = newTicker;

        // Update UI
        const chartTitle = document.querySelector('#candlestickCard .chart-title');
        if (chartTitle) {
            chartTitle.textContent = selector.options[selector.selectedIndex].text + ' — Price';
        }

        // Resubscribe WebSocket
        // We need to store the socket globally
        if (window.mmSocket) {
            window.mmSocket.emit('unsubscribe_prices', { ticker: oldTicker });
            window.mmSocket.emit('subscribe_prices', { ticker: newTicker });
        }

        // Reload all charts for new ticker
        const year = document.getElementById('yearFilter').value;
        loadDailyData(year, newTicker);
        loadVolatilityData(year, newTicker);
        loadAlerts(year, newTicker);
    });
}
