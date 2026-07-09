// ── Stocker Frontend JS ─────────────────────────────────────────────────────

// Auto-dismiss flash messages after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  // Ticker bar — fetch market data periodically
  updateTicker();
  setInterval(updateTicker, 30000);
});


async function updateTicker() {
  const tickerEl = document.getElementById('tickerBar');
  if (!tickerEl) return;

  try {
    const res = await fetch('/api/stock/AAPL');
    if (!res.ok) return;
    const data = await res.json();
    const stocks = ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN'];
    const results = await Promise.allSettled(
      stocks.map(s => fetch(`/api/stock/${s}`).then(r => r.json()))
    );

    const parts = results
      .filter(r => r.status === 'fulfilled')
      .map(r => {
        const d = r.value;
        const sign = d.change >= 0 ? '▲' : '▼';
        return `${d.symbol} $${d.price.toFixed(2)} ${sign}${Math.abs(d.change_pct)}%`;
      });

    tickerEl.innerHTML = parts.join('  ·  ');
    tickerEl.style.color = '#8b949e';
  } catch (e) {
    // Silent fail
  }
}
