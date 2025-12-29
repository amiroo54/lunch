import sqlite3, os, jdatetime, bcrypt
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
                    if User_count == 0:
                        self._active = True
                        self.role = "archadmin"
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (name, display_name, role, password, active) VALUES (?, ?, ?, ?, ?, ?)",
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
            return Users

    def authenticate(self, password):
        try:
            if not self.password:
                return True
            return bcrypt.checkpw(password.encode("utf8"), self.password)
        except (ValueError, TypeError, bcrypt.error) as e:
            raise RuntimeError(f"Error during authentication: {e}") from e
      

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
