document.addEventListener('DOMContentLoaded', function() {
    const fundSearch = document.getElementById('fundSearch');
    const categoryFilter = document.getElementById('categoryFilter');
    const riskFilter = document.getElementById('riskFilter');
    
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
    
    // Investment modal handling
    const investModal = new bootstrap.Modal(document.getElementById('investModal'));
    let selectedFundId = null;
    
    document.querySelectorAll('.invest-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            selectedFundId = this.dataset.fundId;
            investModal.show();
        });
    });
    
    document.getElementById('confirmInvest').addEventListener('click', function() {
        const amount = document.getElementById('investAmount').value;
        
        // Here you would typically make an API call to process the investment
        console.log('Processing investment:', {
            fundId: selectedFundId,
            amount: amount
        });
        
        investModal.hide();
        
        // Show success message
        const toast = new bootstrap.Toast(document.createElement('div'));
        toast.show();
    });
});
