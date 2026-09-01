"""Iberostar Tour Interno - Flask application ready for Render."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # Allows local JSON-only development before dependencies are installed.
    psycopg = None
    Jsonb = None


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
DATA_DIR = Path(os.getenv("TOUR_DATA_DIR", str(ROOT / "data")))
DATABASE_PATH = DATA_DIR / "database.json"
POSTGRES_URL = os.getenv("DATABASE_URL", "").strip()
POSTGRES_STATE_KEY = "primary"
DB_LOCK = threading.RLock()
SESSIONS: dict[str, dict[str, Any]] = {}

ROLE_ADMIN = "ADMIN"
ROLE_DRIVER = "MOTORISTA"
ROLE_HOSTESS = "HOSTESS"
ROLE_CONCIERGE = "CONCIERGE"
ROLES = {ROLE_ADMIN, ROLE_DRIVER, ROLE_HOSTESS, ROLE_CONCIERGE}

STATE_AVAILABLE = "DISPONIVEL"
STATE_IN_TOUR = "EM_TOUR"
STATE_HOME = "NA_CASA"
STATE_WAITING_HOME = "AGUARDANDO_CASA"
STATE_GALLERY = "NA_GALERIA"
STATE_PRESENTATION = "EM_APRESENTACAO"
STATE_WAITING_DESTINATION = "AGUARDANDO_DESTINO"
STATE_FINAL_DESTINATION = "EM_DESTINO_FINAL"
STATE_COMPLETE = "CONCLUIDO"

DRIVER_AVAILABLE = "DISPONIVEL"
DRIVER_IN_TOUR = "EM_TOUR"
DRIVER_HOME = "CASA"
DRIVER_GALLERY = "GALERIA"
DRIVER_DESTINATION = "DESTINO_FINAL"
DRIVER_LEAVE = "FOLGA"
DRIVER_MEDICAL = "ATESTADO"
DRIVER_STATUSES = {DRIVER_AVAILABLE, DRIVER_IN_TOUR, DRIVER_HOME, DRIVER_GALLERY, DRIVER_DESTINATION, DRIVER_LEAVE, DRIVER_MEDICAL}
CART_PASSENGER_CAPACITY = 5  # Passenger seats; the driver is not counted here.
CART_GUEST_CAPACITY = 4  # One passenger seat is reserved for the consultant.

TRANSFER_SCHEDULES = {
    "WAVE_1": {"label": "1ª onda", "tourTime": "09:00", "transferTime": "07:50"},
    "WAVE_2": {"label": "2ª onda", "tourTime": "11:00", "transferTime": "09:50"},
}
TRANSFER_SCHEDULED = "AGENDADO"
TRANSFER_IN_PROGRESS = "EM_DESLOCAMENTO"
TRANSFER_ARRIVED = "CHEGOU_PRESTIGE"
TRANSFER_WITHDRAWN = "DESISTENCIA"
OPERATION_TZ = ZoneInfo("America/Sao_Paulo")
FINAL_DESTINATIONS = [
    {"id": "dest_lobby_bahia", "name": "Lobby Bahia", "active": True},
    {"id": "dest_lobby_selection", "name": "Lobby Selection", "active": True},
    {"id": "dest_prestige", "name": "Prestige Praia", "active": True},
    {"id": "dest_prestige_selection", "name": "Prestige Selection", "active": True},
]

# IDs used only by the first prototype screen.  They are kept here so that a
# one-time migration can remove them from an existing database without ever
# touching records created by the team.
DEMO_CONSULTANT_IDS = {"con_yasmin", "con_rafael", "con_lucas", "con_fernanda", "con_juliana"}
DEMO_DRIVER_IDS = {"drv_carlos", "drv_joao", "drv_marcos", "drv_pedro", "drv_ricardo"}
DEMO_TOUR_IDS = {"tour_yasmin", "tour_rafael", "tour_lucas", "tour_fernanda", "tour_juliana", "tour_marcela", "tour_bruno"}
DEMO_TRANSFER_IDS = {"transfer_adriana", "transfer_gustavo"}
DEMO_ACTIVITY_IDS = {"act_1", "act_2", "act_3"}
DEMO_CART_IDS = {"cart_01", "cart_02", "cart_03", "cart_04", "cart_05"}

# This is a one-way scrypt hash. The initial password is never stored in source code.
INITIAL_ADMIN_HASH = (
    "c75658f843ab803ffbeeee35e0af7299:"
    "4d6dd57c1f333e36a98469f931d3ef728178f675b2a3d80e9f750675ab71afc"
    "976731e7a49d8b55e705e1d118631d62a9c16d49403b6c5fb0e2c2d2b04a24f5c"
)


class APIError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def operation_date() -> str:
    """Operational day in Praia do Forte's timezone, regardless of the Render region."""
    return datetime.now(OPERATION_TZ).date().isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def initial_database() -> dict[str, Any]:
    created = timestamp()
    return {
        "operationDate": operation_date(),
        "users": [{
            "id": "user_admin",
            "username": "adson.gonzalez",
            "name": "Administrador",
            "role": ROLE_ADMIN,
            "active": True,
            "passwordHash": INITIAL_ADMIN_HASH,
            "createdAt": created,
        }],
        "consultants": [],
        "drivers": [],
        "carts": [
            {"id": "cart_01", "name": "Carrinho 01", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "DISPONIVEL"},
            {"id": "cart_02", "name": "Carrinho 02", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "DISPONIVEL"},
            {"id": "cart_03", "name": "Carrinho 03", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "DISPONIVEL"},
            {"id": "cart_04", "name": "Carrinho 04", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "DISPONIVEL"},
            {"id": "cart_05", "name": "Carrinho 05", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "DISPONIVEL"},
        ],
        "destinations": [dict(item) for item in FINAL_DESTINATIONS],
        "tours": [],
        "transfers": [],
        "attendance": [],
        "activities": [
            {"id": new_id("act"), "at": created, "userName": "Sistema", "message": "Painel operacional iniciado sem dados de exemplo.", "previous": None, "next": None},
        ],
    }


def load_local_database() -> dict[str, Any] | None:
    if not DATABASE_PATH.exists():
        return None
    try:
        return json.loads(DATABASE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise APIError("Não foi possível abrir o banco de dados local.", 500) from error


def save_local_database(db: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DATABASE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATABASE_PATH)


def postgres_connection():
    if psycopg is None or Jsonb is None:
        raise APIError("O driver PostgreSQL não está instalado no servidor.", 500)
    try:
        return psycopg.connect(POSTGRES_URL, connect_timeout=10)
    except Exception as error:
        raise APIError("Não foi possível conectar ao banco PostgreSQL. Verifique a variável DATABASE_URL.", 503) from error


def ensure_postgres_schema(connection: Any) -> None:
    """Create the persistent state tables once, without storing credentials in code."""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS tour_control_state (
            state_key TEXT PRIMARY KEY,
            payload JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS tour_control_schema (
            schema_version INTEGER PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("INSERT INTO tour_control_schema (schema_version) VALUES (1) ON CONFLICT DO NOTHING")


def save_postgres_database(db: dict[str, Any], connection: Any | None = None) -> None:
    owns_connection = connection is None
    active_connection = connection or postgres_connection()
    try:
        with active_connection:
            ensure_postgres_schema(active_connection)
            active_connection.execute("""
                INSERT INTO tour_control_state (state_key, payload, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (state_key) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
            """, (POSTGRES_STATE_KEY, Jsonb(db)))
    finally:
        if owns_connection:
            active_connection.close()


def load_database() -> dict[str, Any]:
    if not POSTGRES_URL:
        db = load_local_database()
        if db is not None:
            return db
        db = initial_database()
        save_local_database(db)
        return db

    connection = postgres_connection()
    try:
        with connection:
            ensure_postgres_schema(connection)
            row = connection.execute("SELECT payload FROM tour_control_state WHERE state_key = %s", (POSTGRES_STATE_KEY,)).fetchone()
            if row:
                payload = row[0]
                return json.loads(payload) if isinstance(payload, str) else payload
            db = load_local_database() or initial_database()
            connection.execute("INSERT INTO tour_control_state (state_key, payload) VALUES (%s, %s)", (POSTGRES_STATE_KEY, Jsonb(db)))
            return db
    finally:
        connection.close()


def save_database(db: dict[str, Any]) -> None:
    if POSTGRES_URL:
        save_postgres_database(db)
        return
    save_local_database(db)


def reset_operational_data(db: dict[str, Any], message: str) -> None:
    """Keep people and system setup, but start a clean operational day."""
    current_time = timestamp()
    db["operationDate"] = operation_date()
    db["tours"] = []
    db["transfers"] = []
    db["attendance"] = []
    for driver in db["drivers"]:
        # A new day starts with everyone off duty. A driver becomes available
        # only after using their own account to check in for that day.
        driver["status"] = DRIVER_LEAVE
        driver["toursStarted"] = 0
        driver["homePickups"] = 0
        driver["lastActivity"] = current_time
    for cart in db["carts"]:
        cart["status"] = "DISPONIVEL"
    db["activities"] = [{"id": new_id("act"), "at": current_time, "userName": "Sistema", "message": message, "previous": None, "next": None}]


def ensure_operational_day(db: dict[str, Any]) -> bool:
    """Reset on the first access of a new business day in Brazil's timezone."""
    if db.get("operationDate") == operation_date():
        return False
    reset_operational_data(db, f"Operação iniciada para {operation_date()}.")
    return True


def remove_demo_data(db: dict[str, Any]) -> bool:
    """Remove only records that belonged to the old visual demonstration.

    Real records use generated IDs, so this migration is deliberately keyed by
    the fixed prototype IDs instead of names or roles.
    """
    changed = False
    collection_rules = (
        ("consultants", DEMO_CONSULTANT_IDS),
        ("drivers", DEMO_DRIVER_IDS),
        ("tours", DEMO_TOUR_IDS),
        ("transfers", DEMO_TRANSFER_IDS),
    )
    for field, demo_ids in collection_rules:
        original = db.get(field, [])
        cleaned = [item for item in original if item.get("id") not in demo_ids]
        if len(cleaned) != len(original):
            db[field] = cleaned
            changed = True

    original_activities = db.get("activities", [])
    cleaned_activities = [
        activity for activity in original_activities
        if activity.get("id") not in DEMO_ACTIVITY_IDS
        and activity.get("tourId") not in DEMO_TOUR_IDS
        and activity.get("transferId") not in DEMO_TRANSFER_IDS
    ]
    if len(cleaned_activities) != len(original_activities):
        db["activities"] = cleaned_activities
        changed = True

    active_cart_ids = {
        allocation.get("cartId")
        for tour in db.get("tours", [])
        if tour.get("status") not in {STATE_COMPLETE, STATE_FINAL_DESTINATION}
        for allocation in tour.get("allocations", [])
        if allocation.get("cartId")
    }
    for cart in db.get("carts", []):
        if cart.get("id") in DEMO_CART_IDS and cart.get("id") not in active_cart_ids and cart.get("status") != "DISPONIVEL":
            cart["status"] = "DISPONIVEL"
            changed = True
    return changed


def operational_database() -> dict[str, Any]:
    db = load_database()
    schema_updated = remove_demo_data(db)
    if "attendance" not in db:
        db["attendance"] = []
        schema_updated = True
    for cart in db.get("carts", []):
        if cart.get("capacity") != CART_PASSENGER_CAPACITY or cart.get("guestCapacity") != CART_GUEST_CAPACITY:
            cart["capacity"] = CART_PASSENGER_CAPACITY
            cart["guestCapacity"] = CART_GUEST_CAPACITY
            schema_updated = True
    if db.get("destinations") != FINAL_DESTINATIONS:
        db["destinations"] = [dict(item) for item in FINAL_DESTINATIONS]
        schema_updated = True
    for account in db.get("users", []):
        if account.get("role") != ROLE_DRIVER or account.get("driverId"):
            continue
        has_checked_in = any(item.get("userId") == account["id"] and item.get("operationDate") == operation_date() for item in db.get("attendance", []))
        create_linked_driver(db, account, DRIVER_AVAILABLE if has_checked_in else DRIVER_LEAVE)
        schema_updated = True
    for tour in db.get("tours", []):
        # Preserve active groups created before the old support-at-home option was removed.
        for allocation in tour.get("allocations", []):
            if allocation.get("homeDecision") == "APOIO_NA_CASA":
                allocation["homeDecision"] = "AGUARDOU_NA_CASA"
                schema_updated = True
        if tour.get("status") not in {STATE_GALLERY, STATE_PRESENTATION}:
            continue
        for allocation in tour.get("allocations", []):
            driver = next((item for item in db["drivers"] if item["id"] == allocation.get("driverId")), None)
            cart = next((item for item in db["carts"] if item["id"] == allocation.get("cartId")), None)
            if driver:
                driver["status"] = DRIVER_AVAILABLE
                driver["lastActivity"] = timestamp()
            if cart:
                cart["status"] = "DISPONIVEL"
        tour["allocations"] = []
        tour["status"] = STATE_WAITING_DESTINATION
        tour["phase"] = "Galeria"
        tour["updatedAt"] = timestamp()
        schema_updated = True
    if enforce_driver_checkin(db):
        schema_updated = True
    if ensure_operational_day(db) or schema_updated:
        save_database(db)
    return db


def clean_user(user: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in user.items() if key != "passwordHash"}


def safe_database(db: dict[str, Any]) -> dict[str, Any]:
    result = dict(db)
    result["users"] = [clean_user(user) for user in db["users"]]
    return result


def verify_legacy_scrypt(password: str, stored: str) -> bool:
    """Validate the first administrator's Node scrypt hash during migration."""
    try:
        salt, expected = stored.split(":", 1)
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64).hex()
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def password_matches(password: str, stored: str) -> bool:
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, password)
    return verify_legacy_scrypt(password, stored)


def find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    result = next((item for item in items if item["id"] == item_id), None)
    if not result:
        raise APIError(f"{label} não encontrado.", 404)
    return result


def require_operational(user: dict[str, Any]) -> None:
    if user["role"] not in {ROLE_ADMIN, ROLE_DRIVER}:
        raise APIError("Seu perfil é somente de consulta.", 403)


def require_transfer_access(user: dict[str, Any]) -> None:
    if user["role"] not in {ROLE_ADMIN, ROLE_CONCIERGE}:
        raise APIError("Seu perfil não possui acesso aos convites Waves.", 403)


def require_admin(user: dict[str, Any]) -> None:
    if user["role"] != ROLE_ADMIN:
        raise APIError("Apenas administradores podem realizar esta ação.", 403)


def get_current_user(db: dict[str, Any]) -> dict[str, Any]:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    session = SESSIONS.get(token)
    if not session or session["expiresAt"] < datetime.now(timezone.utc):
        SESSIONS.pop(token, None)
        raise APIError("Sessão inválida ou expirada.", 401)
    user = next((item for item in db["users"] if item["id"] == session["userId"] and item["active"]), None)
    if not user:
        raise APIError("Usuário sem acesso.", 401)
    return user


def log_activity(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any] | None, previous: str | None, next_state: str | None, message: str, transfer: dict[str, Any] | None = None) -> None:
    activity = {"id": new_id("act"), "at": timestamp(), "userName": user["name"], "tourId": tour["id"] if tour else None, "transferId": transfer["id"] if transfer else None, "message": message, "previous": previous, "next": next_state}
    db["activities"].insert(0, activity)
    del db["activities"][250:]


def update_driver(db: dict[str, Any], driver_id: str, status: str, tours: bool = False, home_pickup: bool = False) -> None:
    driver = find(db["drivers"], driver_id, "Motorista")
    driver["status"] = status
    if tours:
        driver["toursStarted"] += 1
    if home_pickup:
        driver["homePickups"] += 1
    driver["lastActivity"] = timestamp()


def create_linked_driver(db: dict[str, Any], user: dict[str, Any], status: str = DRIVER_LEAVE, active: bool | None = None) -> dict[str, Any]:
    """Create the operational driver record required by a driver account."""
    driver = {
        "id": new_id("drv"),
        "name": user["name"],
        "active": user.get("active", True) if active is None else active,
        "status": status,
        "toursStarted": 0,
        "homePickups": 0,
        "lastActivity": timestamp(),
    }
    db["drivers"].append(driver)
    user["driverId"] = driver["id"]
    return driver


def active_driver_assignment(db: dict[str, Any], driver_id: str) -> dict[str, Any] | None:
    """Return a tour currently relying on a driver, if there is one."""
    for tour in db.get("tours", []):
        if tour.get("status") == STATE_COMPLETE:
            continue
        if any(item.get("driverId") == driver_id for item in tour.get("allocations", [])):
            return tour
    return None


def validate_driver_link(db: dict[str, Any], driver_id: Any, user_id: str | None = None) -> str | None:
    if not driver_id:
        return None
    driver_id = str(driver_id)
    find(db["drivers"], driver_id, "Motorista")
    if any(item.get("driverId") == driver_id and item["id"] != user_id for item in db["users"]):
        raise APIError("Esse motorista já está vinculado a outro usuário.", 409)
    return driver_id


def remove_driver_for_role_change(db: dict[str, Any], driver_id: str, user_id: str) -> None:
    """Remove the operational record when its account stops being a driver."""
    assigned_tour = active_driver_assignment(db, driver_id)
    if assigned_tour:
        raise APIError(f"O motorista está vinculado ao tour de {assigned_tour['groupName']}. Libere o transporte antes de mudar o perfil.", 409)
    if any(item.get("id") != user_id and item.get("role") == ROLE_DRIVER and item.get("driverId") == driver_id for item in db["users"]):
        return
    db["drivers"] = [item for item in db["drivers"] if item["id"] != driver_id]


def attendance_for(db: dict[str, Any], user_id: str) -> dict[str, Any] | None:
    return next((item for item in db.setdefault("attendance", []) if item.get("userId") == user_id and item.get("operationDate") == operation_date()), None)


def driver_has_checked_in(db: dict[str, Any], driver_id: str) -> bool:
    linked_accounts = [item for item in db["users"] if item.get("driverId") == driver_id and item.get("active", True) and item["role"] == ROLE_DRIVER]
    return bool(linked_accounts) and any(attendance_for(db, account["id"]) for account in linked_accounts)


def enforce_driver_checkin(db: dict[str, Any]) -> bool:
    """Never expose a driver as available before today's check-in."""
    changed = False
    for driver in db.get("drivers", []):
        if driver.get("status") != DRIVER_AVAILABLE or active_driver_assignment(db, driver["id"]):
            continue
        if not driver.get("active", True) or not driver_has_checked_in(db, driver["id"]):
            driver["status"] = DRIVER_LEAVE
            driver["lastActivity"] = timestamp()
            changed = True
    return changed


def update_cart(db: dict[str, Any], cart_id: str, status: str) -> None:
    find(db["carts"], cart_id, "Carrinho")["status"] = status


def change_tour_state(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any], next_state: str, message: str) -> None:
    previous = tour["status"]
    tour["status"] = next_state
    tour["updatedAt"] = timestamp()
    log_activity(db, user, tour, previous, next_state, message)


def change_transfer_state(db: dict[str, Any], user: dict[str, Any], transfer: dict[str, Any], next_state: str, message: str) -> None:
    previous = transfer["status"]
    transfer["status"] = next_state
    transfer["updatedAt"] = timestamp()
    log_activity(db, user, None, previous, next_state, message, transfer=transfer)


def apply_transfer_action(db: dict[str, Any], user: dict[str, Any], transfer: dict[str, Any], action: str) -> None:
    if action == "withdraw":
        if user["role"] == ROLE_CONCIERGE:
            if transfer.get("conciergeUserId") != user["id"]:
                raise APIError("Você pode registrar desistência apenas nos seus próprios convites.", 403)
        elif user["role"] != ROLE_ADMIN:
            raise APIError("Somente o concierge responsável ou um administrador registra desistências.", 403)
        if transfer["status"] != TRANSFER_SCHEDULED:
            raise APIError("A desistência só pode ser registrada antes do início do traslado.")
        change_transfer_state(db, user, transfer, TRANSFER_WITHDRAWN, f"{transfer['groupName']} registrou desistência do convite Waves.")
        return
    require_admin(user)
    if action == "start":
        if transfer["status"] != TRANSFER_SCHEDULED:
            raise APIError("Apenas convites agendados podem iniciar o traslado.")
        change_transfer_state(db, user, transfer, TRANSFER_IN_PROGRESS, f"Traslado de {transfer['groupName']} saiu do Waves Bahia.")
        return
    if action == "arrive":
        if transfer["status"] != TRANSFER_IN_PROGRESS:
            raise APIError("O traslado precisa estar em deslocamento para confirmar a chegada.")
        change_transfer_state(db, user, transfer, TRANSFER_ARRIVED, f"{transfer['groupName']} chegou ao Praia do Forte para a {TRANSFER_SCHEDULES[transfer['wave']]['label']}.")
        return
    raise APIError("Ação de traslado não encontrada.", 404)


def normalized_allocations(db: dict[str, Any], raw_allocations: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_allocations, list) or not raw_allocations:
        raise APIError("Selecione pelo menos um motorista.")
    drivers: set[str] = set()
    carts: set[str] = set()
    allocations: list[dict[str, Any]] = []
    for allocation in raw_allocations:
        driver_id = allocation.get("driverId")
        if not driver_id:
            raise APIError("Informe o motorista de cada carrinho.")
        if driver_id in drivers:
            raise APIError("Não repita motorista na mesma saída.")
        drivers.add(driver_id)
        driver = find(db["drivers"], driver_id, "Motorista")
        if not driver.get("active", True) or driver["status"] != DRIVER_AVAILABLE:
            raise APIError(f"{driver['name']} não está disponível.")
        if not driver_has_checked_in(db, driver_id):
            raise APIError(f"{driver['name']} ainda não fez check-in hoje.")
        requested_cart_id = allocation.get("cartId")
        if requested_cart_id:
            cart = find(db["carts"], requested_cart_id, "Carrinho")
        else:
            cart = next((item for item in db["carts"] if item["id"] not in carts and item.get("status") == "DISPONIVEL"), None)
            if not cart:
                raise APIError("Não há carrinho disponível para este motorista.")
        if cart["id"] in carts:
            raise APIError("Não repita carrinho na mesma saída.")
        carts.add(cart["id"])
        if cart["status"] != "DISPONIVEL":
            raise APIError(f"{cart['name']} não está disponível.")
        allocations.append({"driverId": driver_id, "cartId": cart["id"], "seats": 0, "guestSeats": 0, "arrived": False})
    return allocations


def confirm_quantity_tour_start(tour: dict[str, Any], consultant_name: str) -> None:
    """Save the consultant paired with the driver for a quantity-only tour."""
    label = tour.get("slotLabel") or str(tour.get("groupName", "Tour")).removesuffix(" aguardando motorista")
    tour.update({
        "groupName": label,
        "slotLabel": label,
        "consultantName": consultant_name,
        "requiresDetails": False,
        "updatedAt": timestamp(),
    })


def create_tour_slots(db: dict[str, Any], user: dict[str, Any], quantity: Any, wave: Any, self_gean_quantity: Any = 0) -> list[dict[str, Any]]:
    """Register normal tours and Self Gean tours as separate operational slots."""
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = -1
    try:
        self_gean_quantity = int(self_gean_quantity)
    except (TypeError, ValueError):
        self_gean_quantity = -1
    total_quantity = quantity + self_gean_quantity
    if quantity < 0 or self_gean_quantity < 0 or not 1 <= total_quantity <= 30:
        raise APIError("Informe as quantidades de tours e Self Gean. O total deve ficar entre 1 e 30.")
    if wave not in TRANSFER_SCHEDULES:
        raise APIError("Selecione a 1ª ou a 2ª onda do tour.")
    created_at = timestamp()
    existing = sum(1 for item in db["tours"] if item.get("requiresDetails"))
    tours = []
    for offset in range(total_quantity):
        number = existing + offset + 1
        is_self_gean = offset >= quantity
        label = f"Self Gean {offset - quantity + 1}" if is_self_gean else f"Tour {number}"
        tour = {"id": new_id("tour"), "groupName": label, "slotLabel": label, "people": 0, "selfGuide": is_self_gean, "consultantId": None, "wave": wave, "scheduledTime": TRANSFER_SCHEDULES[wave]["tourTime"], "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "requiresDetails": True, "registeredBy": user["role"], "createdAt": created_at, "updatedAt": created_at, "allocations": []}
        db["tours"].insert(0, tour)
        tours.append(tour)
    log_activity(db, user, None, None, STATE_AVAILABLE, f"{quantity} tour{'s' if quantity != 1 else ''} e {self_gean_quantity} Self Gean registrado{'s' if total_quantity != 1 else ''} para a {TRANSFER_SCHEDULES[wave]['label']}.")
    return tours


def apply_action(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any], action: str, payload: dict[str, Any]) -> None:
    require_operational(user)
    allocations = lambda: tour.get("allocations", [])

    if action == "start":
        if tour["status"] != STATE_AVAILABLE:
            raise APIError("Apenas grupos disponíveis podem iniciar tour.")
        if tour.get("requiresDetails"):
            consultant_name = str(payload.get("consultantName", "")).strip()
            if not consultant_name:
                raise APIError("Informe o nome do consultor que está saindo no tour.")
            confirm_quantity_tour_start(tour, consultant_name)
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"))
        tour["requiredCartCount"] = len(tour["allocations"])
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR, tours=True)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["phase"] = "Prestige Waves Bahia"
        drivers_in_tour = ", ".join(find(db["drivers"], allocation["driverId"], "Motorista")["name"] for allocation in allocations())
        consultant_name = tour.get("consultantName") or next((item["name"] for item in db["consultants"] if item["id"] == tour.get("consultantId")), "Consultor não informado")
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} iniciou: {consultant_name} com {drivers_in_tour}.")
        return

    if action == "arrived-home":
        if tour["status"] != STATE_IN_TOUR:
            raise APIError("O grupo precisa estar em tour para chegar à Casa.")
        driver_id = payload.get("driverId")
        allocation = next((item for item in allocations() if item["driverId"] == driver_id), None)
        if not allocation:
            raise APIError("Selecione um motorista vinculado a este grupo.")
        if allocation.get("homeDecision"):
            raise APIError("Este motorista já registrou sua situação na Casa.")
        decision = payload.get("homeDecision")
        if decision not in {"DEIXOU_NA_CASA", "AGUARDOU_NA_CASA"}:
            raise APIError("Informe se o motorista deixou o grupo ou permaneceu na Casa.")
        allocation["homeDecision"] = decision
        allocation["arrivedAtHome"] = timestamp()
        allocation["arrived"] = True
        if decision == "DEIXOU_NA_CASA":
            update_driver(db, driver_id, DRIVER_AVAILABLE)
            update_cart(db, allocation["cartId"], "DISPONIVEL")
        else:
            update_driver(db, driver_id, DRIVER_HOME)
        tour["phase"] = "Casa"
        recorded = sum(1 for item in allocations() if item.get("homeDecision"))
        if recorded < len(allocations()):
            tour["updatedAt"] = timestamp()
            decision_label = {"DEIXOU_NA_CASA": "deixou o grupo na Casa", "AGUARDOU_NA_CASA": "permaneceu na Casa"}[decision]
            log_activity(db, user, tour, STATE_IN_TOUR, STATE_IN_TOUR, f"{find(db['drivers'], driver_id, 'Motorista')['name']} registrou: {decision_label} ({recorded}/{len(allocations())} motoristas).")
            return
        staying_driver_names = [find(db["drivers"], item["driverId"], "Motorista")["name"] for item in allocations() if item.get("homeDecision") == "AGUARDOU_NA_CASA"]
        returned_driver_names = [find(db["drivers"], item["driverId"], "Motorista")["name"] for item in allocations() if item.get("homeDecision") == "DEIXOU_NA_CASA"]
        if staying_driver_names:
            change_tour_state(db, user, tour, STATE_HOME, f"{tour['groupName']} está na Casa. Permaneceu com o casal: {', '.join(staying_driver_names)}. Retornou ao Prestige: {', '.join(returned_driver_names) or 'ninguém'}.")
        else:
            change_tour_state(db, user, tour, STATE_WAITING_HOME, f"{tour['groupName']} ficou aguardando transporte na Casa; todos os motoristas retornaram ao Prestige.")
        return

    if action == "return-prestige":
        if tour["status"] != STATE_HOME:
            raise APIError("A ação é válida somente para grupos na Casa.")
        for allocation in allocations():
            if allocation.get("homeDecision") != "DEIXOU_NA_CASA":
                update_driver(db, allocation["driverId"], DRIVER_AVAILABLE)
                update_cart(db, allocation["cartId"], "DISPONIVEL")
        tour["allocations"] = []
        tour["phase"] = "Casa"
        change_tour_state(db, user, tour, STATE_WAITING_HOME, f"{tour['groupName']} ficou aguardando novos motoristas na Casa; a equipe anterior foi liberada para outra família.")
        return

    if action == "pickup-home":
        if tour["status"] != STATE_WAITING_HOME:
            raise APIError("O grupo não está aguardando na Casa.")
        pickup_allocations = normalized_allocations(db, payload.get("allocations"))
        required_carts = tour.get("requiredCartCount", len(pickup_allocations))
        if len(pickup_allocations) != required_carts:
            raise APIError(f"Este grupo precisa de {required_carts} carrinho{'s' if required_carts != 1 else ''}. Selecione {required_carts} motorista{'s' if required_carts != 1 else ''} para a busca na Casa.")
        tour["allocations"] = pickup_allocations
        tour["requiredCartCount"] = required_carts
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR, home_pickup=True)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["phase"] = "Casa → Galeria"
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} foi buscado na Casa para seguir à Galeria.")
        return

    if action == "depart-home":
        if tour["status"] != STATE_HOME:
            raise APIError("O grupo precisa estar na Casa.")
        required_carts = tour.get("requiredCartCount", len(allocations()))
        staying_allocations = [item for item in allocations() if item.get("homeDecision") == "AGUARDOU_NA_CASA"]
        if len(staying_allocations) != required_carts:
            raise APIError("Este grupo precisa de todos os carrinhos que saíram juntos. Chame outro motorista para ir à Casa antes de seguir para a Galeria.")
        for allocation in staying_allocations:
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR)
        tour["allocations"] = staying_allocations
        tour["phase"] = "Casa → Galeria"
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} saiu da Casa para a Galeria com todos os carrinhos necessários.")
        return

    if action == "join-home":
        if tour["status"] != STATE_HOME:
            raise APIError("O grupo precisa estar na Casa.")
        required_carts = tour.get("requiredCartCount", len(allocations()))
        staying_allocations = [item for item in allocations() if item.get("homeDecision") == "AGUARDOU_NA_CASA"]
        missing_drivers = required_carts - len(staying_allocations)
        if missing_drivers <= 0:
            raise APIError("Os motoristas necessários já estão na Casa. Registre a saída para a Galeria.")
        incoming_allocations = normalized_allocations(db, payload.get("allocations"))
        if len(incoming_allocations) != missing_drivers:
            raise APIError(f"Este grupo precisa de exatamente {missing_drivers} motorista{'s' if missing_drivers > 1 else ''} adicional{'is' if missing_drivers > 1 else ''} para seguir à Galeria.")
        for allocation in staying_allocations:
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR)
        for allocation in incoming_allocations:
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR, home_pickup=True)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["allocations"] = staying_allocations + incoming_allocations
        tour["phase"] = "Casa → Galeria"
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} recebeu o motorista necessário na Casa e saiu para a Galeria com {required_carts} carrinhos.")
        return

    if action == "deliver-gallery":
        if tour["status"] != STATE_IN_TOUR:
            raise APIError("O grupo precisa estar em deslocamento para ser entregue na Galeria.")
        for allocation in allocations():
            # The group remains in the Gallery, but its driver and cart immediately return to the available pool.
            update_driver(db, allocation["driverId"], DRIVER_AVAILABLE)
            update_cart(db, allocation["cartId"], "DISPONIVEL")
        tour["allocations"] = []
        tour["phase"] = "Galeria"
        change_tour_state(db, user, tour, STATE_WAITING_DESTINATION, f"{tour['groupName']} chegou à Galeria e aguarda destino final; motorista liberado para retornar ao Prestige.")
        return

    if action == "assign-destination":
        if tour["status"] != STATE_WAITING_DESTINATION:
            raise APIError("O grupo não está aguardando destino.")
        destination_id = payload.get("destinationId")
        if not destination_id:
            raise APIError("Selecione o destino final.")
        find(db["destinations"], destination_id, "Destino")
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"))
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_DESTINATION)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["destinationId"] = destination_id
        tour["phase"] = "Destino final"
        change_tour_state(db, user, tour, STATE_FINAL_DESTINATION, f"{tour['groupName']} saiu para o destino final.")
        return

    if action == "complete-destination":
        if tour["status"] != STATE_FINAL_DESTINATION:
            raise APIError("O grupo ainda não está em destino final.")
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_AVAILABLE)
            update_cart(db, allocation["cartId"], "DISPONIVEL")
        tour["phase"] = "Concluído"
        change_tour_state(db, user, tour, STATE_COMPLETE, f"{tour['groupName']} concluiu o destino final.")
        return

    raise APIError("Ação operacional não encontrada.", 404)


app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@app.errorhandler(APIError)
def handle_api_error(error: APIError):
    return jsonify(error=error.message), error.status


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    if request.path.startswith("/api/"):
        return jsonify(error=error.description), error.code
    return error


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))
    with DB_LOCK:
        db = operational_database()
        user = next((item for item in db["users"] if item["username"].lower() == username and item["active"]), None)
        if not user or not password_matches(password, user["passwordHash"]):
            raise APIError("Usuário ou senha inválidos.", 401)
        # Convert the old seeded hash to Werkzeug's Python-native format after its first valid use.
        if not user["passwordHash"].startswith(("scrypt:", "pbkdf2:")):
            user["passwordHash"] = generate_password_hash(password)
            save_database(db)
        token = secrets.token_urlsafe(48)
        SESSIONS[token] = {"userId": user["id"], "expiresAt": datetime.now(timezone.utc) + timedelta(hours=12)}
        return jsonify(token=token, user=clean_user(user))


@app.post("/api/auth/logout")
def logout():
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    SESSIONS.pop(token, None)
    return jsonify(ok=True)


@app.get("/api/auth/me")
def auth_me():
    with DB_LOCK:
        return jsonify(user=clean_user(get_current_user(operational_database())))


@app.get("/api/public/driver-status")
def public_driver_status():
    """Read-only driver board intended for the consultants' shared screen."""
    with DB_LOCK:
        db = operational_database()
        drivers = [
            {
                "name": driver["name"],
                "status": driver.get("status", DRIVER_LEAVE),
                "active": bool(driver.get("active", True)),
                "lastActivity": driver.get("lastActivity"),
            }
            for driver in db.get("drivers", [])
            if driver.get("active", True)
        ]
        return jsonify(operationDate=db["operationDate"], drivers=drivers)


@app.get("/api/bootstrap")
def bootstrap():
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        current_attendance = attendance_for(db, user["id"])
        data = safe_database(db)
        if user["role"] == ROLE_CONCIERGE:
            # Concierges receive only their own invitations; they cannot inspect the operation.
            data = {"operationDate": db["operationDate"], "transfers": [item for item in db.get("transfers", []) if item.get("conciergeUserId") == user["id"]]}
        elif user["role"] == ROLE_HOSTESS:
            # Hostesses see the General Panel but never operational controls.
            data = {
                "operationDate": db["operationDate"],
                "attendance": [current_attendance] if current_attendance else [],
                "tours": [
                    {"id": item["id"], "selfGuide": bool(item.get("selfGuide")), "status": item["status"], "requiresDetails": bool(item.get("requiresDetails"))}
                    for item in db.get("tours", [])
                ],
                "drivers": [
                    {"id": item["id"], "name": item["name"], "status": item["status"], "active": bool(item.get("active", True)), "toursStarted": item.get("toursStarted", 0), "homePickups": item.get("homePickups", 0), "lastActivity": item.get("lastActivity")}
                    for item in db.get("drivers", [])
                    if item.get("active", True)
                ],
            }
        elif user["role"] == ROLE_DRIVER:
            # Drivers receive the operational dashboard, without users or management data.
            data = {
                "operationDate": db["operationDate"],
                "attendance": [current_attendance] if current_attendance else [],
                "tours": db.get("tours", []),
                "drivers": db.get("drivers", []),
                "consultants": db.get("consultants", []),
                "destinations": db.get("destinations", []),
                "transfers": db.get("transfers", []),
                "activities": db.get("activities", []),
            }
        return jsonify(
            user=clean_user(user),
            data=data,
            states={"DISPONIVEL": STATE_AVAILABLE, "EM_TOUR": STATE_IN_TOUR, "NA_CASA": STATE_HOME, "AGUARDANDO_CASA": STATE_WAITING_HOME, "NA_GALERIA": STATE_GALLERY, "EM_APRESENTACAO": STATE_PRESENTATION, "AGUARDANDO_DESTINO": STATE_WAITING_DESTINATION, "EM_DESTINO_FINAL": STATE_FINAL_DESTINATION, "CONCLUIDO": STATE_COMPLETE},
            driverStates={"DISPONIVEL": DRIVER_AVAILABLE, "EM_TOUR": DRIVER_IN_TOUR, "CASA": DRIVER_HOME, "GALERIA": DRIVER_GALLERY, "DESTINO_FINAL": DRIVER_DESTINATION, "FOLGA": DRIVER_LEAVE, "ATESTADO": DRIVER_MEDICAL},
            attendance=current_attendance,
            waves=TRANSFER_SCHEDULES,
            transferStates={"AGENDADO": TRANSFER_SCHEDULED, "EM_DESLOCAMENTO": TRANSFER_IN_PROGRESS, "CHEGOU_PRESTIGE": TRANSFER_ARRIVED, "DESISTENCIA": TRANSFER_WITHDRAWN},
        )


@app.post("/api/users")
def create_user():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        username = str(payload.get("username", "")).strip().lower()
        name = str(payload.get("name", "")).strip()
        password = str(payload.get("password", ""))
        role = payload.get("role")
        if not username or not name or len(password) < 8 or role not in ROLES:
            raise APIError("Preencha nome, usuário, senha de ao menos 8 caracteres e perfil.")
        if any(item["username"] == username for item in db["users"]):
            raise APIError("Esse usuário já existe.", 409)
        driver_id = validate_driver_link(db, payload.get("driverId")) if role == ROLE_DRIVER else None
        new_user = {"id": new_id("user"), "username": username, "name": name, "role": role, "active": True, "passwordHash": generate_password_hash(password), "createdAt": timestamp()}
        if driver_id:
            new_user["driverId"] = driver_id
        if role in {ROLE_DRIVER, ROLE_HOSTESS}:
            new_user["checkInLocation"] = str(payload.get("checkInLocation", "")).strip() or "Prestige Praia do Forte"
        db["users"].append(new_user)
        if role == ROLE_DRIVER and not driver_id:
            create_linked_driver(db, new_user)
        log_activity(db, user, None, None, None, f"Usuário {name} criado com perfil {role}.")
        save_database(db)
        return jsonify(user=clean_user(new_user)), 201


@app.put("/api/users/<user_id>")
def update_user(user_id: str):
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        current_user = get_current_user(db)
        require_admin(current_user)
        target = find(db["users"], user_id, "Usuário")
        previous_role = target["role"]
        previous_driver_id = target.get("driverId")
        name = str(payload.get("name", target["name"])).strip()
        username = str(payload.get("username", target["username"])).strip().lower()
        role = payload.get("role", target["role"])
        active = bool(payload["active"]) if "active" in payload else target.get("active", True)
        password = str(payload.get("password", ""))
        if not name or not username or role not in ROLES:
            raise APIError("Preencha nome, usuário e perfil corretamente.")
        if any(item["username"].lower() == username and item["id"] != target["id"] for item in db["users"]):
            raise APIError("Esse usuário já existe.", 409)
        if password and len(password) < 8:
            raise APIError("A nova senha deve ter ao menos 8 caracteres.")
        if target["id"] == current_user["id"] and (role != ROLE_ADMIN or not active):
            raise APIError("O administrador conectado não pode remover o próprio acesso.")
        active_admins_after = sum(1 for item in db["users"] if item["id"] != target["id"] and item["role"] == ROLE_ADMIN and item.get("active", True))
        if role == ROLE_ADMIN and active:
            active_admins_after += 1
        if active_admins_after < 1:
            raise APIError("Mantenha ao menos um administrador ativo no sistema.")
        driver_id = payload.get("driverId", target.get("driverId")) if role == ROLE_DRIVER else None
        driver_id = validate_driver_link(db, driver_id, target["id"])
        if previous_role == ROLE_DRIVER and role != ROLE_DRIVER and previous_driver_id:
            remove_driver_for_role_change(db, previous_driver_id, target["id"])
        target.update({"name": name, "username": username, "role": role, "active": active})
        if role == ROLE_DRIVER and not driver_id:
            driver_id = create_linked_driver(db, target, active=active)["id"]
        if driver_id:
            target["driverId"] = driver_id
        else:
            target.pop("driverId", None)
        if role in {ROLE_DRIVER, ROLE_HOSTESS}:
            target["checkInLocation"] = str(payload.get("checkInLocation", target.get("checkInLocation", ""))).strip() or "Prestige Praia do Forte"
        else:
            target.pop("checkInLocation", None)
        if previous_role == ROLE_DRIVER and role != ROLE_DRIVER:
            db["attendance"] = [item for item in db.setdefault("attendance", []) if item.get("userId") != target["id"]]
        if password:
            target["passwordHash"] = generate_password_hash(password)
        log_activity(db, current_user, None, None, None, f"Usuário {name} atualizado.")
        save_database(db)
        return jsonify(user=clean_user(target))


@app.post("/api/tours")
def create_tour():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        if "quantity" in payload:
            tours = create_tour_slots(db, user, payload.get("quantity"), payload.get("wave", "WAVE_1"), payload.get("selfGeanQuantity", payload.get("selfGuideQuantity", 0)))
            save_database(db)
            return jsonify(tours=tours), 201
        group_name = str(payload.get("groupName", "")).strip()
        try:
            people = int(payload.get("people", 0))
        except (ValueError, TypeError):
            people = 0
        if not group_name or not 1 <= people <= 48:
            raise APIError("Informe o grupo e uma quantidade de pessoas entre 1 e 48.")
        find(db["consultants"], payload.get("consultantId"), "Consultor")
        wave = payload.get("wave", "WAVE_1")
        if wave not in TRANSFER_SCHEDULES:
            raise APIError("Selecione a 1ª ou a 2ª onda do tour.")
        tour = {"id": new_id("tour"), "groupName": group_name, "people": people, "selfGuide": bool(payload.get("selfGuide")), "consultantId": payload["consultantId"], "wave": wave, "scheduledTime": TRANSFER_SCHEDULES[wave]["tourTime"], "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "createdAt": timestamp(), "updatedAt": timestamp(), "allocations": []}
        db["tours"].insert(0, tour)
        log_activity(db, user, tour, None, STATE_AVAILABLE, f"{group_name} cadastrado como disponível no Prestige.")
        save_database(db)
        return jsonify(tour=tour), 201


@app.post("/api/tours/hostess")
def register_hostess_tours():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        if user["role"] != ROLE_HOSTESS:
            raise APIError("Somente o perfil Hostess registra a quantidade de tours.", 403)
        tours = create_tour_slots(db, user, payload.get("quantity"), payload.get("wave", "WAVE_1"), payload.get("selfGeanQuantity", payload.get("selfGuideQuantity", 0)))
        save_database(db)
        return jsonify(tours=tours), 201


@app.delete("/api/users/<user_id>")
def delete_user(user_id: str):
    with DB_LOCK:
        db = operational_database()
        current_user = get_current_user(db)
        require_admin(current_user)
        target = find(db["users"], user_id, "Usuário")
        if target["id"] == current_user["id"]:
            raise APIError("O administrador conectado não pode excluir a própria conta.")
        if target["role"] == ROLE_ADMIN and sum(1 for item in db["users"] if item["role"] == ROLE_ADMIN and item["active"]) <= 1:
            raise APIError("Mantenha ao menos um administrador ativo no sistema.")
        db["users"] = [item for item in db["users"] if item["id"] != target["id"]]
        log_activity(db, current_user, None, None, None, f"Usuário {target['name']} excluído.")
        for token, session in list(SESSIONS.items()):
            if session["userId"] == target["id"]:
                SESSIONS.pop(token, None)
        db["attendance"] = [item for item in db.setdefault("attendance", []) if item.get("userId") != target["id"]]
        save_database(db)
        return jsonify(ok=True)


@app.post("/api/attendance/check-in")
def check_in():
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        if user["role"] not in {ROLE_DRIVER, ROLE_HOSTESS}:
            raise APIError("O check-in é destinado a motoristas e hostess.", 403)
        existing = attendance_for(db, user["id"])
        created_driver = None
        if user["role"] == ROLE_DRIVER and not user.get("driverId"):
            created_driver = create_linked_driver(db, user, DRIVER_AVAILABLE if existing else DRIVER_LEAVE)
        if existing:
            if created_driver:
                save_database(db)
            return jsonify(attendance=existing, alreadyCheckedIn=True)
        location = user.get("checkInLocation") or "Prestige Praia do Forte"
        record = {"id": new_id("checkin"), "userId": user["id"], "userName": user["name"], "role": user["role"], "location": location, "status": "TRABALHANDO", "operationDate": operation_date(), "checkInAt": timestamp()}
        driver_id = user.get("driverId")
        if user["role"] == ROLE_DRIVER and driver_id:
            driver = find(db["drivers"], driver_id, "Motorista")
            if not driver.get("active", True):
                raise APIError("O cadastro deste motorista está inativo. Procure o administrador.", 409)
            if not active_driver_assignment(db, driver_id):
                update_driver(db, driver_id, DRIVER_AVAILABLE)
        db.setdefault("attendance", []).append(record)
        log_activity(db, user, None, None, None, f"{user['name']} realizou check-in e está trabalhando.")
        save_database(db)
        return jsonify(attendance=record), 201


@app.post("/api/drivers")
def create_driver():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        name = str(payload.get("name", "")).strip()
        status = payload.get("status", DRIVER_AVAILABLE)
        if not name or status not in DRIVER_STATUSES:
            raise APIError("Informe o nome e uma disponibilidade válida.")
        # A registered driver still needs a linked account and today's check-in
        # before becoming operationally available.
        initial_status = DRIVER_LEAVE if status == DRIVER_AVAILABLE else status
        driver = {"id": new_id("drv"), "name": name, "active": bool(payload.get("active", True)), "status": initial_status, "toursStarted": 0, "homePickups": 0, "lastActivity": timestamp()}
        db["drivers"].append(driver)
        log_activity(db, user, None, None, None, f"Motorista {name} cadastrado.")
        save_database(db)
        return jsonify(driver=driver), 201


@app.put("/api/drivers/<driver_id>")
def update_driver_record(driver_id: str):
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        driver = find(db["drivers"], driver_id, "Motorista")
        name = str(payload.get("name", driver["name"])).strip()
        status = payload.get("status", driver["status"])
        active = bool(payload["active"]) if "active" in payload else driver.get("active", True)
        if not name or status not in DRIVER_STATUSES:
            raise APIError("Informe o nome e uma disponibilidade válida.")
        assigned_tour = active_driver_assignment(db, driver_id)
        if assigned_tour and (status != driver["status"] or active != driver.get("active", True)):
            raise APIError(f"{driver['name']} está vinculado ao tour de {assigned_tour['groupName']}. Finalize ou libere o transporte antes de mudar sua disponibilidade.", 409)
        if status == DRIVER_AVAILABLE and not driver_has_checked_in(db, driver_id):
            status = DRIVER_LEAVE
        driver.update({"name": name, "active": active, "status": status, "lastActivity": timestamp()})
        log_activity(db, user, None, None, None, f"Motorista {name} atualizado para {status}.")
        save_database(db)
        return jsonify(driver=driver)


@app.delete("/api/drivers/<driver_id>")
def delete_driver(driver_id: str):
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        driver = find(db["drivers"], driver_id, "Motorista")
        assigned_tour = active_driver_assignment(db, driver_id)
        if assigned_tour:
            raise APIError(f"{driver['name']} está vinculado ao tour de {assigned_tour['groupName']}. Libere-o antes de excluir.", 409)
        db["drivers"] = [item for item in db["drivers"] if item["id"] != driver_id]
        for account in db["users"]:
            if account.get("driverId") == driver_id:
                account.pop("driverId", None)
        log_activity(db, user, None, None, None, f"Motorista {driver['name']} excluído.")
        save_database(db)
        return jsonify(ok=True)


@app.post("/api/consultants")
def create_consultant():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        name = str(payload.get("name", "")).strip()
        if not name:
            raise APIError("Informe o nome do consultor.")
        consultant = {"id": new_id("con"), "name": name, "active": bool(payload.get("active", True))}
        db["consultants"].append(consultant)
        log_activity(db, user, None, None, None, f"Consultor {name} cadastrado.")
        save_database(db)
        return jsonify(consultant=consultant), 201


@app.put("/api/consultants/<consultant_id>")
def update_consultant(consultant_id: str):
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        consultant = find(db["consultants"], consultant_id, "Consultor")
        name = str(payload.get("name", consultant["name"])).strip()
        if not name:
            raise APIError("Informe o nome do consultor.")
        consultant.update({"name": name, "active": bool(payload["active"]) if "active" in payload else consultant.get("active", True)})
        log_activity(db, user, None, None, None, f"Consultor {name} atualizado.")
        save_database(db)
        return jsonify(consultant=consultant)


@app.delete("/api/consultants/<consultant_id>")
def delete_consultant(consultant_id: str):
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        consultant = find(db["consultants"], consultant_id, "Consultor")
        db["consultants"] = [item for item in db["consultants"] if item["id"] != consultant_id]
        log_activity(db, user, None, None, None, f"Consultor {consultant['name']} excluído.")
        save_database(db)
        return jsonify(ok=True)


@app.post("/api/tours/<tour_id>/action")
def tour_action(tour_id: str):
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        tour = find(db["tours"], tour_id, "Tour")
        apply_action(db, user, tour, payload.get("action", ""), payload)
        save_database(db)
        return jsonify(tour=tour)


@app.post("/api/transfers")
def create_transfer():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_transfer_access(user)
        group_name = str(payload.get("groupName", "")).strip()
        concierge_name = user["name"] if user["role"] == ROLE_CONCIERGE else str(payload.get("conciergeName", "")).strip()
        try:
            people = int(payload.get("people", 0))
        except (ValueError, TypeError):
            people = 0
        wave = payload.get("wave", "")
        if not group_name or not concierge_name or not 1 <= people <= 48 or wave not in TRANSFER_SCHEDULES:
            raise APIError("Preencha grupo, pessoas, concierge e onda do convite.")
        schedule = TRANSFER_SCHEDULES[wave]
        transfer = {"id": new_id("transfer"), "groupName": group_name, "people": people, "conciergeName": concierge_name, "conciergeUserId": user["id"] if user["role"] == ROLE_CONCIERGE else None, "wave": wave, "scheduledTime": schedule["transferTime"], "tourStartTime": schedule["tourTime"], "status": TRANSFER_SCHEDULED, "origin": "Prestige Waves Bahia", "destination": "Prestige Praia do Forte", "createdAt": timestamp(), "updatedAt": timestamp()}
        db.setdefault("transfers", []).insert(0, transfer)
        log_activity(db, user, None, None, TRANSFER_SCHEDULED, f"Convite de {group_name} agendado no Waves Bahia para {schedule['transferTime']}.", transfer=transfer)
        save_database(db)
        return jsonify(transfer=transfer), 201


@app.post("/api/transfers/<transfer_id>/action")
def transfer_action(transfer_id: str):
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        transfer = find(db.setdefault("transfers", []), transfer_id, "Convite")
        apply_transfer_action(db, user, transfer, payload.get("action", ""))
        save_database(db)
        return jsonify(transfer=transfer)


@app.post("/api/operation/reset")
def reset_operation():
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        require_admin(user)
        reset_operational_data(db, f"Operação zerada manualmente por {user['name']}.")
        save_database(db)
        return jsonify(ok=True, operationDate=db["operationDate"])


@app.get("/")
def root():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(STATIC_DIR / "assets", filename)


@app.get("/service-worker.js")
def service_worker():
    return send_from_directory(STATIC_DIR, "service-worker.js", mimetype="application/javascript")


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.webmanifest", mimetype="application/manifest+json")


@app.get("/<path:path>")
def spa(path: str):
    # Let the single-page interface own its client-side URLs.
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "4174")), debug=True)
