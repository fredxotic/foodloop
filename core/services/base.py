"""
Enhanced Base Service with Standardized Response Format
"""
from typing import Tuple, Any, Optional, Dict
from django.db import DatabaseError
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class ServiceResponse:
    """Standardized service response object"""
    
    def __init__(self, success: bool, data: Any = None, message: str = "", errors: Dict = None):
        self.success = success
        self.data = data
        self.message = message
        self.errors = errors or {}
    
    def to_tuple(self) -> Tuple[bool, Any, str]:
        """Convert to tuple for backward compatibility"""
        return self.success, self.data, self.message
    
    def __bool__(self):
        return self.success


class BaseService:
    """Enhanced base service with consistent patterns"""
    
    @staticmethod
    def success(data: Any = None, message: str = "") -> ServiceResponse:
        """Return success response"""
        return ServiceResponse(success=True, data=data, message=message)
    
    @staticmethod
    def error(message: str, data: Any = None, errors: Dict = None) -> ServiceResponse:
        """Return error response"""
        return ServiceResponse(success=False, data=data, message=message, errors=errors)
    
    @classmethod
    def handle_exception(cls, exception: Exception, context: str = "") -> ServiceResponse:
        """Standardized exception handling"""
        error_context = f"{context}: " if context else ""
        
        if isinstance(exception, ValidationError):
            error_msg = f"{error_context}Validation error - {str(exception)}"
            logger.warning(error_msg)
        elif isinstance(exception, DatabaseError):
            error_msg = f"{error_context}Database error - {str(exception)}"
            logger.error(error_msg, exc_info=True)
        else:
            error_msg = f"{error_context}Unexpected error - {str(exception)}"
            logger.exception(error_msg)
        
        return cls.error(error_msg)
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: list) -> Optional[str]:
        """Validate required fields in data dictionary"""
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return f"Missing required fields: {', '.join(missing_fields)}"
        return None