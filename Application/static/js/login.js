let biometricLoginDone = false;

function setupLoginBiometrics() {
    const preview = document.getElementById("camera-preview");
    const video = document.getElementById("video");
    const status = document.getElementById("capture-status");
    const biometricsBtn = document.getElementById("biometrics-btn");
    const form = document.getElementById("login-form");

    if (!biometricsBtn || !preview || !video || !status || !form) {
        console.warn("Éléments manquants pour la capture biométrique (login).");
        return;
    }

    // Soumission du formulaire
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        if (!biometricLoginDone) {
            showPopup("Veuillez d'abord faire la capture biométrique pour vous connecter.", "error");
            return;
        }

        const formData = new FormData(form);

        fetch("/login", {
            method: "POST",
            body: formData
        })
        .then(res => {
            if (!res.ok) return res.text().then(text => { throw new Error(text); });
            return res.json();
        })
        .then(data => {
            showPopup(data.message, "success");

            setTimeout(() => {
                showPopup("Connexion réussie ! Redirection...", "success", true);
            }, 2500);

            setTimeout(() => {
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            }, 5000);

            form.reset();
        })
        .catch(async (err) => {
            let errorMessage = "Une erreur est survenue.";
            
            try {
                const text = await err.message;
                const json = JSON.parse(text);
                errorMessage = json.message || errorMessage;
            } catch (e) {
                errorMessage = err.message;
            }
        
            showPopup(errorMessage, "error");
        });
        
    });

    // Capture biométrique
    biometricsBtn.addEventListener("click", async () => {
        preview.style.display = "flex";

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;

            const canvas = document.createElement("canvas");
            canvas.width = 320;
            canvas.height = 240;

            for (let i = 1; i <= 30; i++) {
                status.textContent = `Capture ${i}/30 en cours...`;
                await new Promise(res => setTimeout(res, 200));
                canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
                const imageData = canvas.toDataURL("image/png");

                await fetch("/verify-face", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ image: imageData })
                });
            }

            stream.getTracks().forEach(track => track.stop());
            video.srcObject = null;
            preview.style.display = "none";
            alert("Vérification biométrique réussie !");
            biometricLoginDone = true;
        } catch (err) {
            alert("Erreur lors de l'accès à la caméra !");
            preview.style.display = "none";
        }
    });
}

// Réutilisation du système de popup
function showPopup(message, type = "success", withSpinner = false) {
    const overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    document.body.appendChild(overlay);

    const popup = document.createElement("div");
    popup.className = `popup ${type}`;
    popup.innerHTML = `
        <span class="icon">
            <i class="bi ${type === "error" ? "bi-x-circle-fill" : "bi-check-circle-fill"}"></i>
        </span>
        <span class="message">${message}</span>
        <span class="close-btn"><i class="bi bi-x-lg"></i></span>
        ${withSpinner ? '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>' : ''}
    `;

    document.body.appendChild(popup);

    popup.querySelector(".close-btn").addEventListener("click", () => {
        popup.remove();
        overlay.remove();
    });

    setTimeout(() => {
        if (document.body.contains(popup)) popup.remove();
        if (document.body.contains(overlay)) overlay.remove();
    }, 10000);
}

// Export global
window.setupLoginBiometrics = setupLoginBiometrics;
