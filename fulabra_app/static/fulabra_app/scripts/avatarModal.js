// Impede o navegador de tentar abrir a imagem
window.addEventListener("dragover", e => e.preventDefault(), false);
window.addEventListener("drop", e => e.preventDefault(), false);

document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById("id_avatar");
    const presetHiddenInput = document.getElementById("id_selected_preset");
    const mainPreviewImg = document.getElementById("current-avatar-preview");
    const form = document.querySelector('#profileForm');
    
    const btnTriggerSelect = document.getElementById("triggerFileSelect");
    const presetImages = document.querySelectorAll(".preset-option");

    const uploadBox = document.querySelector(".upload-box");

    // Drag and drop
    if (uploadBox && fileInput) {
        // Bloqueia o navegador de abrir a imagem noutra aba
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadBox.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        uploadBox.addEventListener('drop', function(e) {
            let dt = e.dataTransfer;
            let files = dt.files;

            if (files && files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }, false);
    }

    if (btnTriggerSelect && fileInput) {
        btnTriggerSelect.addEventListener("click", function() {
            fileInput.click();
        });
    }

    // Se o usuário selecionou um arquivo do computador
    if (fileInput) {
        fileInput.addEventListener("change", function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    mainPreviewImg.src = e.target.result;
                    presetHiddenInput.value = "";
                    form.dispatchEvent(new Event('avatarChanged', { bubbles: true }));
                }

                reader.readAsDataURL(this.files[0]);

                $('#avatarModal').modal('hide');
            }
        });
    }

    // Se o usuario escolheu um preset
    presetImages.forEach(img => {
        img.addEventListener("click", function() {
            const filename = this.getAttribute("data-filename");
            
            if (presetHiddenInput) {
                presetHiddenInput.value = filename;
            }

            mainPreviewImg.src = this.src;
            
            if (fileInput) fileInput.value = "";
        
            form.dispatchEvent(new Event('avatarChanged', { bubbles: true }));

            $('#avatarModal').modal('hide');
        });
    });

    // Remover avatar
    const btnRemoveAvatar = document.getElementById("btn-remove-avatar");
    if (btnRemoveAvatar) {
        btnRemoveAvatar.addEventListener("click", function() {
            if (presetHiddenInput) {
                presetHiddenInput.value = "default_avatar.png"; 
            }
            if (fileInput) {
                fileInput.value = "";
            }
            mainPreviewImg.src = "/static/fulabra_app/images/avatars/default_avatar.png"; 

            if(form) form.dispatchEvent(new Event('avatarChanged', { bubbles: true }));
        });
    }
});