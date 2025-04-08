
const openSignupBtn = document.getElementById("open-signup");
const openLoginBtn = document.getElementById("open-login");

const signupModal = document.getElementById("signup-modal");
const signupContent = document.getElementById("signup-modal-content");
const loginModal = document.getElementById("login-modal");
const loginContent = document.getElementById("login-modal-content");

document.addEventListener("DOMContentLoaded", function () {

    function loadModal(endpoint, modalElem, contentElem, scriptPath, callbackFunctionName, needsFaceApi = false) {
        fetch(endpoint)
            .then(res => res.text())
            .then(html => {
                contentElem.innerHTML = html;
                modalElem.style.display = "flex";
    
                // Affiche l'overlay
                const overlay = document.getElementById("modal-overlay");
                if (overlay) overlay.style.display = "block";
    
                const loadUserScript = () => {
                    const userScript = document.createElement("script");
                    userScript.src = scriptPath;
    
                    userScript.onload = () => {
                        if (typeof window[callbackFunctionName] === "function") {
                            window[callbackFunctionName]();
                            if (typeof window.initGenderSelect === "function") {
                                window.initGenderSelect();
                            }
    
                            // Gère retour après CGU
                            const params = new URLSearchParams(window.location.search);
                            if (params.get("open") === "signup" && params.get("accept_cgu") === "yes") {
                                if (typeof window.restoreSignupFormData === "function") {
                                    window.restoreSignupFormData();
                                    window.history.replaceState(null, '', '/');
                                }
                            }
                        }
                    };
    
                    document.body.appendChild(userScript);
                };
    
                if (needsFaceApi) {
                    const faceApiScript = document.createElement("script");
                    faceApiScript.src = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api/dist/face-api.min.js";
                    faceApiScript.onload = loadUserScript;
                    document.body.appendChild(faceApiScript);
                } else {
                    loadUserScript();
                }
            });
    }
    

    if (openSignupBtn) {
        openSignupBtn.addEventListener("click", (e) => {
            e.preventDefault();
            loadModal("/signup-modal", signupModal, signupContent, "/static/js/signup_modal.js", "setupBiometricsCapture", true);
        });
    }

    if (openLoginBtn) {
        openLoginBtn.addEventListener("click", (e) => {
            e.preventDefault();
            loadModal("/login-modal", loginModal, loginContent, "/static/js/login_modal.js", "setupLoginWithCamera", true);
        });
    }

    // Fermer les modals si on clique à l'extérieur
    window.addEventListener("click", (e) => {
        if (e.target === signupModal) {
            signupModal.style.display = "none";
            signupContent.innerHTML = "";
        }
        if (e.target === loginModal) {
            loginModal.style.display = "none";
            loginContent.innerHTML = "";
        }
    });
});

// ✅ Pour cocher la case CGU automatiquement après lecture
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("open") === "signup") {
        const openSignupBtn = document.getElementById("open-signup");
        if (openSignupBtn) {
            openSignupBtn.click();

            const interval = setInterval(() => {
                const checkbox = document.getElementById("accept-checkbox");
                if (checkbox) {
                    // ✅ Cocher la case si accept_cgu=yes
                    if (params.get("accept_cgu") === "yes") {
                        checkbox.checked = true;
                        const hiddenInput = document.getElementById("terms_accepted");
                        if (hiddenInput) hiddenInput.value = "yes";
                    }

                    // ✅ Restauration dans tous les cas
                    if (typeof window.restoreSignupFormData === "function") {
                        window.restoreSignupFormData();
                    }

                    window.history.replaceState(null, '', '/'); // Nettoie l'URL
                    clearInterval(interval);
                }
            }, 100);
        }
    }
});


// 💾 Sauvegarde du formulaire dans localStorage
function saveSignupFormData() {
    const fields = [
        "last_name", "first_name", "gender", "birthday",
        "email", "phone", "username", "password"
    ];
    let formData = {};
    fields.forEach(id => {
        const input = document.getElementById(id);
        if (input) formData[id] = input.value;
    });
    localStorage.setItem("signupFormData", JSON.stringify(formData));
}

// ♻️ Restauration du formulaire
function restoreSignupFormData() {
    const savedData = localStorage.getItem("signupFormData");
    if (!savedData) return;
    const formData = JSON.parse(savedData);
    Object.entries(formData).forEach(([key, value]) => {
        const input = document.getElementById(key);
        if (input) input.value = value;
    });
}

// Rendre les fonctions globales (utilisable dans signup_modal.js)
window.saveSignupFormData = saveSignupFormData;
window.restoreSignupFormData = restoreSignupFormData;

// Nettoyage de la caméra en cas de fermuture modal par clik extérieur
window.addEventListener("click", (e) => {
    if (e.target === signupModal) {
        if (typeof stopSignupCamera === "function") stopSignupCamera();
        signupModal.style.display = "none";
        signupContent.innerHTML = "";
    }
    if (e.target === loginModal) {
        if (typeof stopLoginCamera === "function") stopLoginCamera();
        loginModal.style.display = "none";
        loginContent.innerHTML = "";
    }
});

