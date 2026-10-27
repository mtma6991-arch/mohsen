(function () {
  var mapNode = document.getElementById("template-map");
  var category = document.querySelector("[name=category]");
  var template = document.querySelector("[name=template]");
  if (!mapNode || !category || !template) return;
  var rows = [];
  try { rows = JSON.parse(mapNode.textContent || "[]"); } catch (e) { rows = []; }
  var current = template.value;
  function ensureCategorySelected() {
    if (category.value) return;
    for (var i = 0; i < category.options.length; i++) {
      if (category.options[i].value) {
        category.value = category.options[i].value;
        break;
      }
    }
  }
  function refill() {
    ensureCategorySelected();
    var id = String(category.value || "");
    var options = rows.filter(function (row) { return String(row.category_id) === id; });
    if (!options.length && rows.length && !id) {
      options = rows;
    }
    if (!options.length) {
      template.innerHTML = '<option value="">قالبی برای این دسته ثبت نشده است</option>';
      return;
    }
    template.innerHTML = options.map(function (row) {
      return '<option value="' + row.id + '">' + row.name + " · " + row.version + "</option>";
    }).join("");
    if (options.some(function (row) { return String(row.id) === String(current); })) {
      template.value = current;
    } else {
      template.value = String(options[0].id);
      current = template.value;
    }
  }
  category.addEventListener("change", function () {
    current = "";
    refill();
  });
  refill();
})();
