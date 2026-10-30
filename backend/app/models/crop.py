from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    variety = Column(String(100), nullable=True)
    planting_date = Column(Date, nullable=True)
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    farm = relationship("Farm", back_populates="crops")
    soil_records = relationship("SoilRecord", back_populates="crop", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="crop", cascade="all, delete-orphan")
