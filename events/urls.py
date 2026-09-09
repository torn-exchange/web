from django.urls import path

from . import views
from .treasury import views as treasury_views
from .captain import views as captain_views

urlpatterns = [
    path("", views.event_index, name="event_index"),

    # Elimination treasury (Phase 2)
    path("elimination/treasury/", treasury_views.treasury_home, name="treasury_home"),
    path("elimination/treasury/import", treasury_views.treasury_import, name="treasury_import"),
    path("elimination/treasury/entry/add", treasury_views.treasury_add_entry, name="treasury_add_entry"),
    path("elimination/treasury/entry/<int:entry_id>/delete", treasury_views.treasury_delete_entry, name="treasury_delete_entry"),
    path("elimination/treasury/request", treasury_views.treasury_request_create, name="treasury_request_create"),
    path("elimination/treasury/request/<int:request_id>/cancel", treasury_views.treasury_request_cancel, name="treasury_request_cancel"),
    path("elimination/treasury/request/<int:request_id>/decline", treasury_views.treasury_decline_request, name="treasury_decline_request"),
    path("elimination/treasury/line/<int:line_id>/fulfil", treasury_views.treasury_fulfil_line, name="treasury_fulfil_line"),

    # Elimination captain (Phase 2)
    path("elimination/captain/", captain_views.captain_dashboard, name="captain_dashboard"),
    path("elimination/captain/role", captain_views.captain_set_role, name="captain_set_role"),

    path("<str:key>/", views.event_page, name="event_page"),
]
