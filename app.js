function persistentInputOnInput(element) {
  localStorage.setItem(element.id, element.value);
}

function persistentInputOnLoad(id) {
  const textbox = document.getElementById(id);
  const apiKeyValue = localStorage.getItem(id);
  if (apiKeyValue && textbox.value === '') {
    textbox.value = apiKeyValue;
  }
}

function textOnChange() {
  document.getElementById('num_flashcards').value = Math.round(document.getElementById('text').value.length / 234);
}

function downloadOnClick(event) {
  event.preventDefault();
  const content = document.getElementById('flashcards').value;
  const blob = new Blob([content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'flashcards.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

