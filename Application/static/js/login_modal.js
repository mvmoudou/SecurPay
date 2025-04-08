let interval = null;

function setupLoginWithCamera() {
    const preview = document.getElementById("camera-preview-login");
    const video = document.getElementById("video-login");
    const status = document.getElementById("login-capture-status");
    const form = document.getElementById("login-form");
    const backBtn = document.getElementById("back-login");
    const closeBtn = document.querySelector(".close-login-btn");

    if (!preview || !video || !status || !form) return;

    backBtn?.addEventListener("click", closeModal);
    closeBtn?.addEventListener("click", closeModal);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector("button[type='submit']");
        submitBtn.disabled = true;

        const username = document.getElementById("login-username")?.value;
        const password = document.getElementById("login-password")?.value;

        if (!username || !password) {
            showPopup("Veuillez renseigner vos identifiants.", "error");
            submitBtn.disabled = false;
            return;
        }

        preview.style.display = "flex";
        status.textContent = "Veuillez bien positionner votre tête...";

        try {
            await faceapi.nets.tinyFaceDetector.loadFromUri("/static/models/tiny_face_detector_model");
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;

            const canvas = document.createElement("canvas");
            canvas.width = 320;
            canvas.height = 240;
            const context = canvas.getContext("2d");

            let images = [];
            let countdown = 10;
            let startTime = Date.now();

            interval = setInterval(async () => {
                const elapsed = (Date.now() - startTime) / 1000;

                const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions());

                if (detections.length > 0) {
                    startTime = Date.now(); // reset chrono
                    status.textContent = "Restez comme ça...";

                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    images.push(canvas.toDataURL("image/png"));

                    if (images.length >= 10) {
                        clearInterval(interval);
                        interval = null;
                        stopLoginCamera();
                        await sendLoginRequest(username, password, images, submitBtn);
                    }
                } else {
                    status.textContent = `Veuillez bien positionner votre tête (${Math.ceil(10 - elapsed)}s restantes)`;

                    if (elapsed >= countdown) {
                        clearInterval(interval);
                        interval = null;
                        stopLoginCamera();
                        submitBtn.disabled = false;
                        showPopup("Temps écoulé. Aucun visage correctement détecté.", "error");
                    }
                }
            }, 400);

        } catch (err) {
            console.error("Erreur caméra:", err);
            status.textContent = "Erreur d'accès à la caméra.";
            form.querySelector("button[type='submit']").disabled = false;
        }
    });
}

async function sendLoginRequest(username, password, images, submitBtn) {
    showFaceVerificationPopup();

    try {
        const res = await fetch("/login-modal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, images })
        });

        let data = { message: "Erreur inconnue." };
        try {
            data = await res.json();
        } catch (err) {
            console.warn("Erreur parsing JSON:", err);
        }

        closeFaceVerificationPopup();
        submitBtn.disabled = false;

        if (res.ok) {
            showPopup("Connexion réussie ! Vous allez être redirigé vers votre espace personnel...", "success");
            setTimeout(() => {
                if (data.redirect) window.location.href = data.redirect;
            }, 3000);
        } else {
            showPopup(data.message || "Échec de la connexion. Veuillez réessayer.", "error");
        }

    } catch (err) {
        closeFaceVerificationPopup();
        submitBtn.disabled = false;
        console.error("Erreur login:", err);
        showPopup("Erreur réseau ou serveur. Veuillez réessayer.", "error");
    }
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

function stopLoginCamera() {
    const video = document.getElementById("video-login");
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    const preview = document.getElementById("camera-preview-login");
    if (preview) preview.style.display = "none";
}



function closeModal() {
    const modal = document.getElementById("login-modal");
    const modalContent = document.getElementById("login-modal-content");
    stopLoginCamera();
    if (modal && modalContent) {
        modal.style.display = "none";
        modalContent.innerHTML = "";
    }

    const overlay = document.getElementById("modal-overlay");
    if (overlay) overlay.style.display = "none";
}


function showFaceVerificationPopup() {
    document.getElementById('face-verification-popup').style.display = 'flex';
    document.querySelector('.modal-content').style.opacity = '0.3';
}

function closeFaceVerificationPopup() {
    document.getElementById('face-verification-popup').style.display = 'none';
    document.querySelector('.modal-content').style.opacity = '1';
}
