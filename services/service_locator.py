class ServiceLocator:
    _services = {}

    @classmethod
    def add(cls, service_name: str, service):
        cls._services[service_name] = service

    @classmethod
    def get(cls, service_name: str):
        return cls._services.get(service_name)