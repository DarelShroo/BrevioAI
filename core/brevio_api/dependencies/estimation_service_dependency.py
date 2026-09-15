from core.brevio_api.services.estimation import EstimationService


def get_estimation_service() -> EstimationService:
    return EstimationService()
