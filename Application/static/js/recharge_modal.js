function openRechargeModal() {
    const modal = document.getElementById('recharge-modal');
    if (modal) {
      modal.style.display = 'flex'; // ou "block" selon ton CSS
    }
  }
  
  function closeRechargeModal() {
    const modal = document.getElementById('recharge-modal');
    if (modal) {
      modal.style.display = 'none';
    }
  }


  function handleRechargeSubmit(event) {
  event.preventDefault(); // Empêche la soumission classique du formulaire

  const form = document.getElementById('recharge-form');
  const formData = new FormData(form);
  const targetCardId = formData.get("target_card_id");
  const sourceCardId = formData.get("source_card_id");
  const amount = parseFloat(formData.get("amount"));

  // Préparation côté backend
  fetch('/prepare_recharge', {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_card_id: targetCardId,
      source_card_id: sourceCardId,
      amount: amount
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === "ok") {
      closeRechargeModal(); // Ferme la modale de recharge

      window.__pinVerificationMode = "recharge";

      // Cas spécial : recharge externe (source = cible = première carte)
      if (data.external_recharge === true) {
        window.__onPINSuccess = () => {
          startRechargeFaceVerification(); // Lance la caméra après PIN
        };
        startPINVerification(targetCardId, window.__onPINSuccess);
      } 
      // Cas classique : recharge entre deux cartes
      else {
        window.__onPINSuccess = () => {
          fetch('/complete_recharge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
          })
          .then(res => {
            if (res.ok) {
              showPopup("Recharge successful!");
              window.location.href = "/manage_cards";
            } else {
              showPopup("Recharge failed", "error");
            }
          });
        };
        startPINVerification(targetCardId, window.__onPINSuccess);
      }

    } else {
      showPopup(data.message || "Erreur lors de la préparation de la recharge", "error");
    }
  })
  .catch(() => {
    showPopup("Erreur serveur lors de la recharge", "error");
  });
}
