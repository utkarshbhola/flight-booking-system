from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

    bookings = relationship("Booking", back_populates="user")


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String, unique=True, index=True)
    departure_city = Column(String)
    arrival_city = Column(String)
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    total_seats = Column(Integer)  # This is just a number
    price = Column(Integer)

    # This is a one-to-many relationship with Seat
    seat_list = relationship("Seat", back_populates="flight")  # Use a name that's not a column!

    bookings = relationship("Booking", back_populates="flight")


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"))
    seat_number = Column(String)        
    is_booked = Column(Boolean, default=False)
    flight = relationship("Flight", back_populates="seat_list")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    booking_time = Column(DateTime(timezone=True), server_default=func.now())

    flight = relationship("Flight")
    user = relationship("User")
    seat = relationship("Seat")
