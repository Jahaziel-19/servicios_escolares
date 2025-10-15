function showProgressBar() {
  const modal = new bootstrap.Modal(document.getElementById('progressModal'));
  document.getElementById('progressBar').style.width = '0%';
  document.getElementById('progressBar').innerText = '0%';
  modal.show();

  let progress = 0;
  const interval = setInterval(() => {
    progress += 10;
    if (progress >= 90) clearInterval(interval); // no pasar del 90%
    updateProgress(progress);
  }, 500);
}

function updateProgress(value) {
  const bar = document.getElementById('progressBar');
  bar.style.width = `${value}%`;
  bar.innerText = `${value}%`;
}

function completeProgress() {
  updateProgress(100);
  setTimeout(() => {
    const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
    modal.hide();
  }, 500);
}
