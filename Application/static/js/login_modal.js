// login_modal.js

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

    function closeModal() {
        const modal = document.getElementById("login-modal");
        const modalContent = document.getElementById("login-modal-content");
        if (modal && modalContent) {
            modal.style.display = "none";
            modalContent.innerHTML = "";
        }
    }

    // ⏳ Délai de 10 secondes pour bien se positionner
    setTimeout(async () => {
        try {
            preview.style.display = "flex";
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;

            const canvas = document.createElement("canvas");
            canvas.width = 320;
            canvas.height = 240;
            const context = canvas.getContext("2d");

            let images = [];
            let count = 0;

            const interval = setInterval(async () => {
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                images.push(canvas.toDataURL("image/png"));
                count++;

                if (count >= 10) {
                    clearInterval(interval);
                    stream.getTracks().forEach(track => track.stop());
                    preview.style.display = "none";

                    // 🔄 popup loading
                    const loading = showPopup("Vérification en cours...", "loading");

                    const formData = new FormData(form);
                    formData.append("images", JSON.stringify(images));

                    const res = await fetch("/login-modal", {
                        method: "POST",
                        body: formData,
                    });

                    const data = await res.json();
                    closeAllPopups();

                    if (res.ok) {
                        showPopup(data.message, "success");
                        setTimeout(() => {
                            if (data.redirect) window.location.href = data.redirect;
                        }, 3000);
                    } else {
                        showPopup(data.message || "Erreur", "error");
                    }
                }
            }, 300); // 10 captures rapides
        } catch (err) {
            console.error("Erreur caméra:", err);
            status.textContent = "Erreur d'accès à la caméra.";
        }
    }, 10000); // délai initial 10s
}


function showPopup(message, type = "success") {
    const overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    document.body.appendChild(overlay);

    const popup = document.createElement("div");
    popup.className = `popup ${type}`;
    popup.innerHTML = `
        <span class="icon">
            <i class="bi ${
                type === "error" ? "bi-x-circle-fill" :
                type === "loading" ? "bi-hourglass-split" :
                "bi-check-circle-fill"
            }"></i>
        </span>
        <span class="message">${message}</span>
        <span class="close-btn"><i class="bi bi-x-lg"></i></span>
        ${type === "loading" ? '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>' : ''}
    `;

    document.body.appendChild(popup);

    popup.querySelector(".close-btn").addEventListener("click", () => {
        popup.remove();
        overlay.remove();
    });

    // Ne pas supprimer tout de suite si loading
    if (type !== "loading") {
        setTimeout(() => {
            if (document.body.contains(popup)) popup.remove();
            if (document.body.contains(overlay)) overlay.remove();
        }, 5000);
    }
}

