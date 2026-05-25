document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById("id_avatar");
    const presetHiddenInput = document.getElementById("id_selected_preset");
    const mainPreviewImg = document.getElementById("current-avatar-preview");
    
    const btnTriggerSelect = document.getElementById("triggerFileSelect");
    const presetImages = document.querySelectorAll(".preset-option");

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

            $('#avatarModal').modal('hide');
        });
    });
});