document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("add-card-form");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        console.log("Formulaire soumis !");

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // 🔍 Nettoyage des données
        data.card_number = data.card_number.replace(/\s+/g, "").trim();
        data.expiration = data.expiration.trim();
        data.cvv = data.cvv.trim();
        data.pin = data.pin.trim();
        data.billing_address = data.billing_address.trim();

        // ✅ Vérifications frontend
        const cardNumberValid = /^\d{13,19}$/.test(data.card_number);
        const expirationValid = /^(0[1-9]|1[0-2])\/20[2-9][0-9]$/.test(data.expiration);
        const cvvValid = /^\d{3,4}$/.test(data.cvv);
        const pinValid = /^\d{4,6}$/.test(data.pin);
        const addressValid = data.billing_address.length > 5;

        if (!cardNumberValid) {
            showPopup("Numéro de carte invalide. Il doit contenir entre 13 et 19 chiffres.", "error");
            return;
        }
        if (!expirationValid) {
            showPopup("Date d’expiration invalide. Format attendu : MM/YYYY.", "error");
            return;
        }
        if (!cvvValid) {
            showPopup("Code CVV invalide. Il doit contenir 3 ou 4 chiffres.", "error");
            return;
        }
        if (!pinValid) {
            showPopup("Code PIN invalide. Il doit contenir entre 4 et 6 chiffres.", "error");
            return;
        }
        if (!addressValid) {
            showPopup("Adresse de facturation trop courte.", "error");
            return;
        }

        try {
            const response = await fetch("/add_card", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.status === "error" || !response.ok) {
                showPopup(result.message || "Erreur lors de l'ajout", "error");
                return;
            }

            // ✅ Succès
            showPopup(result.message || "Carte ajoutée avec succès !");
            setTimeout(() => {
                window.location.href = "/manage_cards";
            }, 1500);

        } catch (error) {
            showPopup("Erreur de communication avec le serveur", "error");
        }
    });
});




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
