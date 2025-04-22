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
