let biometricDone = false;

async function setupBiometricsCapture() {
    const preview = document.getElementById("camera-preview");
    const video = document.getElementById("video");
    const status = document.getElementById("capture-status");
    const biometricsBtn = document.getElementById("biometrics-btn");
    const form = document.getElementById("signup-form");

    if (!preview || !video || !status || !form || !biometricsBtn) return;

    await faceapi.nets.tinyFaceDetector.loadFromUri('/static/models/tiny_face_detector_model');

    // 🎥 Lancement capture biométrique
    biometricsBtn.addEventListener("click", async () => {
        preview.style.display = "flex";
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;

        const canvas = document.createElement("canvas");
        canvas.width = 320;
        canvas.height = 240;

        let count = 0;
        let startTime = Date.now();

        const interval = setInterval(async () => {
            const elapsed = (Date.now() - startTime) / 1000;

            if (elapsed >= 10) {
                clearInterval(interval);
                stream.getTracks().forEach(t => t.stop());
                preview.style.display = "none";
                await fetch("/clear-temp-faces");
                showPopup("Temps écoulé. Aucun visage correctement détecté.", "error");
                return;
            }

            const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions());
            if (detections.length > 0) {
                startTime = Date.now();
                status.textContent = `Capture ${count + 1}/50 en cours...`;

                const context = canvas.getContext("2d");
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                const imageData = canvas.toDataURL("image/png");

                await fetch("/register-face", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ image: imageData })
                });

                count++;
                if (count >= 50) {
                    clearInterval(interval);
                    stream.getTracks().forEach(t => t.stop());
                    preview.style.display = "none";
                    biometricDone = true;
                    showPopup("Captures terminées avec succès !", "success");
                }
            } else {
                status.textContent = `Positionnez bien votre tête (${Math.floor(10 - elapsed)}s restantes)`;
            }
        }, 300);
    });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
    
        if (!biometricDone) {
            showPopup("Veuillez compléter la capture biométrique avant de vous inscrire.", "error");
            return;
        }
    
        const requiredFields = ["last_name", "first_name", "gender", "birthday", "email", "phone", "username", "password"];
        for (const field of requiredFields) {
            const input = document.getElementById(field);
            if (!input.value.trim()) {
                showPopup(`Le champ ${field} est requis.`, "error");
                return;
            }
        }
    
        // Affiche un popup "loading"
        let loadingPopup = showPopup("Traitement des données en cours...", "loading");
    
        const formData = new FormData(form);
    
        try {
            const response = await fetch("/signup-modal", {
                method: "POST",
                body: formData
            });
    
            const result = await response.json();
    
            if (!response.ok) {
                // On supprime le popup loading manuellement
                closeAllPopups();
                showPopup(result.message || "Erreur lors de l'inscription", "error");
                return;
            }
    
            // Succès : popup success + redirection ou traitement biométrique
            loadingPopup = showPopup("Inscription réussie, traitement des données biométriques en cours...", "loading");
    
            const biometricRes = await fetch("/process-faces");
            const biometricResult = await biometricRes.json();
    
            if (!biometricRes.ok) {
                closeAllPopups();
                showPopup("Erreur lors du traitement des visages", "error");
                return;
            }
    
            closeAllPopups();
            let finalMessage = "Traitement terminé !";
            if (biometricResult.redirect === "/home2") {
                finalMessage = "Bienvenue ! Redirection vers votre espace sécurisé...";
            } else if (biometricResult.redirect === "/login-modal" || biometricResult.redirect === "/") {
                finalMessage = "Inscription réussie ! Redirection vers la page de connexion...";
            }

            loadingPopup.querySelector(".message").textContent = finalMessage;
            loadingPopup.classList.remove("loading");
            loadingPopup.classList.add("success");
            loadingPopup.querySelector(".icon i").className = "bi bi-check-circle-fill";

            setTimeout(() => {
                closeAllPopups();
                if (biometricResult.redirect) {
                    window.location.href = biometricResult.redirect;
                }
            }, 3000);

    
        } catch (error) {
            console.error("Erreur JS :", error);
            closeAllPopups();
            showPopup("Erreur inattendue", "error");
        }
    });       
}

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

function closeAllPopups() {
    document.querySelectorAll(".popup, .popup-overlay").forEach(el => el.remove());
}


