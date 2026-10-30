from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class YieldPrediction(Base):
    __tablename__ = "yield_predictions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    crop_name = Column(String(100), nullable=False)
    predicted_yield = Column(Float, nullable=True)
    yield_unit = Column(String(30), default="tons/hectare")
    confidence = Column(Float, nullable=True)
    area = Column(Float, nullable=True)
    soil_ph = Column(Float, nullable=True)
    soil_nitrogen = Column(Float, nullable=True)
    soil_phosphorus = Column(Float, nullable=True)
    soil_potassium = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)
    season = Column(String(50), nullable=True)
    is_demo = Column(String(10), default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    farmer = relationship("User", back_populates="yield_predictions")
    farm = relationship("Farm", back_populates="yield_predictions")
