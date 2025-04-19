document.addEventListener("DOMContentLoaded", () => {
    const popup = document.getElementById("payment-popup");
    const overlay = document.getElementById("payment-overlay");
    const closeBtn = document.querySelector(".payment-close");

    if (popup && overlay && closeBtn) {
        closeBtn.addEventListener("click", () => {
            popup.classList.add("hidden");
            overlay.classList.add("hidden");
        });

        overlay.addEventListener("click", () => {
            popup.classList.add("hidden");
            overlay.classList.add("hidden");
        });
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("payment-form");

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const formData = new FormData(form);

            const amount = parseFloat(formData.get("amount"));
            if (amount > 50) {
                const cardId = formData.get("card_id");

                // Appelle le backend pour envoyer le code par mail
                try {
                    const res = await fetch(`/card/${cardId}/request_pin_code`, {
                        method: "POST"
                    });

                    if (!res.ok) {
                        const data = await res.json();
                        showPopup(data.error || "Erreur lors de l'envoi du code", "error");
                        return;
                    }

                    // Affiche la modale de vérification
                    document.getElementById("verification-overlay").classList.remove("hidden");
                    document.getElementById("verification-modal").classList.remove("hidden");

                    return; //Stop ici : on attend que l'utilisateur entre le code avant de soumettre
                } catch (err) {
                    showPopup("Échec de la vérification", "error");
                    return;
                }
            }


            // Debug : affichage des données envoyées
            const debugData = Object.fromEntries(formData.entries());
            console.log("Données envoyées :", debugData);

            try {
                const response = await fetch("/process_payment", {
                    method: "POST",
                    body: formData  // ✅ FormData utilisé à la place de JSON
                });

                const result = await response.json();

                if (!response.ok) {
                    showPopup(result.message, "error");
                    return;
                }

                window.location.href = result.redirect;
            } catch (err) {
                showPopup("Erreur de communication avec le serveur", "error");
            }
        });
    }
});


async function submitPaymentViaFetch() {
    console.log("submitPaymentViaFetch() appelé");  //TRACE

    const form = document.getElementById("payment-form");
    const formData = new FormData(form);

    const debugData = Object.fromEntries(formData.entries());
    console.log("Données envoyées au paiement :", debugData);

    try {
        const response = await fetch("/process_payment", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        console.log("Résultat reçu :", result);

        if (!response.ok) {
            showPopup(result.message || "Échec du paiement", "error");
            return;
        }

        showPopup("Paiement effectué avec succès");
        setTimeout(() => {
            window.location.href = result.redirect;
        }, 2000);
    } catch (err) {
        console.error(" Erreur serveur :", err);
        showPopup("Erreur serveur pendant le paiement", "error");
    }
}

// Rendez la fonction disponible globalement
window.submitPaymentViaFetch = submitPaymentViaFetch;


function showPopup(message, type = "success", options = {}) {
    const overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    document.body.appendChild(overlay);

    const popup = document.createElement("div");
    popup.className = `popup ${type}`;

    let iconClass = "bi-check-circle-fill";
    if (type === "error") iconClass = "bi-x-circle-fill";
    else if (type === "loading") iconClass = "bi-hourglass-split spin-icon";
    else if (type === "confirm") iconClass = "bi-question-circle-fill";

    popup.innerHTML = `
        <span class="icon"><i class="bi ${iconClass}"></i></span>
        <span class="message">${message}</span>
        ${type !== "loading" && type !== "confirm" ? '<span class="close-btn"><i class="bi bi-x-lg"></i></span>' : ''}
    `;

    if (type === "confirm") {
        const btnGroup = document.createElement("div");
        btnGroup.className = "popup-buttons";

        const confirmBtn = document.createElement("button");
        confirmBtn.textContent = options.confirmText || "Confirmer";
        confirmBtn.className = "popup-confirm";

        const cancelBtn = document.createElement("button");
        cancelBtn.textContent = options.cancelText || "Annuler";
        cancelBtn.className = "popup-cancel";

        btnGroup.appendChild(confirmBtn);
        btnGroup.appendChild(cancelBtn);
        popup.appendChild(btnGroup);

        confirmBtn.addEventListener("click", () => {
            popup.remove();
            overlay.remove();
            if (typeof options.onConfirm === "function") options.onConfirm();
        });

        cancelBtn.addEventListener("click", () => {
            popup.remove();
            overlay.remove();
            if (typeof options.onCancel === "function") options.onCancel();
        });
    }

    if (type === "loading") {
        const spinner = document.createElement("div");
        spinner.className = "spinner";
        popup.appendChild(spinner);
    }

    document.body.appendChild(popup);

    const closeBtn = popup.querySelector(".close-btn");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            popup.remove();
            overlay.remove();
        });
    }

    if (type !== "loading" && type !== "confirm") {
        setTimeout(() => {
            popup.remove();
            overlay.remove();
        }, 5000);
    }
    

    // Retourner le popup afin d'utiliser la fonction dans une variable 
    return popup;
}

window.submitPaymentViaFetch = submitPaymentViaFetch;

