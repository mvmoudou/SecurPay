// Ouvre la modale de vérification et envoie le mail
function startPINVerification(cardId, onSuccess) {
    fetch(`/card/${cardId}/request_pin_code`, {
      method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        openPINVerificationModal(cardId, onSuccess);
      } else {
        showPopup(data.message || "Erreur lors de l'envoi du code", "error");
      }
    });
  }
  
  // Affiche la modale
  function openPINVerificationModal(cardId, callback) {
    window.__currentCardId = cardId;
    window.__onPINSuccess = callback;
    document.getElementById("pin-verification-modal").style.display = "flex";
  
    clearPINInputs();
    startResendCountdown();
  }
  
  // Ferme la modale
  function closePINVerificationModal() {
    document.getElementById("pin-verification-modal").style.display = "none";
    document.getElementById("pin-error-msg").style.display = "none";
  }
  
  // Ajoute un chiffre depuis le pavé
  function addDigit(elem) {
    const digit = elem.innerText.trim();
    const boxes = document.querySelectorAll(".code-box");
    for (let box of boxes) {
      if (box.value === "") {
        box.value = digit;
        box.focus();
        break;
      }
    }
  }
  
  // Soumission du code
  function submitPINVerification() {
    const code = Array.from(document.querySelectorAll(".code-box"))
        .map(b => b.value.trim())
        .join("");

    if (code.length < 6) {
        showError("Code incomplet");
        return;
    }

    console.log("Code PIN soumis :", code);
    console.log("🪪 Card ID :", window.__currentCardId);

    fetch(`/card/${window.__currentCardId}/verify_code_and_get_pin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            closePINVerificationModal();
            if (window.__pinVerificationMode === "show_pin") {
              showPINPopup(data.pin);
          }
          console.log("Callback détecté ?", window.__onPINSuccess);
            console.log("Type du callback :", typeof window.__onPINSuccess);


            console.log("Code PIN correct, exécution du callback");
            if (typeof window.__onPINSuccess === 'function') {
              console.log("Callback valide, exécution...");
                window.__onPINSuccess();
            } else {
                console.error("__onPINSuccess non défini ou pas une fonction");
            }
        } else {
            showError(data.message || "Code invalide");
        }
    })
    .catch(() => showError("Erreur serveur"));
}

  
  // Efface les cases
  function clearPINInputs() {
    document.querySelectorAll(".code-box").forEach(box => box.value = "");
    document.querySelector(".code-box").focus();
  }
  
  // Copier/coller direct
  document.addEventListener('paste', (e) => {
    const paste = (e.clipboardData || window.clipboardData).getData('text').trim();
    if (/^\d{6}$/.test(paste)) {
      const boxes = document.querySelectorAll(".code-box");
      for (let i = 0; i < 6; i++) {
        boxes[i].value = paste[i];
      }
    }
  });
  
  // Renvoyer le code (30s)
  function startResendCountdown() {
    let seconds = 30;
    const resend = document.getElementById("resend-text");
    resend.style.pointerEvents = "none";
    resend.textContent = `Resend in ${seconds}s`;
  
    const interval = setInterval(() => {
      seconds--;
      resend.textContent = seconds > 0 ? `Resend in ${seconds}s` : "Resend now";
      if (seconds === 0) {
        clearInterval(interval);
        resend.style.pointerEvents = "auto";
        resend.onclick = () => {
          resend.onclick = null;
          startPINVerification(window.__currentCardId, window.__onPINSuccess);
        };
      }
    }, 1000);
  }
  
  // Message d’erreur
  function showError(msg) {
    const error = document.getElementById("pin-error-msg");
    error.textContent = msg;
    error.style.display = "block";
  }

  function showPINPopup(pin) {
    const modal = document.getElementById("pin-popup-modal");
    const value = document.getElementById("pin-value");
    const progress = document.getElementById("progress-bar");
    const countdown = document.getElementById("countdown");
    console.log("PIN affiché :", pin);
  
    value.textContent = pin;
    progress.style.width = "100%";
    countdown.textContent = "10";
    modal.style.display = "flex";
  
    let timeLeft = 10;
    const interval = setInterval(() => {
      timeLeft--;
      countdown.textContent = timeLeft;
      progress.style.width = `${(timeLeft / 10) * 100}%`;
  
      if (timeLeft <= 0) {
        clearInterval(interval);
        modal.style.display = "none";
      }
    }, 1000);
  }
  
  function handleShowSecretCode(cardId) {
    window.__pinVerificationMode = "show_pin"; // <- Ici tu définis le mode
    window.__onPINSuccess = () => {
      console.log("Vérification réussie pour affichage du code PIN.");
      // Rien d'autre ici : showPINPopup est appelé automatiquement dans submitVerification
    };
  
    startPINVerification(cardId, window.__onPINSuccess);
  }
  

  function handlePaymentWithVerification() {
    const amount = Number(document.getElementById("payment-amount").value);
    const cardId = document.getElementById("payment-card-id").value;
  
    // On stocke la fonction à exécuter après vérification
    window.__onPINSuccess = () => {
      console.log("Code vérifié, déclenchement du paiement");
      setTimeout(() => {
        if (typeof window.submitPaymentViaFetch === 'function') {
          console.log("Appel de submitPaymentViaFetch depuis PIN success");
          window.submitPaymentViaFetch();
        } else {
          console.error("submitPaymentViaFetch non défini au moment du callback");
        }
      }, 100);
  };
  
    if (amount > 50) {
      window.__pinVerificationMode = "payment";  // Contexte de paiement
      startPINVerification(cardId, window.__onPINSuccess); // enregistre et lance
    } else {
      submitPaymentViaFetch();
    }
  }

  function handleRechargeVerification(targetCardId, sourceCardId, amount) {
    window.__pinVerificationMode = "recharge";
  
    window.__onPINSuccess = () => {
      console.log("Code vérifié pour recharge");
  
      if (sourceCardId === targetCardId && sourceCardId === String(window.__firstCardId)) {
        console.log("Recharge externe (source == cible == première carte) → déclenche reconnaissance faciale");
        startRechargeFaceVerification();
      }
      else {
        console.log("Recharge normale → appel direct à /complete_recharge");
        fetch('/complete_recharge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        })
        .then(res => {
          if (res.ok) {
            showPopup("Recharge completed successfully!");
            window.location.href = "/manage_cards";
          } else {
            showPopup("Recharge failed", "error");
          }
        });
      }
    };
  
    // Lance la vérification par mail (code PIN)
    startPINVerification(targetCardId, window.__onPINSuccess);
  }
  
  function startRechargeFaceVerification() {
    const popup = document.getElementById("face-verification-popup");
    const video = document.getElementById("recharge-video");
    const canvas = document.getElementById("recharge-canvas");
    const context = canvas.getContext("2d");
    const statusText = document.getElementById("face-recharge-status");
    const loading = document.getElementById("recharge-loading");
  
    popup.style.display = "flex";
    statusText.textContent = "Please align your face with the camera...";
    loading.style.display = "none";
  
    let capturedImages = [];
    let count = 0;
    let maxCount = 10;
  
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        video.srcObject = stream;
  
        function captureLoop() {
          if (count >= maxCount) {
            verifyRechargeFace();
            return;
          }
  
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          let imgData = canvas.toDataURL('image/jpeg');
          capturedImages.push(imgData);
          count++;
          statusText.textContent = `Capturing ${count}/${maxCount}...`;
          setTimeout(captureLoop, 800);
        }
  
        setTimeout(captureLoop, 1500); // attend 1.5s avant démarrage
      });
  
    function verifyRechargeFace() {
      statusText.style.display = "none";
      loading.style.display = "block";
  
      fetch('/verify_recharge_face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: capturedImages })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          fetch('/complete_recharge', { method: 'POST' }).then(() => {
            popup.style.display = "none";
            showPopup("Recharge successful!");
            window.location.href = "/manage_cards";
          });
        } else {
          loading.style.display = "none";
          statusText.style.display = "block";
          statusText.textContent = "Face verification failed. Please try again.";
        }
      })
      .catch(() => {
        loading.style.display = "none";
        statusText.style.display = "block";
        statusText.textContent = "Error verifying your face.";
      });
    }
  }
  
  
function verifyRechargeFace() {
      statusText.style.display = "none";
      loading.style.display = "block";
  
      fetch('/verify_recharge_face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: capturedImages })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          fetch('/complete_recharge', { method: 'POST' }).then(() => {
            popup.style.display = "none";
            showPopup("Recharge successful!");
            window.location.href = "/manage_cards";
          });
        } else {
          loading.style.display = "none";
          statusText.style.display = "block";
          statusText.textContent = "Face verification failed. Please try again.";
        }
      })
      .catch(() => {
        loading.style.display = "none";
        statusText.style.display = "block";
        statusText.textContent = "Error verifying your face.";
      });
    }

    function handleBankTransferVerification(transferData) {
      window.__pinVerificationMode = "bank_transfer";
  
      // Cette fonction sera appelée après succès du code PIN
      window.__onPINSuccess = () => {
          console.log("Code vérifié pour virement, appel à /complete_transfer");
  
          fetch('/complete_transfer', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({})
          })
          .then(res => res.json())
          .then(response => {
              if (response.success) {
                  showPopup("Bank transfer completed!", "success");
                  setTimeout(() => window.location.href = "/home2", 2000);
              } else {
                  showPopup(response.error || "Transfer failed.", "error");
              }
          })
          .catch(err => {
              console.error("Erreur lors du /complete_transfer :", err);
              showPopup("Error finalizing transfer", "error");
          });
      };
  
      // Appel l’envoi du code PIN
      startPINVerification(transferData.source_card_id, window.__onPINSuccess);
  }
  
  
  
  
window.submitPINVerification = submitPINVerification;
window.handlePaymentWithVerification = handlePaymentWithVerification;

