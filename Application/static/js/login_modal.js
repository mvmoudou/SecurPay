document.addEventListener('DOMContentLoaded', function() {
    // Éléments du DOM
    const loginModal = document.getElementById('login-modal');
    const loginForm = document.getElementById('login-form');
    const closeBtn = document.querySelector('.close-login-btn');
    const goToSignupBtn = document.getElementById('go-to-signup');
    const startFaceLoginBtn = document.getElementById('start-face-login');
    const cameraPreview = document.getElementById('camera-preview-login');
    const video = document.getElementById('video-login');
    const captureBtn = document.getElementById('capture-login');
    const cancelBtn = document.getElementById('cancel-login-capture');
    const verificationPopup = document.getElementById('face-verification-popup');

    // Gestionnaire pour la soumission du formulaire
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(loginForm);
        try {
            const response = await fetch('/login-modal', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                window.location.href = data.redirect;
            } else {
                alert(data.message);
            }
        } catch (error) {
            console.error('Erreur:', error);
            alert('Erreur de connexion');
        }
    });

    // Gestionnaire pour le bouton de fermeture
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            loginModal.style.display = 'none';
        });
    }

    // Gestionnaire pour le lien d'inscription
    if (goToSignupBtn) {
        goToSignupBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = '/signup-modal';
        });
    }

    // Gestionnaire pour le bouton de connexion par reconnaissance faciale
    startFaceLoginBtn.addEventListener('click', async function() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            cameraPreview.style.display = 'block';
            loginForm.style.display = 'none'; // Cache le formulaire pendant la capture
        } catch (err) {
            console.error('Erreur caméra:', err);
            alert('Impossible d\'accéder à la caméra');
        }
    });

    // Gestionnaire pour le bouton de capture
    captureBtn.addEventListener('click', async function() {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        
        const imageData = canvas.toDataURL('image/png');
        
        // Arrêter la caméra
        video.srcObject.getTracks().forEach(track => track.stop());
        cameraPreview.style.display = 'none';
        verificationPopup.style.display = 'block';

        try {
            const response = await fetch('/login-face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const data = await response.json();
            verificationPopup.style.display = 'none';
            
            if (response.ok) {
                window.location.href = data.redirect;
            } else {
                alert(data.message);
                loginForm.style.display = 'block'; // Réaffiche le formulaire en cas d'échec
            }
        } catch (error) {
            verificationPopup.style.display = 'none';
            console.error('Erreur:', error);
            alert('Erreur de vérification faciale');
            loginForm.style.display = 'block'; // Réaffiche le formulaire en cas d'erreur
        }
    });

    // Gestionnaire pour le bouton d'annulation
    cancelBtn.addEventListener('click', function() {
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
        }
        cameraPreview.style.display = 'none';
        loginForm.style.display = 'block'; // Réaffiche le formulaire
    });

    // Fermer la modal si on clique en dehors
    window.addEventListener('click', function(e) {
        if (e.target === loginModal) {
            loginModal.style.display = 'none';
        }
    });

    // Ouvrir la modal de connexion si nécessaire (par exemple via un bouton sur la page principale)
    document.querySelectorAll('.open-login-modal').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            loginModal.style.display = 'block';
        });
    });
});

// Fonction utilitaire pour afficher les messages d'erreur
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    loginForm.insertBefore(errorDiv, loginForm.firstChild);
    
    // Supprimer le message après 3 secondes
    setTimeout(() => {
        errorDiv.remove();
    }, 3000);
}