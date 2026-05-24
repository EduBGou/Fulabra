document.addEventListener("htmx:afterSettle", (e) => {
  focusInvalidField(e.detail.elt)
})

function focusInvalidField(parentForm) {
  const ipt = parentForm.querySelector('.is-invalid')

  if (ipt) {
    let type = ipt.type
    if (type !== 'text') ipt.type = 'text'
    ipt.focus()
    const atIndex = ipt.value.indexOf('@')

    if (atIndex === -1) {
      const endPos = ipt.value.length
      ipt.setSelectionRange(endPos, endPos)
    } else {
      ipt.setSelectionRange(atIndex, atIndex)
    }

    ipt.type = type
  }
}