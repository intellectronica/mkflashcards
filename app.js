const API_KEY_FIELDS = ['OPENAI_API_KEY', 'JINA_API_KEY'];

function getAPIKeyTextbox(apiKeyField) {
  return document.getElementById(apiKeyField).getElementsByTagName('input')[0];
}

function initializeTextboxListeners() {
  for (let apiKeyField of API_KEY_FIELDS) {
    getAPIKeyTextbox(apiKeyField).addEventListener('input', () => {
      localStorage.setItem(apiKeyField, getAPIKeyTextbox(apiKeyField).value);
    });
  }
}

function populateTextboxesFromLocalStorsge() {
  for (let apiKeyField of API_KEY_FIELDS) {
    const textbox = getAPIKeyTextbox(apiKeyField);
    const apiKeyValue = localStorage.getItem(apiKeyField);
    if (apiKeyValue && textbox.value === '') {
      textbox.value = apiKeyValue;
    }
  }
}

window.setTimeout(() => {
  initializeTextboxListeners();
  populateTextboxesFromLocalStorsge();
}, 1234);
