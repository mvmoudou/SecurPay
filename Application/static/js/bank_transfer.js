function openBeneficiaryPopup() {
    console.log("openBeneficiaryPopup appelée");
  
    fetch('/get_beneficiaries')
      .then(res => res.json())
      .then(data => {
        console.log("Données reçues :", data);
        const list = document.getElementById("beneficiary-list");
        list.innerHTML = "";
  
        if (!data.beneficiaries || data.beneficiaries.length === 0) {
          list.innerHTML = "<li>No beneficiaries available</li>";
          return;
        }
  
        data.beneficiaries.forEach(b => {
          const li = document.createElement("li");
          li.innerHTML = `
            <span>${b.full_name} (N° ${b.card_number_masked})</span>
            <button onclick="selectBeneficiary(${b.id}, '${b.full_name}', '${b.card_number_masked}')">Choose</button>
          `;
          list.appendChild(li);
        });
  
        const popup = document.getElementById("beneficiary-popup");
        console.log("Avant suppression hidden: ", popup.classList.value);
        popup.classList.remove("hidden");
        console.log("Après suppression hidden: ", popup.classList.value);
      })
      .catch(err => {
        showPopup("Erreur lors du chargement des bénéficiaires", "error");

      });
  }
  
  function closeBeneficiaryPopup() {
    const popup = document.getElementById("beneficiary-popup");
    popup.classList.add("hidden");
  }
  
  function selectBeneficiary(id, name, cardNumber) {
    document.getElementById("selected-beneficiary-id").value = id;
    const summary = document.getElementById("beneficiary-summary");
    summary.textContent = `Beneficiary: ${name} (${cardNumber})`;
    summary.classList.remove("hidden");
    closeBeneficiaryPopup();
  }

  function handleBankTransferSubmit(event) {
    event.preventDefault();
  
    const form = document.getElementById('transfer-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
  
    fetch('/submit_transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(response => {
      if (!response.success) {
        showPopup(response.error || "Transfer failed.", "error");
        return;
      }
  
      handleBankTransferVerification({
        source_card_id: response.source_card_id  // la carte qui sera débitée
      });
      
    })
    .catch(err => {
      console.error("Erreur de soumission :", err);
      showPopup("Erreur lors du transfert.", "error");
    });
  }

  
  function closeAddBeneficiaryModal() {
    const modal = document.getElementById("add-beneficiary-modal");
    modal.classList.add("hidden");
    modal.style.display = "none";
    
  }
  
  function handleAddBeneficiary(event) {
    event.preventDefault();
    const form = document.getElementById('add-beneficiary-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
  
    fetch('/add_beneficiary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(response => {
      if (response.success) {
        showPopup("Beneficiary added successfully!");
        closeAddBeneficiaryModal();
      } else {
        showPopup(response.error || "Failed to add beneficiary", "error");
      }
    })
    .catch(() => {
      showPopup("Server error while adding beneficiary", "error");
    });
  }

  function openAddBeneficiaryModal() {
    fetch('/get_user_cards')
      .then(res => res.json())
      .then(data => {
        const select = document.getElementById("beneficiary-card");
        select.innerHTML = "";
  
        if (!data.cards || data.cards.length === 0) {
          select.innerHTML = "<option disabled>No cards available</option>";
          return;
        }
  
        data.cards.forEach(card => {
          const option = document.createElement("option");
          option.value = card.id;
          option.textContent = card.masked;
          select.appendChild(option);
        });
        const modal = document.getElementById("add-beneficiary-modal");
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        
      });
  }
  
  
  function showPopup(message, type = "success") {
    closeAllPopups(); // empêche l’empilement
    const overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    document.body.appendChild(overlay);

    const popup = document.createElement("div");
    popup.className = `popup ${type}`;
    popup.innerHTML = `
        <span class="icon">
            <i class="bi ${
                type === "error" ? "bi-x-circle-fill" :
                type === "loading" ? "bi-hourglass-split spin-icon" :
                "bi-check-circle-fill"
            }"></i>
        </span>
        <span class="message">${message}</span>
        <span class="close-btn"><i class="bi bi-x-lg"></i></span>
    `;

    document.body.appendChild(popup);

    popup.querySelector(".close-btn").addEventListener("click", () => {
        popup.remove();
        overlay.remove();
    });

    if (type !== "loading") {
        setTimeout(() => {
            popup.remove();
            overlay.remove();
        }, 5000);
    }

    return popup;
}

function closeAllPopups() {
    document.querySelectorAll(".popup, .popup-overlay").forEach(el => el.remove());
}



  