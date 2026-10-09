from django.urls import path
from .views import AgentExplainView, AgentStatusView

urlpatterns = [
    path("status/", AgentStatusView.as_view(), name="agent-status"),
    path("explain/<int:intervention_id>/", AgentExplainView.as_view(), name="agent-explain"),
]
