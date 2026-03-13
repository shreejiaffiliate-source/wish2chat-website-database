document.addEventListener("DOMContentLoaded", function () {
  const masterSelect = document.querySelector("#id_master_category");
  const subSelect = document.querySelector("#id_sub_category");

  if (masterSelect && subSelect) {
    masterSelect.addEventListener("change", function () {
      const masterId = this.value;
      const url = `/ajax/load-subcategories/?master_id=${masterId}`;

      // Reset sub-category dropdown
      subSelect.innerHTML = '<option value="">---------</option>';

      if (masterId) {
        fetch(url)
          .then((response) => response.json())
          .then((data) => {
            data.forEach((item) => {
              const option = document.createElement("option");
              option.value = item.id;
              option.textContent = item.name;
              subSelect.appendChild(option);
            });
          })
          .catch((error) =>
            console.error("Error loading subcategories:", error)
          );
      }
    });
  }
});
