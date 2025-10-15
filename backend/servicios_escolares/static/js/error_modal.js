function showError(message) {
  const errorMessage = document.getElementById('errorMessage');
  errorMessage.innerText = message;
  const modal = new bootstrap.Modal(document.getElementById('errorModal'));
  modal.show();
}
