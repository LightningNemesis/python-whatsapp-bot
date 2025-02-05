function isMobile() {
  return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
}

// Check if we're inside MetaMask browser
function isMetaMaskBrowser() {
  return window.ethereum?.isMetaMask && isMobile();
}

async function connectMetaMask() {
  try {
    if (isMobile() && !isMetaMaskBrowser()) {
      // Only redirect to MetaMask if we're not already in MetaMask browser
      const hostname = window.location.hostname;
      const path = window.location.pathname;
      const searchParams = window.location.search;
      const redirectUrl = `https://metamask.app.link/dapp/${hostname}${path}${searchParams}${
        searchParams ? '&' : '?'
      }source=metamask`;
      window.location.href = redirectUrl;
      return;
    }

    // If we're here, we're either on desktop or already in MetaMask browser
    if (!window.ethereum) {
      showStatus(
        'MetaMask is not installed. Please install MetaMask first.',
        'error'
      );
      return;
    }

    // Request account access
    const accounts = await window.ethereum.request({
      method: 'eth_requestAccounts',
    });
    const account = accounts[0];

    showStatus('Connected! Preparing to sign...', 'success');
    await handleSigning(account);
  } catch (error) {
    showStatus('Error connecting: ' + error.message, 'error');
  }
}

async function handleSigning(address) {
  try {
    const provider = new ethers.providers.Web3Provider(window.ethereum);
    const signer = provider.getSigner();

    // Create message to sign
    const message = JSON.stringify({
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      action: 'sign_loi',
    });

    showStatus('Please sign the message in MetaMask...', 'success');

    // Request signature
    const signature = await signer.signMessage(message);

    // Verify with backend
    const response = await fetch('/api/store-signature', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        signature: signature,
        address: address,
      }),
    });

    const result = await response.json();

    if (result.success) {
      showStatus('Signed successfully! Returning to WhatsApp...', 'success');
      setTimeout(() => {
        window.location.href = result.redirect_url;
      }, 2000);
    } else {
      showStatus('Signing failed: ' + result.error, 'error');
    }
  } catch (error) {
    showStatus('Error during signing: ' + error.message, 'error');
  }
}

function showStatus(message, type = 'normal') {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
  statusDiv.style.display = 'block';
}

// Add click handler for connect button
document
  .getElementById('connectButton')
  .addEventListener('click', connectMetaMask);

// Show appropriate UI based on browser and attempt auto-connect
window.addEventListener('load', async () => {
  if (isMetaMaskBrowser()) {
    document.getElementById('initialState').style.display = 'none';
    document.getElementById('metamaskBrowserState').style.display = 'block';

    // Try to auto-connect if we're in MetaMask browser
    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({
          method: 'eth_accounts',
        });
        if (accounts.length > 0) {
          await handleSigning(accounts[0]);
        }
      } catch (error) {
        console.error('Error auto-connecting:', error);
      }
    }
  }
});
