(function () {
  var mapNode = document.getElementById("template-map");
  var category = document.querySelector("[name=category]");
  var template = document.querySelector("[name=template]");
  if (!mapNode || !category || !template) return;
  var rows = [];
  try { rows = JSON.parse(mapNode.textContent || "[]"); } catch (e) { rows = []; }
  var current = template.value;
  function refill() {
    var id = String(category.value || "");
    var options = rows.filter(function (row) { return String(row.category_id) === id; });
    template.innerHTML = options.map(function (row) {
      return '<option value="' + row.id + '">' + row.name + " · " + row.version + "</option>";
    }).join("");
    if (options.some(function (row) { return String(row.id) === String(current); })) {
      template.value = current;
    }
  }
  category.addEventListener("change", function () {
    current = "";
    refill();
  });
  refill();
})();
