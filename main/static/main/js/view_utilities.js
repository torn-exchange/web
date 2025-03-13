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

function handleFilterResize() {
    const element = document.querySelector('.filter-container');
    if (window.innerWidth < 768) {
        element?.classList.remove('filter-show');
    } else {
        element?.classList.add('filter-show');
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

  handleFilterResize();
  let filterTogglers = document.querySelectorAll('.filter-toggler');
  console.log(filterTogglers);
  if (filterTogglers.length > 0) {
    filterTogglers.forEach(function (filterToggler) {
      console.log(filterToggler);
      filterToggler.addEventListener('click', function (e) {
        console.log('clicked');
        e.preventDefault();
        let target = this.getAttribute('data-target');
        let container = document.getElementById(target);
        if (container) {
          container.classList.toggle('filter-show');
        }
      });
    });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  // Restores user preference layout on page load
  boot();
});