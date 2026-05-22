document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (!form) return; 

    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    
    const initialData = new FormData(form);
    const initialState = Array.from(initialData.entries()).toString();

    function setButtonState(isDisabled) {
        submitBtn.disabled = isDisabled;
        if (isDisabled) {
            submitBtn.style.cursor = 'default';
        } else {
            submitBtn.style.cursor = '';
        }
    }

    setButtonState(true);

    form.addEventListener('input', () => {
        const currentData = new FormData(form);
        const currentState = Array.from(currentData.entries()).toString();
        const noneChanged = (initialState === currentState);
        setButtonState(noneChanged);
    });
});