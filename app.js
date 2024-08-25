window.onload = () => {
  const API_KEY_FIELDS = ['openai_api_key', 'jina_api_key'];

  for (let apiKeyField of API_KEY_FIELDS) {
    document.getElementById(apiKeyField).addEventListener('input', () => {
      localStorage.setItem(apiKeyField, document.getElementById(apiKeyField).value);
    });
  }

  for (let apiKeyField of API_KEY_FIELDS) {
    const textbox = document.getElementById(apiKeyField);
    const apiKeyValue = localStorage.getItem(apiKeyField);
    if (apiKeyValue && textbox.value === '') {
      textbox.value = apiKeyValue;
    }
  }

  document.getElementById('text').addEventListener('change', () => {
    document.getElementById('num_flashcards').value = Math.round(document.getElementById('text').value.length / 234);
  });
}
