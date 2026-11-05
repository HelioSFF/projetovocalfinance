class AppError(Exception):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.debug: dict | None = None


class ProviderError(AppError):
    def __init__(self):
        super().__init__("AI_UNAVAILABLE", "Serviço de voz indisponível. Tente em instantes.", 503)
