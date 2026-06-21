class AuditMiddleware:
    """
    Middleware d'audit pour tracer les actions utilisateurs.
    Stub pour le développement.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Logique de capture d'audit (ex: IP, URL, User-Agent)
        # Sera utilisé pour alimenter le modèle AuditLog
        response = self.get_response(request)
        return response