from django.urls import path

from .frontend_views import (
    KanbanView,
    LeadDetailView,
    LeadListView,
    LeadLoseView,
    LeadMoveStageView,
    LeadWinView,
)

app_name = 'crm'

urlpatterns = [
    path('leads/',                       LeadListView.as_view(),    name='lead-list'),
    path('kanban/',                      KanbanView.as_view(),      name='kanban'),
    path('leads/<uuid:pk>/',             LeadDetailView.as_view(),  name='lead-detail'),
    path('leads/<uuid:pk>/win/',         LeadWinView.as_view(),     name='lead-win'),
    path('leads/<uuid:pk>/lose/',        LeadLoseView.as_view(),    name='lead-lose'),
    path('leads/<uuid:pk>/move-stage/',  LeadMoveStageView.as_view(), name='lead-move-stage'),
]
