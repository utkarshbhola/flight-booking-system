from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User, Flight, Seat, Booking
from schemas import UserCreate, FlightCreate, SeatCreate, UserLogin, BookingCreate
import traceback
import util
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from kafka_producer import send_kafka_message
# --- Initialize App and DB ---
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create the database tables
Base.metadata.create_all(bind=engine)


# -------------------------------
# 🏠 Home
# -------------------------------
@app.get("/")
def read_root():
    return {"message": "Welcome to the Flight Booking System API!"}


# -------------------------------
# 📁 USERS
# -------------------------------
@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"users": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}


@app.post("/login")
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not util.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"message": "Login successful", "user_id": user.id, "name": user.name}


@app.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = util.hash_password(user.password)
    user.password = hashed_password
    db_user = User(name=user.name, email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"user_id": db_user.id, "name": db_user.name, "email": db_user.email}


@app.get("/users/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}


# -------------------------------
# ✈️ FLIGHTS
# -------------------------------
@app.get("/flights")
def get_flights(db: Session = Depends(get_db)):
    flights = db.query(Flight).all()
    return {
        "flights": [
            {
                "id": f.id,
                "flight_number": f.flight_number,
                "departure_city": f.departure_city,
                "arrival_city": f.arrival_city,
                "departure_time": f.departure_time,
                "arrival_time": f.arrival_time,
                "total_seats": f.total_seats,
                "price": f.price,
            }
            for f in flights
        ]
    }


@app.post("/flights")
def create_flight(flight: FlightCreate, db: Session = Depends(get_db)):
    try:
        db_flight = Flight(
            id=flight.id,
            flight_number=flight.flight_number,
            departure_city=flight.departure_city,
            arrival_city=flight.arrival_city,
            departure_time=flight.departure_time,
            arrival_time=flight.arrival_time,
            total_seats=flight.total_seats,
            price=flight.price,
        )
        db.add(db_flight)
        db.commit()
        db.refresh(db_flight)
        return {"flight_id": db_flight.id}
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Database insertion failed")


@app.delete("/flights/{flight_id}")
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # also delete seats + bookings manually
    db.query(Booking).filter(Booking.flight_id == flight_id).delete()
    db.query(Seat).filter(Seat.flight_id == flight_id).delete()
    db.delete(flight)
    db.commit()

    return {"message": f"Flight {flight_id} deleted"}


# -------------------------------
# 💺 SEATS
# -------------------------------
@app.put("/seats/book")
def book_seat(seat: SeatCreate, db: Session = Depends(get_db)):
    db_seat = db.query(Seat).filter(
        Seat.flight_id == seat.flight_id, Seat.seat_number == seat.seat_number
    ).first()
    if not db_seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    db_seat.is_booked = seat.is_booked
    db.commit()
    return {
        "message": f"Seat {seat.seat_number} on flight {seat.flight_id} booking updated",
        "seat": {"id": db_seat.id, "seat_number": db_seat.seat_number, "is_booked": db_seat.is_booked},
    }


@app.get("/seats/{flight_id}")
def get_seats(flight_id: int, db: Session = Depends(get_db)):
    seats = db.query(Seat).filter(Seat.flight_id == flight_id).all()
    return {"seats": [{"id": s.id, "seat_number": s.seat_number, "is_booked": s.is_booked} for s in seats]}


@app.post("/seats/{flight_id}")
def create_seats_for_flight(flight_id: int, db: Session = Depends(get_db)):
    existing_seats = db.query(Seat).filter(Seat.flight_id == flight_id).count()
    if existing_seats > 0:
        return {"message": "Seats already created for this flight"}

    seats = []
    rows = 30
    cols = ["A", "B", "C", "D", "E", "F"]

    for row in range(1, rows + 1):
        for col in cols:
            seat_number = f"{row}{col}"
            seat = Seat(flight_id=flight_id, seat_number=seat_number, is_booked=False)
            seats.append(seat)

    db.bulk_save_objects(seats)
    db.commit()
    return {"message": f"{len(seats)} seats created for flight {flight_id}"}


# -------------------------------
# 🛫 BOOKINGS
# -------------------------------
@app.post("/bookings")
async def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(
        Seat.id == booking.seat_id, Seat.flight_id == booking.flight_id
    ).first()

    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    if seat.is_booked:
        raise HTTPException(status_code=400, detail="Seat already booked")

    seat.is_booked = True
    db.commit()

    new_booking = Booking(
        flight_id=booking.flight_id, seat_id=booking.seat_id, user_id=booking.user_id
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    # --- 🔥 Publish Kafka Event ---
    await send_kafka_message("bookings", {
        "event": "booking_created",
        "booking_id": new_booking.id,
        "flight_id": new_booking.flight_id,
        "seat_id": new_booking.seat_id,
        "user_id": new_booking.user_id,
    })

    return {
        "message": "Booking successful",
        "booking": {
            "id": new_booking.id,
            "flight_id": new_booking.flight_id,
            "seat_id": new_booking.seat_id,
            "user_id": new_booking.user_id,
        },
    }


@app.get("/bookings/{user_id}")
def get_user_bookings(user_id: int, db: Session = Depends(get_db)):
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    return {
        "bookings": [
            {
                "id": b.id,
                "flight_id": b.flight_id,
                "seat_id": b.seat_id,
                "user_id": b.user_id,
            }
            for b in bookings
        ]
    }
