import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """요청 로깅 미들웨어"""

    def process_request(self, request):
        # 요청 정보 로깅 (한글 처리)
        try:
            logger.info(f"Request: {request.method} {request.path}")
            if request.body:
                logger.debug(f"Request Body: {request.body.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.warning(f"Request logging failed: {e}")

        return None

    def process_response(self, request, response):
        # 응답 정보 로깅
        try:
            logger.info(f"Response: {response.status_code} for {request.path}")
        except Exception as e:
            logger.warning(f"Response logging failed: {e}")

        return response


class CORSMiddleware(MiddlewareMixin):
    """CORS 헤더 추가 미들웨어"""

    def process_response(self, request, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response["Access-Control-Max-Age"] = "3600"

        return response