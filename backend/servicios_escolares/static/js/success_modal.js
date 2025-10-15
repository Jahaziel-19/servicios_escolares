document.addEventListener("DOMContentLoaded", function () {
  const successContainer = document.getElementById("successData");
  if (successContainer) {
    const raw = successContainer.getAttribute("data-success");
    const successList = JSON.parse(raw || "[]");

    if (successList.length > 0) {
      const listEl = document.getElementById("successList");
      successList.forEach(msg => {
        const li = document.createElement("li");
        li.textContent = msg;
        listEl.appendChild(li);
      });

      const modal = new bootstrap.Modal(document.getElementById("successModal"));
      modal.show();
    }
  }
});
