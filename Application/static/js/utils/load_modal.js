function loadModal(url, modalContainer, contentContainer, scriptPath, initFunctionName, center = true) {
    fetch(url)
        .then(response => response.text())
        .then(html => {
            contentContainer.innerHTML = html;
            modalContainer.classList.remove("hidden");
            modalContainer.style.display = "flex";
            if (center) {
                modalContainer.style.alignItems = "center";
                modalContainer.style.justifyContent = "center";
            }

            if (scriptPath) {
                const script = document.createElement("script");
                script.src = scriptPath;
                script.onload = () => {
                    if (initFunctionName && typeof window[initFunctionName] === "function") {
                        window[initFunctionName]();
                    }
                };
                document.body.appendChild(script);
            } else if (initFunctionName && typeof window[initFunctionName] === "function") {
                window[initFunctionName]();
            }
        });
}
