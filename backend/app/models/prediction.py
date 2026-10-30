from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="SET NULL"), nullable=True)
    image_path = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    crop_name = Column(String(100), nullable=True)
    disease_name = Column(String(200), nullable=True)
    pest_name = Column(String(200), nullable=True)
    prediction_type = Column(String(50), nullable=False, default="disease")  # disease, pest
    confidence = Column(Float, nullable=True)
    bbox_data = Column(JSON, nullable=True)  # Bounding box data as JSON
    status = Column(String(50), default="completed")
    is_demo = Column(String(10), default="false")  # Indicates if this was a demo/fallback prediction
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    farmer = relationship("User", back_populates="predictions")
    crop = relationship("Crop", back_populates="predictions")
    recommendations = relationship("Recommendation", back_populates="prediction", cascade="all, delete-orphan")
