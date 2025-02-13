document.addEventListener('DOMContentLoaded', function() {
    // Initialize performance chart
    const ctx = document.getElementById('performanceChart').getContext('2d');
    let performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Fund NAV',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }, {
                label: 'Benchmark',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ₹${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });

    // Period selector for performance chart
    document.querySelectorAll('[data-period]').forEach(button => {
        button.addEventListener('click', function() {
            document.querySelector('[data-period].active').classList.remove('active');
            this.classList.add('active');
            updatePerformanceData(this.dataset.period);
        });
    });

    // Update performance chart data
    function updatePerformanceData(period) {
        fetch(`/api/fund-performance/${fundId}?period=${period}`)
            .then(response => response.json())
            .then(data => {
                performanceChart.data.labels = data.labels;
                performanceChart.data.datasets[0].data = data.fund_nav;
                performanceChart.data.datasets[1].data = data.benchmark;
                performanceChart.update();
                updateReturnsTable(data.returns);
            });
    }

    // Update returns table
    function updateReturnsTable(returns) {
        const tbody = document.getElementById('returnsTable');
        tbody.innerHTML = Object.entries(returns).map(([period, data]) => `
            <tr>
                <td>${period}</td>
                <td class="${data.fund >= 0 ? 'text-success' : 'text-danger'}">
                    ${data.fund.toFixed(2)}%
                </td>
                <td>${data.category.toFixed(2)}%</td>
                <td>${data.benchmark.toFixed(2)}%</td>
            </tr>
        `).join('');
    }

    // SIP Calculator
    document.getElementById('calculateSIP').addEventListener('click', function() {
        const amount = parseFloat(document.getElementById('sipAmount').value);
        const period = parseInt(document.getElementById('sipPeriod').value);
        const rate = parseFloat(document.getElementById('sipReturn').value);
        
        const monthlyRate = rate / (12 * 100);
        const months = period * 12;
        const invested = amount * months;
        
        // Calculate future value using SIP formula
        const futureValue = amount * (Math.pow(1 + monthlyRate, months) - 1) / monthlyRate * (1 + monthlyRate);
        const returns = futureValue - invested;
        
        document.getElementById('sipResults').innerHTML = `
            <div class="mb-2">
                <strong>Total Investment:</strong> ₹${invested.toFixed(2)}
            </div>
            <div class="mb-2">
                <strong>Expected Returns:</strong> ₹${returns.toFixed(2)}
            </div>
            <div class="mb-2">
                <strong>Future Value:</strong> ₹${futureValue.toFixed(2)}
            </div>
            <div>
                <strong>Absolute Returns:</strong> ${((returns/invested)*100).toFixed(2)}%
            </div>
        `;
    });

    // Buy Fund
    document.getElementById('confirmBuy').addEventListener('click', async function() {
        const amount = parseFloat(document.getElementById('buyAmount').value);
        if (!amount || amount < minInvestment) {
            alert(`Minimum investment amount is ₹${minInvestment}`);
            return;
        }

        try {
            const response = await fetch('/api/create-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fund_id: fundId,
                    amount: amount
                })
            });

            const data = await response.json();
            if (data.error) {
                alert(data.error);
                return;
            }

            const options = {
                key: data.key,
                amount: data.amount * 100,
                currency: "INR",
                name: "Mutual Fund Platform",
                description: `Investment in ${fundName}`,
                order_id: data.order_id,
                handler: async function(response) {
                    try {
                        const verifyResponse = await fetch('/api/verify-payment', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                payment_id: data.id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature,
                                fund_id: fundId
                            })
                        });

                        const verifyData = await verifyResponse.json();
                        if (verifyData.error) {
                            alert(verifyData.error);
                            return;
                        }

                        window.location.reload();
                    } catch (error) {
                        alert('Error processing payment verification');
                    }
                }
            };

            const rzp = new Razorpay(options);
            rzp.open();
            
        } catch (error) {
            alert('Error creating payment order');
        }
    });

    // Sell Fund
    document.getElementById('confirmSell').addEventListener('click', async function() {
        const units = parseFloat(document.getElementById('sellUnits').value);
        const availableUnits = parseFloat(document.getElementById('availableUnits').textContent);

        if (!units || units <= 0 || units > availableUnits) {
            alert('Please enter a valid number of units to sell');
            return;
        }

        try {
            const response = await fetch('/api/sell-units', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fund_id: fundId,
                    units: units
                })
            });

            const data = await response.json();
            if (data.error) {
                alert(data.error);
                return;
            }

            window.location.reload();
        } catch (error) {
            alert('Error processing sale');
        }
    });

    // Start SIP
    document.getElementById('confirmSIP').addEventListener('click', async function() {
        const amount = parseFloat(document.getElementById('monthlySIP').value);
        const sipDate = document.getElementById('sipDate').value;

        if (!amount || amount < minSIPAmount) {
            alert(`Minimum SIP amount is ₹${minSIPAmount}`);
            return;
        }

        try {
            const response = await fetch('/api/create-sip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fund_id: fundId,
                    amount: amount,
                    sip_date: sipDate
                })
            });

            const data = await response.json();
            if (data.error) {
                alert(data.error);
                return;
            }

            alert('SIP has been set up successfully!');
            window.location.reload();
        } catch (error) {
            alert('Error setting up SIP');
        }
    });

    // Initialize with 1Y data
    updatePerformanceData('1Y');
});
