document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('#profileForm');
    if (!form) return; 

    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;

    const nicknameInput = form.querySelector('[name="nickname"]');
    const initialNickname = nicknameInput ? nicknameInput.value : "";

    let avatarWasChanged = false;

    function checkChanges() {
        const currentNickname = nicknameInput ? nicknameInput.value : "";
        const nicknameChanged = (currentNickname !== initialNickname);

        if (nicknameChanged || avatarWasChanged) {
            submitBtn.disabled = false;
            submitBtn.style.cursor = '';
        } else {
            submitBtn.disabled = true;
            submitBtn.style.cursor = 'default';
        }
    }

    checkChanges();

    if (nicknameInput) {
        nicknameInput.addEventListener('input', checkChanges);
    }

    form.addEventListener('avatarChanged', function() {
        avatarWasChanged = true;
        checkChanges();
    });
});