document.addEventListener('DOMContentLoaded', function() {
    // Fetch portfolio data
    fetch('/api/portfolio-data')
        .then(response => response.json())
        .then(data => {
            initializePortfolioChart(data);
            updatePortfolioStats(data);
            updateHoldingsTable(data);
        });
});

function updatePortfolioStats(data) {
    const totalValue = data.reduce((sum, item) => sum + item.current_value, 0);
    const totalInvestment = data.reduce((sum, item) => sum + item.purchase_value, 0);
    const returns = ((totalValue - totalInvestment) / totalInvestment * 100).toFixed(2);
    
    const statsHtml = `
        <div class="list-group list-group-flush">
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span>Total Value:</span>
                <span>₹${totalValue.toFixed(2)}</span>
            </div>
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span>Total Investment:</span>
                <span>₹${totalInvestment.toFixed(2)}</span>
            </div>
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span>Returns:</span>
                <span class="${returns >= 0 ? 'text-success' : 'text-danger'}">
                    ${returns}%
                </span>
            </div>
        </div>
    `;
    
    document.getElementById('portfolioStats').innerHTML = statsHtml;
}

function updateHoldingsTable(data) {
    const tableHtml = data.map(item => `
        <tr>
            <td>${item.fund_name}</td>
            <td>${item.units.toFixed(2)}</td>
            <td>₹${(item.current_value / item.units).toFixed(2)}</td>
            <td>₹${item.current_value.toFixed(2)}</td>
            <td>₹${item.purchase_value.toFixed(2)}</td>
            <td class="${item.current_value >= item.purchase_value ? 'text-success' : 'text-danger'}">
                ${((item.current_value - item.purchase_value) / item.purchase_value * 100).toFixed(2)}%
            </td>
        </tr>
    `).join('');
    
    document.getElementById('holdingsTable').innerHTML = tableHtml;
}
