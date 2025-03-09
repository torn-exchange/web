// Toggle view layout
const toggleViewLayout = function (container, target, layout = null) {
  // Available layouts
  let layouts = ['grid-view', 'list-view'];

  let layoutPreferences = localStorage.getItem('view_layouts');
  // Grab User layout preferences and parse the JSON string and convert it into a JavaScript object
  layoutPreferences = layoutPreferences ? JSON.parse(layoutPreferences) : {};

  if (layout === null) {
    layout = layoutPreferences[target] || 'grid-view';
  }

  if (!layouts.includes(layout)) {
    // Default layout
    layout = 'grid-view';
  }

  // Remove all layouts
  container.classList.remove(...layouts);
  // Add the selected layout
  container.classList.add(layout);

  layoutPreferences[target] = layout;
  // Save user preference layout
  localStorage.setItem('view_layouts', JSON.stringify(layoutPreferences));
};

// Set the view layout
const setViewLayouts = function () {
  let layoutPreferences = localStorage.getItem('view_layouts');
  layoutPreferences = layoutPreferences ? JSON.parse(layoutPreferences) : {};

  for (let target in layoutPreferences) {
    let container = document.getElementById(target);
    // Check if the container exists, so that we don't run unnecessary logic
    if (container) {
      toggleViewLayout(container, target, layoutPreferences[target]);
    }
  }
}

// Initialize the view layout
const boot = function () {
  let viewTogglers = document.querySelectorAll('.view-toggler');
  if (viewTogglers.length > 0) {
    setViewLayouts();

    viewTogglers.forEach(function (viewToggler) {
      viewToggler.addEventListener('click', function (e) {
        // Prevent the default action of the link, if any, recommended to use <a href="javascript:void(0)">
        e.preventDefault();
        let target = this.getAttribute('data-target');
        let layout = this.getAttribute('data-layout');
        let container = document.getElementById(target);
        // Check if the container exists, so that we don't run unnecessary logic
        if (container) {
          toggleViewLayout(container, target, layout);
        }
      });
    });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  // Restores user preference layout on page load
  boot();
});