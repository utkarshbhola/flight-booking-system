from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    class Config:
        orm_mode = True  # This tells Pydantic to convert ORM model to dict

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class FlightCreate(BaseModel):
    id: int
    flight_number: str
    departure_city: str
    arrival_city: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    price: int

class FlightUpdate(FlightCreate):
    id: int
class SeatCreate(BaseModel):
    flight_id: int
    seat_number: str
    is_booked: bool

class BookingCreate(BaseModel):
    flight_id: int
    seat_id: int
    user_id: int
