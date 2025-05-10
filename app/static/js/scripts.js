// MetaMask integration for wallet connect
async function connectWallet() {
    if (window.ethereum) {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            const walletAddress = accounts[0];
            // Send address to backend
            const response = await fetch('/user/connect_wallet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `wallet_address=${walletAddress}`
            });
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Не вдалося підключити гаманець.');
            }
        } catch (err) {
            alert('Підключення MetaMask скасовано або сталася помилка.');
        }
    } else {
        alert('MetaMask не встановлено!');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const walletShort = document.getElementById('wallet-address-short');
    const walletCopyStatus = document.getElementById('wallet-copy-status');
    if (walletShort) {
        walletShort.addEventListener('click', function () {
            const fullAddress = '{{ current_user.wallet_address }}';
            navigator.clipboard.writeText(fullAddress).then(() => {
                if (walletCopyStatus) {
                    walletCopyStatus.style.display = 'inline';
                    setTimeout(() => {
                        walletCopyStatus.style.display = 'none';
                    }, 1500);
                }
            });
        });
    }

    document.querySelectorAll('.auction-toggle-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var auctionId = btn.getAttribute('data-auction-id');
            var modal = document.getElementById('auctionModal-' + auctionId);
            if (modal) {
                var bsModal = new bootstrap.Modal(modal);
                bsModal.show();
            }
        });
    });

    function handleAuctionAction(btnClass, resultTextCb) {
        document.querySelectorAll(btnClass).forEach(function (btn) {
            btn.addEventListener('click', async function () {
                const auctionId = btn.getAttribute('data-auction-id');
                const url = btn.getAttribute('data-url');
                const resultDiv = document.getElementById('auction-action-result-' + auctionId);
                if (!url || !resultDiv) return;
                // Disable all action buttons for this auction
                const modal = btn.closest('.modal');
                modal.querySelectorAll('.participate-btn, .view-price-btn, .close-auction-btn').forEach(b => b.disabled = true);
                resultDiv.style.display = 'none';
                try {
                    const response = await fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                    const data = await response.json();
                    let html = '';
                    if (data.error) {
                        html = `<div class='alert alert-danger mb-0'>${data.error}</div>`;
                    } else {
                        html = resultTextCb(data);
                    }
                    resultDiv.innerHTML = html;
                    resultDiv.style.display = 'block';
                } catch (e) {
                    resultDiv.innerHTML = `<div class='alert alert-danger mb-0'>Сталася помилка. Спробуйте ще раз.</div>`;
                    resultDiv.style.display = 'block';
                }
                setTimeout(() => {
                    resultDiv.style.display = 'none';
                    modal.querySelectorAll('.participate-btn, .view-price-btn, .close-auction-btn').forEach(b => b.disabled = false);
                }, 5000);
            });
        });
    }
    handleAuctionAction('.participate-btn', data => `<div class='alert alert-success mb-0'>Успішно! Учасників: <b>${data.participants ?? '?'}</b>, поточна ціна: <b>${data.final_price ?? '?'}</b> грн</div>`);
    handleAuctionAction('.view-price-btn', data => `<div class='alert alert-info mb-0'>Перегляд ціни. Учасників: <b>${data.participants ?? '?'}</b>, поточна ціна: <b>${data.final_price ?? '?'}</b> грн</div>`);
    handleAuctionAction('.close-auction-btn', data => `<div class='alert alert-warning mb-0'>Аукціон закрито. Учасників: <b>${data.participants ?? '?'}</b>, ціна: <b>${data.final_price ?? '?'}</b> грн</div>`);
});

