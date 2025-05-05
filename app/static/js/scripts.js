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
});

