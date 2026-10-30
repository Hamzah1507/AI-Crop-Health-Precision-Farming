from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True)
    soil_record_id = Column(Integer, ForeignKey("soil_records.id", ondelete="SET NULL"), nullable=True)
    farmer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # fertilizer, crop, irrigation, alert, treatment
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    prediction = relationship("Prediction", back_populates="recommendations")
    soil_record = relationship("SoilRecord", back_populates="recommendations")
    farmer = relationship("User", back_populates="recommendations")
