const toggleViewLayout = function (container, target, layout = null) {
  let layouts = ['grid-view', 'list-view'];

  let layoutPreferences = localStorage.getItem('view_layouts');
  layoutPreferences = layoutPreferences ? JSON.parse(layoutPreferences) : {};

  if (layout === null) {
    layout = layoutPreferences[target] || 'grid-view';
  }

  if (!layouts.includes(layout)) {
    layout = 'grid-view';
  }

  container.classList.remove(...layouts);
  container.classList.add(layout);

  layoutPreferences[target] = layout;
  localStorage.setItem('view_layouts', JSON.stringify(layoutPreferences));
};

const setViewLayouts = function () {
  let layoutPreferences = localStorage.getItem('view_layouts');
  layoutPreferences = layoutPreferences ? JSON.parse(layoutPreferences) : {};

  for (let target in layoutPreferences) {
    let container = document.getElementById(target);
    if (container) {
      toggleViewLayout(container, target, layoutPreferences[target]);
    }
  }
}

const boot = function () {
  let viewTogglers = document.querySelectorAll('.view-toggler');
  if (viewTogglers.length > 0) {
    setViewLayouts();

    viewTogglers.forEach(function (viewToggler) {
      viewToggler.addEventListener('click', function (e) {
        e.preventDefault();
        let target = this.getAttribute('data-target');
        let layout = this.getAttribute('data-layout');
        let container = document.getElementById(target);
        if (container) {
          toggleViewLayout(container, target, layout);
        }
      });
    });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  boot();
});