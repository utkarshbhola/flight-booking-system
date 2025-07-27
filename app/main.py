from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base
from schemas import UserCreate, FlightCreate, SeatCreate
import psycopg2
from psycopg2.extras import RealDictCursor
import traceback

# --- Initialize App and DB ---
app = FastAPI()

try:
    conn = psycopg2.connect(
        dbname="flight_booking_system",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432",
        cursor_factory=RealDictCursor
    )
    cursor = conn.cursor()
    print("✅ Database connection established successfully!")
except Exception as e:
    print(f"❌ Error connecting to the database: {e}")


# -------------------------------
# 📁 USERS
# -------------------------------
@app.get("/users")
def read_users():
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return {"users": users}

@app.post("/users")
def create_user(user: UserCreate):
    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING id",
        (user.name, user.email, user.password)
    )
    user_id = cursor.fetchone()['id']
    conn.commit()
    return {"user_id": user_id}


# -------------------------------
# ✈️ FLIGHTS
# -------------------------------
@app.get("/flights")
def get_flights():
    cursor.execute("SELECT * FROM flights")
    flights = cursor.fetchall()
    return {"flights": flights}

@app.post("/flights")
def create_flight(flight: FlightCreate):
    try:
        cursor.execute(
            """
            INSERT INTO flights (id, flight_number, departure_city, arrival_city,
                                 departure_time, arrival_time, seats, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                flight.id,
                flight.flight_number,
                flight.departure_city,
                flight.arrival_city,
                flight.departure_time,
                flight.arrival_time,
                flight.seats,
                flight.price
            )
        )
        flight_id = cursor.fetchone()["id"]
        conn.commit()
        return {"flight_id": flight_id}

    except Exception as e:
        conn.rollback()
        print("Database error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Database insertion failed")


# -------------------------------
# 💺 SEATS
# -------------------------------

@app.put("/seats/book")
def book_seat(seat: SeatCreate):
    try:
        cursor.execute(
            """
            UPDATE seats
            SET is_booked = %s
            WHERE flight_id = %s AND seat_number = %s
            RETURNING id
            """,
            (seat.is_booked, seat.flight_id, seat.seat_number)
        )
        updated_seat = cursor.fetchone()
        if not updated_seat:
            raise HTTPException(status_code=404, detail="Seat not found")

        conn.commit()
        return {
            "message": f"Seat {seat.seat_number} on flight {seat.flight_id} booking updated to {seat.is_booked}"
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/seats/{flight_id}")
def get_seats(flight_id: int):
    cursor.execute("SELECT * FROM seats WHERE flight_id = %s", (flight_id,))
    seats = cursor.fetchall()
    return {"seats": seats}


@app.post("/seats/{flight_id}")
def create_seats_for_flight(flight_id: int):
    try:
        seats = []
        rows = 30
        cols = ['A', 'B', 'C', 'D', 'E', 'F']

        for row in range(1, rows + 1):
            for col in cols:
                seat_number = f"{row}{col}"
                seats.append((flight_id, seat_number, False))

        for seat in seats:
            cursor.execute(
                "INSERT INTO seats (flight_id, seat_number, is_booked) VALUES (%s, %s, %s)",
                seat
            )

        conn.commit()
        return {"message": f"{len(seats)} seats created for flight {flight_id}"}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
