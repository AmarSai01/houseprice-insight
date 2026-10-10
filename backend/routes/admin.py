"""
Admin routes: user management, model retraining, metrics.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_admin_user
from database import get_db
from ml.predict import get_predictor
from ml.train import train_model
from models import Prediction, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserResponse(BaseModel):
    """User response model."""
    id: int
    name: str
    email: str
    role: str
    created_at: str
    prediction_count: int


class PredictionResponse(BaseModel):
    """Prediction response model."""
    id: int
    user_id: int
    user_name: str
    user_email: str
    input_features: Dict[str, Any]
    predicted_value: float
    timestamp: str


class MetricsResponse(BaseModel):
    """Model metrics response."""
    train_mae: float
    test_mae: float
    train_rmse: float
    test_rmse: float
    train_r2: float
    test_r2: float


class RetrainRequest(BaseModel):
    """Retrain request model."""
    csv_path: Optional[str] = None


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)."""
    users = db.query(User).all()
    
    result = []
    for user in users:
        prediction_count = db.query(Prediction).filter(Prediction.user_id == user.id).count()
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
            "prediction_count": prediction_count
        })
    
    return result


@router.get("/predictions", response_model=List[PredictionResponse])
async def get_all_predictions(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = 100
):
    """Get all predictions (admin only)."""
    predictions = db.query(Prediction).join(User).order_by(
        Prediction.timestamp.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "user_name": p.user.name,
            "user_email": p.user.email,
            "input_features": p.input_features,
            "predicted_value": p.predicted_value,
            "timestamp": p.timestamp.isoformat()
        }
        for p in predictions
    ]


@router.get("/metrics", response_model=MetricsResponse)
async def get_model_metrics(
    current_user: User = Depends(get_current_admin_user)
):
    """Get model performance metrics (admin only)."""
    try:
        predictor = get_predictor()
        metrics = predictor.get_metrics()

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Metrics not available",
            )

        return metrics
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics.",
        )


def retrain_model_task(csv_path: str):
    """Background task to retrain the model."""
    try:
        train_model(csv_path)
    except Exception:
        # Keep failure details server-side only.
        logger.exception("Model retraining failed for dataset path=%s", csv_path)


@router.post("/retrain")
async def retrain_model(
    background_tasks: BackgroundTasks,
    request: RetrainRequest = RetrainRequest(),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Retrain the ML model (admin only).
    Can be called with optional csv_path in request body.
    """
    # Default CSV path
    csv_path = request.csv_path if request.csv_path else os.getenv("DATASET_PATH", "data/house_data.csv")

    if not os.path.exists(csv_path):
        # Path may be logged for operators; never returned to the client.
        logger.warning(
            "Admin retrain refused: dataset unavailable path=%s",
            csv_path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file could not be processed.",
        )

    # Run retraining in background
    background_tasks.add_task(retrain_model_task, csv_path)

    return {
        "message": "Model retraining started in background",
        "status": "success"
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)."""
    if new_role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user' or 'admin'"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = new_role
    db.commit()
    db.refresh(user)
    
    return {"message": "User role updated successfully", "user": user}
