from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class FlightCreate(BaseModel):
    id: int
    flight_number: str
    departure_city: str
    arrival_city: str
    departure_time: datetime
    arrival_time: datetime
    seats: int
    price: int

class SeatCreate(BaseModel):
    flight_id: int
    seat_number: str
    is_booked: bool