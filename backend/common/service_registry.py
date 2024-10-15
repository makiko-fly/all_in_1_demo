import redis
import json
import uuid

class ServiceRegistry:
    def __init__(self, redis_host='redis', redis_port=6379):
        self.redis = redis.Redis(host=redis_host, port=redis_port)

    def register(self, service_name, host, port):
        instance_id = str(uuid.uuid4())
        service_info = json.dumps({'host': host, 'port': port, 'id': instance_id})
        self.redis.sadd(f'services:{service_name}', service_info)
        return instance_id

    def deregister(self, service_name, instance_id):
        services = self.redis.smembers(f'services:{service_name}')
        for service in services:
            service_info = json.loads(service)
            if service_info['id'] == instance_id:
                self.redis.srem(f'services:{service_name}', service)
                break

    def get_service(self, service_name):
        services = self.redis.smembers(f'services:{service_name}')
        if services:
            return [json.loads(service) for service in services]
        return None
