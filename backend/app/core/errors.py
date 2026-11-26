class AppError(Exception):
    """Base application error with an HTTP status and safe message."""
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ValidationError(AppError):
    status_code = 422


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UpstreamError(AppError):
    status_code = 502
