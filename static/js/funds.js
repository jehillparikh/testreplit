document.addEventListener('DOMContentLoaded', function() {
    const fundSearch = document.getElementById('fundSearch');
    const categoryFilter = document.getElementById('categoryFilter');
    const riskFilter = document.getElementById('riskFilter');
    const investModal = new bootstrap.Modal(document.getElementById('investModal'));
    const successModal = new bootstrap.Modal(document.getElementById('successModal'));

    let selectedFundId = null;
    let selectedFundName = null;
    let minInvestmentAmount = 0;

    // Search and filter functionality
    function filterFunds() {
        const searchTerm = fundSearch.value.toLowerCase();
        const category = categoryFilter.value;
        const risk = riskFilter.value;

        const rows = document.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const name = row.cells[0].textContent.toLowerCase();
            const fundCategory = row.cells[2].textContent;
            const riskLevel = row.cells[5].textContent;

            const matchesSearch = name.includes(searchTerm);
            const matchesCategory = !category || fundCategory === category;
            const matchesRisk = !risk || riskLevel === risk;

            row.style.display = matchesSearch && matchesCategory && matchesRisk ? '' : 'none';
        });
    }

    fundSearch.addEventListener('input', filterFunds);
    categoryFilter.addEventListener('change', filterFunds);
    riskFilter.addEventListener('change', filterFunds);

    // Investment handling
    document.querySelectorAll('.invest-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            selectedFundId = this.dataset.fundId;
            selectedFundName = this.dataset.fundName;
            minInvestmentAmount = parseFloat(this.dataset.minInvestment);

            document.getElementById('fundName').textContent = selectedFundName;
            document.getElementById('minInvestment').textContent = minInvestmentAmount.toFixed(2);
            document.getElementById('investAmount').min = minInvestmentAmount;

            investModal.show();
        });
    });

    document.getElementById('confirmInvest').addEventListener('click', async function() {
        const amount = parseFloat(document.getElementById('investAmount').value);

        if (amount < minInvestmentAmount) {
            alert(`Minimum investment amount is ₹${minInvestmentAmount}`);
            return;
        }

        try {
            // Create payment order
            const response = await fetch('/api/create-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fund_id: selectedFundId,
                    amount: amount
                })
            });

            const data = await response.json();
            if (data.error) {
                alert(data.error);
                return;
            }

            // Initialize RazorPay
            const options = {
                key: data.key,
                amount: data.amount * 100,
                currency: "INR",
                name: "Mutual Fund Platform",
                description: `Investment in ${selectedFundName}`,
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
                                fund_id: selectedFundId
                            })
                        });

                        const verifyData = await verifyResponse.json();
                        if (verifyData.error) {
                            alert(verifyData.error);
                            return;
                        }

                        investModal.hide();
                        successModal.show();
                    } catch (error) {
                        alert('Error processing payment verification');
                    }
                },
                prefill: {
                    name: "Investor",
                    email: "",
                    contact: ""
                },
                theme: {
                    color: "#3399cc"
                }
            };

            const rzp = new Razorpay(options);
            rzp.open();
            investModal.hide();

        } catch (error) {
            alert('Error creating payment order');
        }
    });
});