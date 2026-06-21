class RateLimitMiddleware:
    """
    Middleware de limitation de débit (Rate Limiting).
    Stub pour le développement.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Logique de limitation de débit à implémenter ici
        # Pour l'instant, on laisse passer toutes les requêtes
        response = self.get_response(request)
        return response