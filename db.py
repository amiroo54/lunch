import sqlite3, os, jdatetime, bcrypt, random
from pathlib import Path

DB_PATH = Path("instance/db.sqlite")
if os.getenv("DB_PATH"):
    DB_PATH = Path(os.getenv("DB_PATH"))

class User:
    def __init__(self, id=-1, name="", display_name="", role="", password=""):
        self.id = id
        self.name = name
        self.display_name = display_name if display_name else name
        self.role = role

        self.set_password(password)

        self._active = False
        self._is_authenticated = False

    def set_password(self, password):
        if password:  # only hash if provided
            salt = bcrypt.gensalt()
            self.password = bcrypt.hashpw(password.encode("utf8"), salt)
            
        else:
            self.password = None


    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self._active

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def get_pass_hash(self):
        try:
            with get_connection() as conn:
                res = conn.execute(
                    "SELECT password FROM users WHERE id=?",
                    [self.id]
                ).fetchone()
                if res:
                    return res["password"]
                else:
                    raise LookupError(f"No user found with id={self.id}")
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error while fetching password: {e}") from e
    
    @staticmethod
    def get_by_id(id):
        try:
            with get_connection() as conn:
                res = conn.execute("SELECT * FROM users WHERE id=?", [id]).fetchone()
                if not res:
                    raise LookupError(f"No user found with id={id}")

                e = User(res["id"], res["name"], res["display_name"], res["role"])
                e.password = res["password"]
                e._active = bool(res["active"])
                return e
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error while fetching user by id: {e}") from e

    @staticmethod
    def get_by_name(name):
        try:
            with get_connection() as conn:
                res = conn.execute("SELECT * FROM users WHERE name=?", [name]).fetchone()
                if not res:
                    raise LookupError(f"No user found with name={name}")

                e = User(res["id"], res["name"], res["display_name"], res["role"])
                e.password = res["password"]
                e._active = bool(res["active"])
                return e
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error while fetching user by name: {e}") from e

    @staticmethod
    def exists(q):
        with get_connection() as conn:
            return bool(conn.execute("SELECT id FROM users WHERE id=? OR name=?", [q, q]).fetchone())

    def save(self):
        try:
            with get_connection() as conn:
                if not User.exists(self.id):
                    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()["COUNT(*)"]
                    if user_count == 0:
                        self._active = True
                        self.role = "archadmin"
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (name, display_name, role, password, active) VALUES (?, ?, ?, ?, ?)",
                        [self.name, self.display_name, self.role, self.password, int(self.is_active)]
                    )
                    self.id = cur.lastrowid
                else:  # Insert
                    raise RuntimeError(f"User {id} already exists")

        except sqlite3.IntegrityError as e:
            raise ValueError(f"Integrity error while saving User: {e}") from e
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error while saving User: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error while saving User: {e}") from e


    def update(self):
        try:
            with get_connection() as conn:
                if User.exists(self.id):
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE users SET name=?, display_name=?, role=?, password=?, active=? WHERE id=?",
                        [self.name, self.display_name, self.role, self.password, self.is_active, self.email, self.id]
                    )
                    self.id = cur.lastrowid
                else: 
                    raise RuntimeError(f"User {id} doesn't exists")

        except sqlite3.IntegrityError as e:
            raise ValueError(f"Integrity error while saving User: {e}") from e
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error while saving User: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error while saving User: {e}") from e

    def activate(self):
        with get_connection() as conn:
            conn.execute("UPDATE users SET active=1 WHERE id=?", [self.id])
            conn.commit()
        self.active = 1

    def deactivate(self):
        with get_connection() as conn:
            conn.execute("UPDATE users SET active=0 WHERE id=?", [self.id])
            conn.commit()
        self.active = 0

    @staticmethod
    def list_all():
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM users").fetchall()
            users = []
            for r in rows:
                e = User(id=r["id"], name=r["name"], display_name=r["display_name"], role=r["role"])
                e.password = r["password"]
                e._active = bool(r["active"])
                users.append(e)
            return users

    def authenticate(self, password):
        try:
            if not self.password:
                return True
            return bcrypt.checkpw(password.encode("utf8"), self.password)
        except (ValueError, TypeError, bcrypt.error) as e:
            raise RuntimeError(f"Error during authentication: {e}") from e


class LunchEvent:
    def __init__(self, id=-1, event_date="", payer_id=None):
        self.id = id
        self.event_date = event_date
        self.payer_id = payer_id

    @staticmethod
    def get_or_create_by_date(event_date):
        with get_connection() as conn:
            res = conn.execute("SELECT * FROM lunch_events WHERE event_date=?", [event_date]).fetchone()
            if res:
                return LunchEvent(res["id"], res["event_date"], res["payer_id"])
            else:
                cur = conn.cursor()
                cur.execute("INSERT INTO lunch_events (event_date) VALUES (?)", [event_date])
                conn.commit()
                return LunchEvent(cur.lastrowid, event_date, None)

    @staticmethod
    def get_by_date(event_date):
        with get_connection() as conn:
            res = conn.execute("""
                SELECT le.*, u.display_name as payer_name
                FROM lunch_events le
                LEFT JOIN Users u ON le.payer_id = u.id
                WHERE le.event_date=?
            """, [event_date]).fetchone()
            if res:
                e = LunchEvent(res["id"], res["event_date"], res["payer_id"])
                e.payer_name = res["payer_name"]
                return e
            return None

    def set_payer(self, user_id):
        with get_connection() as conn:
            conn.execute("UPDATE lunch_events SET payer_id=? WHERE id=?", [user_id, self.id])
            conn.commit()
        self.payer_id = user_id

    def add_attendee(self, user_id):
        with get_connection() as conn:
            try:
                conn.execute("INSERT INTO lunch_attendance (lunch_event_id, user_id) VALUES (?, ?)", [self.id, user_id])
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Already exists

    def remove_attendee(self, user_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM lunch_attendance WHERE lunch_event_id=? AND user_id=?", [self.id, user_id])
            conn.commit()

    def get_attendees(self):
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT u.* FROM Users u
                JOIN lunch_attendance la ON la.user_id = u.id
                WHERE la.lunch_event_id = ?
            """, [self.id]).fetchall()
            users = []
            for r in rows:
                e = User(id=r["id"], name=r["name"], display_name=r["display_name"], role=r["role"])
                e._active = bool(r["active"])
                users.append(e)
            return users

    @staticmethod
    def get_user_stats():
        """Returns dict of user_id -> {'paid': count, 'drank': count}"""
        with get_connection() as conn:
            # Get drink counts (attendance)
            drank_rows = conn.execute("""
                SELECT user_id, COUNT(*) as drank_count
                FROM lunch_attendance
                GROUP BY user_id
            """).fetchall()
            
            # Get paid counts
            paid_rows = conn.execute("""
                SELECT payer_id, COUNT(*) as paid_count
                FROM lunch_events
                WHERE payer_id IS NOT NULL
                GROUP BY payer_id
            """).fetchall()
            
            stats = {}
            for row in drank_rows:
                user_id = row["user_id"]
                stats[user_id] = {'paid': 0, 'drank': row["drank_count"]}
            
            for row in paid_rows:
                user_id = row["payer_id"]
                if user_id in stats:
                    stats[user_id]['paid'] = row["paid_count"]
                else:
                    stats[user_id] = {'paid': row["paid_count"], 'drank': 0}
            
            return stats

    @staticmethod
    def get_next_payer(attendee_ids):
        """
        Returns the user who should pay next based on paid-to-drank ratio.
        Logic: lowest ratio pays next. If tie, random selection.
        Only considers users in attendee_ids.
        """
        if not attendee_ids:
            return None
        
        stats = LunchEvent.get_user_stats()
        
        # Calculate ratios for attendees
        ratios = []
        for user_id in attendee_ids:
            if user_id in stats:
                paid = stats[user_id]['paid']
                drank = stats[user_id]['drank']
            else:
                paid = 0
                drank = 0
            
            # Ratio: paid / drank (avoid division by zero)
            if drank == 0:
                ratio = 0  # Never drank, lowest priority (will be 0)
            else:
                ratio = paid / drank
            
            ratios.append((user_id, ratio))
        
        # Find minimum ratio
        min_ratio = min(r[1] for r in ratios)
        
        # Get all users with minimum ratio
        candidates = [r[0] for r in ratios if r[1] == min_ratio]
        
        # Random selection if tie
        return random.choice(candidates)

    @staticmethod
    def list_recent(limit=10):
        """List recent lunch events"""
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT le.*, u.display_name as payer_name
                FROM lunch_events le
                LEFT JOIN Users u ON le.payer_id = u.id
                ORDER BY le.event_date DESC
                LIMIT ?
            """, [limit]).fetchall()
            events = []
            for r in rows:
                e = LunchEvent(r["id"], r["event_date"], r["payer_id"])
                e.payer_name = r["payer_name"]
                events.append(e)
            return events


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection

def make_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn, open("schema.sql") as sch:
        conn.executescript(sch.read())
        

if not DB_PATH.exists():
    make_db()

if __name__ == "__main__":
    if Path.exists(DB_PATH):
        os.remove(DB_PATH)
    make_db()
    r = User(name="amiroof", display_name="فیروزفر", role="technician", password="username")
    r.save()
    t = User(name="test", role="technician", password="test")
    print(t.password)
    t._active = True
    t.save()
    a = User(name="testAdmin", role="technician", password="admin")
    a._active = True
    a.save()
    a.role = "admin"
    a.update()
    l = User.get_by_id(1)
