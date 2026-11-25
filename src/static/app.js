const searchInput = document.querySelector("[data-table-search]");
const searchableRows = document.querySelector("[data-searchable-rows]");

if (searchInput && searchableRows) {
  const rows = [...searchableRows.querySelectorAll("tr")];

  searchInput.addEventListener("input", () => {
    const query = searchInput.value.trim().toLocaleLowerCase();

    for (const row of rows) {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
    }
  });
}
