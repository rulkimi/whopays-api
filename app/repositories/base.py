"""Base repository class with common CRUD operations."""

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, text

from app.db.base_class import Base, AuditMixin

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType], ABC):
    """Base repository class providing common CRUD operations.
    
    Provides:
    - Standard CRUD operations (Create, Read, Update, Delete)
    - Soft delete support for models with AuditMixin
    - Query filtering and pagination
    - Structured logging for data operations
    """
    
    def __init__(self, db: Session, model: Type[ModelType], correlation_id: Optional[str] = None):
        """Initialize repository with database session and model type.
        
        Args:
            db: SQLAlchemy database session
            model: SQLAlchemy model class
            correlation_id: Optional request correlation ID for logging
        """
        self.db = db
        self.model = model
        self.correlation_id = correlation_id
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create(self, obj_in: CreateSchemaType, **kwargs: Any) -> ModelType:
        """Create a new record in the database.
        
        Args:
            obj_in: Pydantic model or dict with creation data
            **kwargs: Additional fields to set on the model
            
        Returns:
            Created model instance
            
        Raises:
            SQLAlchemyError: On database operation failure
        """
        try:
            if hasattr(obj_in, 'dict'):
                # Pydantic model
                obj_data = obj_in.dict(exclude_unset=True)
            else:
                # Dictionary
                obj_data = obj_in
            
            obj_data.update(kwargs)
            db_obj = self.model(**obj_data)
            
            self.db.add(db_obj)
            self.db.flush()
            self.db.refresh(db_obj)
            
            self._log_operation("create", model=self.model.__name__, id=getattr(db_obj, 'id', None))
            return db_obj
            
        except SQLAlchemyError as e:
            self.logger.error(
                f"Failed to create {self.model.__name__}",
                extra={
                    "correlation_id": self.correlation_id,
                    "repository": self.__class__.__name__,
                    "error": str(e)
                }
            )
            raise
    
    def get_by_id(self, id: int, include_deleted: bool = False) -> Optional[ModelType]:
        """Get a record by ID.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Model instance or None if not found
        """
        query = self.db.query(self.model).filter(self.model.id == id)
        
        # Apply soft delete filter if model has AuditMixin
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        result = query.first()
        self._log_operation("get_by_id", model=self.model.__name__, id=id, found=result is not None)
        return result
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted records
            filters: Dictionary of field filters
            order_by: Field name to order by
            
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Apply soft delete filter if model has AuditMixin
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
            self._log_operation("get_multi_soft_delete_filter", model=self.model.__name__, include_deleted=include_deleted, has_is_deleted=hasattr(self.model, 'is_deleted'))
        
        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
                    self._log_operation("get_multi_applying_filter", model=self.model.__name__, field=field, value=value)
                else:
                    self._log_operation("get_multi_filter_field_not_found", model=self.model.__name__, field=field)
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            # Default to descending for created_at, ascending for others
            if order_by == 'created_at':
                query = query.order_by(order_field.desc())
            else:
                query = query.order_by(order_field)
            self._log_operation("get_multi_applying_order", model=self.model.__name__, order_by=order_by)
        else:
            self._log_operation("get_multi_no_order", model=self.model.__name__, order_by=order_by, has_order_by=hasattr(self.model, order_by) if order_by else None)
        
        # Log query before execution
        self._log_operation("get_multi_before_execution", model=self.model.__name__, skip=skip, limit=limit)
        
        results = query.offset(skip).limit(limit).all()
        
        # Log detailed results
        result_details = []
        for r in results:
            result_details.append({
                "id": getattr(r, 'id', None),
                "is_deleted": getattr(r, 'is_deleted', None),
                "user_id": getattr(r, 'user_id', None) if hasattr(r, 'user_id') else None
            })
        
        self._log_operation(
            "get_multi",
            model=self.model.__name__,
            count=len(results),
            skip=skip,
            limit=limit,
            result_details=result_details
        )
        return results
    
    def update(self, id: int, obj_in: UpdateSchemaType, **kwargs: Any) -> Optional[ModelType]:
        """Update a record by ID.
        
        Args:
            id: Record ID
            obj_in: Pydantic model or dict with update data
            **kwargs: Additional fields to update
            
        Returns:
            Updated model instance or None if not found
            
        Raises:
            SQLAlchemyError: On database operation failure
        """
        try:
            db_obj = self.get_by_id(id)
            if not db_obj:
                return None
            
            if hasattr(obj_in, 'dict'):
                # Pydantic model
                update_data = obj_in.dict(exclude_unset=True)
            else:
                # Dictionary
                update_data = obj_in
            
            update_data.update(kwargs)
            
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.db.flush()
            self.db.refresh(db_obj)
            
            self._log_operation("update", model=self.model.__name__, id=id)
            return db_obj
            
        except SQLAlchemyError as e:
            self.logger.error(
                f"Failed to update {self.model.__name__} with id {id}",
                extra={
                    "correlation_id": self.correlation_id,
                    "repository": self.__class__.__name__,
                    "error": str(e)
                }
            )
            raise
    
    def delete(self, id: int, soft_delete: bool = True) -> bool:
        """Delete a record by ID.
        
        Args:
            id: Record ID
            soft_delete: Whether to perform soft delete (if model supports it)
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: On database operation failure
        """
        try:
            db_obj = self.get_by_id(id)
            if not db_obj:
                return False
            
            if soft_delete and hasattr(db_obj, 'is_deleted'):
                # Soft delete
                db_obj.is_deleted = True
                if hasattr(db_obj, 'deleted_at'):
                    db_obj.deleted_at = self.db.execute(text('SELECT NOW()')).scalar()
                self.db.flush()
            else:
                # Hard delete
                self.db.delete(db_obj)
                self.db.flush()
            
            self._log_operation("delete", model=self.model.__name__, id=id, soft=soft_delete)
            return True
            
        except SQLAlchemyError as e:
            self.logger.error(
                f"Failed to delete {self.model.__name__} with id {id}",
                extra={
                    "correlation_id": self.correlation_id,
                    "repository": self.__class__.__name__,
                    "error": str(e)
                }
            )
            raise
    
    def exists(self, id: int, include_deleted: bool = False) -> bool:
        """Check if a record exists by ID.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            True if record exists, False otherwise
        """
        query = self.db.query(self.model.id).filter(self.model.id == id)
        
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        result = query.first() is not None
        self._log_operation("exists", model=self.model.__name__, id=id, exists=result)
        return result
    
    def count(self, filters: Optional[Dict[str, Any]] = None, include_deleted: bool = False) -> int:
        """Count records with optional filtering.
        
        Args:
            filters: Dictionary of field filters
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Number of matching records
        """
        query = self.db.query(self.model)
        
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        
        result = query.count()
        self._log_operation("count", model=self.model.__name__, count=result)
        return result
    
    def _log_operation(self, operation: str, **kwargs: Any) -> None:
        """Log repository operation with structured fields.
        
        Args:
            operation: Name of the operation being performed
            **kwargs: Additional fields to include in log
        """
        log_data = {
            "correlation_id": self.correlation_id,
            "repository": self.__class__.__name__,
            "operation": operation,
            **kwargs
        }
        self.logger.info(f"Repository operation: {operation}", extra=log_data)
