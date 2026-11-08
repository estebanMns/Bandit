"""Convierte eventos de dominio en mensajes para el navegador."""

from bandit.analysis.public import ActivityEntryResponse, AnalysisActivity
from bandit.cameras.public import CameraStatusChanged
from bandit.incidents.public import IncidentChanged, IncidentResponse
from bandit.realtime.application.event_hub import EventHub


class LiveEventPublisher:
    def __init__(self, hub: EventHub) -> None:
        self._hub = hub

    async def on_incident_changed(self, event: IncidentChanged) -> None:
        incident = IncidentResponse.of(event.incident)
        self._hub.publish(
            event.incident.establishment_id,
            {"type": "incident", "incident": incident.model_dump(mode="json")},
        )

    async def on_camera_status(self, event: CameraStatusChanged) -> None:
        self._hub.publish(
            event.establishment_id,
            {"type": "camera", "cameraId": str(event.camera_id), "status": event.status.value},
        )

    async def on_analysis_activity(self, event: AnalysisActivity) -> None:
        entry = ActivityEntryResponse.of(event.camera_id, event)
        self._hub.publish(
            event.establishment_id,
            {
                "type": "analysis",
                "cameraName": event.camera_name,
                "entry": entry.model_dump(mode="json"),
            },
        )
