from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User, Flight, Seat
from schemas import UserCreate, FlightCreate, SeatCreate, UserLogin
import traceback
import util
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext
from fastapi import APIRouter, status


# --- Initialize App and DB ---
app = FastAPI()

# Dependency
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create the database tables
Base.metadata.create_all(bind=engine)

#home page
@app.get("/")
def read_root():
    return {"message": "Welcome to the Flight Booking System API!"}


# -------------------------------
# 📁 USERS
# -------------------------------
@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"users": users}
router = APIRouter(tags=["Authentication"])

@app.post("/login")
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    print("Email received:", user_credentials.email)
    print("Password received:", user_credentials.password)

    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not util.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"message": "Login successful"}


@app.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    
    # Hash the password - user password should be hashed before storing
    hashed_password = util.hash_password(user.password)
    user.password = hashed_password
    
    db_user = User(name=user.name, email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"user_id": db_user.id}

@app.get("/users/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}

# -------------------------------
# ✈️ FLIGHTS
# -------------------------------
@app.get("/flights")
def get_flights(db: Session = Depends(get_db)):
    flights = db.query(Flight).all()
    return {"flights": flights}

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
            price=flight.price
        )
        db.add(db_flight)
        db.commit()
        db.refresh(db_flight)
        return {"flight_id": db_flight.id}
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Database insertion failed", headers={"X-Error": str(e)})

# -------------------------------
# 💺 SEATS
# -------------------------------
@app.put("/seats/book")
def book_seat(seat: SeatCreate, db: Session = Depends(get_db)):
    db_seat = db.query(Seat).filter(Seat.flight_id == seat.flight_id, Seat.seat_number == seat.seat_number).first()
    if not db_seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    db_seat.is_booked = seat.is_booked
    db.commit()
    return {"message": f"Seat {seat.seat_number} on flight {seat.flight_id} booking updated to {seat.is_booked}"}

@app.get("/seats/{flight_id}")
def get_seats(flight_id: int, db: Session = Depends(get_db)):
    seats = db.query(Seat).filter(Seat.flight_id == flight_id).all()
    return {"seats": seats}

@app.post("/seats/{flight_id}")
def create_seats_for_flight(flight_id: int, db: Session = Depends(get_db)):
    try:
        seats = []
        rows = 30
        cols = ['A', 'B', 'C', 'D', 'E', 'F']

        for row in range(1, rows + 1):
            for col in cols:
                seat_number = f"{row}{col}"
                seat = Seat(flight_id=flight_id, seat_number=seat_number, is_booked=False)
                seats.append(seat)

        db.bulk_save_objects(seats)
        db.commit()
        return {"message": f"{len(seats)} seats created for flight {flight_id}"}
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
