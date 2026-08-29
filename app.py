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


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
DATA_DIR = Path(os.getenv("TOUR_DATA_DIR", str(ROOT / "data")))
DATABASE_PATH = DATA_DIR / "database.json"
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
        "consultants": [
            {"id": "con_yasmin", "name": "Yasmin", "active": True},
            {"id": "con_rafael", "name": "Rafael", "active": True},
            {"id": "con_lucas", "name": "Lucas", "active": True},
            {"id": "con_fernanda", "name": "Fernanda", "active": True},
            {"id": "con_juliana", "name": "Juliana", "active": True},
        ],
        "drivers": [
            {"id": "drv_carlos", "name": "Carlos", "active": True, "status": DRIVER_IN_TOUR, "toursStarted": 5, "homePickups": 2, "lastActivity": created},
            {"id": "drv_joao", "name": "João", "active": True, "status": DRIVER_IN_TOUR, "toursStarted": 4, "homePickups": 1, "lastActivity": created},
            {"id": "drv_marcos", "name": "Marcos", "active": True, "status": DRIVER_AVAILABLE, "toursStarted": 3, "homePickups": 0, "lastActivity": created},
            {"id": "drv_pedro", "name": "Pedro", "active": True, "status": DRIVER_HOME, "toursStarted": 2, "homePickups": 1, "lastActivity": created},
            {"id": "drv_ricardo", "name": "Ricardo", "active": True, "status": DRIVER_GALLERY, "toursStarted": 3, "homePickups": 0, "lastActivity": created},
        ],
        "carts": [
            {"id": "cart_01", "name": "Carrinho 01", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "EM_USO"},
            {"id": "cart_02", "name": "Carrinho 02", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "EM_USO"},
            {"id": "cart_03", "name": "Carrinho 03", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "DISPONIVEL"},
            {"id": "cart_04", "name": "Carrinho 04", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "EM_USO"},
            {"id": "cart_05", "name": "Carrinho 05", "capacity": CART_PASSENGER_CAPACITY, "guestCapacity": CART_GUEST_CAPACITY, "status": "EM_USO"},
        ],
        "destinations": [
            {"id": "dest_prestige", "name": "Prestige Praia do Forte", "active": True},
            {"id": "dest_waves", "name": "Prestige Waves Bahia", "active": True},
            {"id": "dest_lobby", "name": "Lobby principal", "active": True},
            {"id": "dest_villas", "name": "Villas", "active": True},
        ],
        "tours": [
            {
                "id": "tour_yasmin", "groupName": "Família de Yasmin", "people": 8, "selfGuide": False, "consultantId": "con_yasmin", "wave": "WAVE_1", "scheduledTime": "09:00",
                "status": STATE_IN_TOUR, "phase": "Golf", "createdAt": created, "updatedAt": created,
                "allocations": [
                    {"driverId": "drv_carlos", "cartId": "cart_01", "seats": 6, "arrived": True},
                    {"driverId": "drv_joao", "cartId": "cart_02", "seats": 2, "arrived": True},
                ],
            },
            {"id": "tour_rafael", "groupName": "Casal de Rafael", "people": 2, "selfGuide": True, "consultantId": "con_rafael", "wave": "WAVE_1", "scheduledTime": "09:00", "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_lucas", "groupName": "Família de Lucas", "people": 5, "selfGuide": False, "consultantId": "con_lucas", "wave": "WAVE_1", "scheduledTime": "09:00", "status": STATE_WAITING_HOME, "phase": "Casa", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_fernanda", "groupName": "Casal de Fernanda", "people": 2, "selfGuide": False, "consultantId": "con_fernanda", "wave": "WAVE_1", "scheduledTime": "09:00", "status": STATE_GALLERY, "phase": "Galeria", "createdAt": created, "updatedAt": created, "allocations": [{"driverId": "drv_ricardo", "cartId": "cart_05", "seats": 2, "arrived": True}]},
            {"id": "tour_juliana", "groupName": "Família de Juliana", "people": 4, "selfGuide": True, "consultantId": "con_juliana", "wave": "WAVE_2", "scheduledTime": "11:00", "status": STATE_PRESENTATION, "phase": "Galeria", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_marcela", "groupName": "Família de Marcela", "people": 6, "selfGuide": False, "consultantId": "con_yasmin", "wave": "WAVE_2", "scheduledTime": "11:00", "status": STATE_WAITING_DESTINATION, "phase": "Galeria", "destinationId": "dest_prestige", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_bruno", "groupName": "Casal de Bruno", "people": 2, "selfGuide": False, "consultantId": "con_rafael", "wave": "WAVE_2", "scheduledTime": "11:00", "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "createdAt": created, "updatedAt": created, "allocations": []},
        ],
        "transfers": [
            {"id": "transfer_adriana", "groupName": "Família de Adriana", "people": 4, "conciergeName": "Marina", "wave": "WAVE_1", "scheduledTime": "07:50", "tourStartTime": "09:00", "status": TRANSFER_SCHEDULED, "origin": "Prestige Waves Bahia", "destination": "Prestige Praia do Forte", "createdAt": created, "updatedAt": created},
            {"id": "transfer_gustavo", "groupName": "Casal de Gustavo", "people": 2, "conciergeName": "André", "wave": "WAVE_2", "scheduledTime": "09:50", "tourStartTime": "11:00", "status": TRANSFER_IN_PROGRESS, "origin": "Prestige Waves Bahia", "destination": "Prestige Praia do Forte", "createdAt": created, "updatedAt": created},
        ],
        "attendance": [],
        "activities": [
            {"id": "act_1", "at": created, "userName": "Sistema", "message": "Painel operacional iniciado", "previous": None, "next": None},
            {"id": "act_2", "at": created, "userName": "Sistema", "message": "Família de Yasmin está no roteiro do tour", "tourId": "tour_yasmin", "previous": STATE_AVAILABLE, "next": STATE_IN_TOUR},
            {"id": "act_3", "at": created, "userName": "Sistema", "message": "Família de Marcela aguarda destino final", "tourId": "tour_marcela", "previous": STATE_PRESENTATION, "next": STATE_WAITING_DESTINATION},
        ],
    }


def load_database() -> dict[str, Any]:
    if not DATABASE_PATH.exists():
        db = initial_database()
        save_database(db)
        return db
    try:
        return json.loads(DATABASE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise APIError("Não foi possível abrir o banco de dados local.", 500) from error


def save_database(db: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DATABASE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATABASE_PATH)


def reset_operational_data(db: dict[str, Any], message: str) -> None:
    """Keep people and system setup, but start a clean operational day."""
    current_time = timestamp()
    db["operationDate"] = operation_date()
    db["tours"] = []
    db["transfers"] = []
    db["attendance"] = []
    for driver in db["drivers"]:
        driver["status"] = DRIVER_AVAILABLE
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


def operational_database() -> dict[str, Any]:
    db = load_database()
    schema_updated = False
    if "attendance" not in db:
        db["attendance"] = []
        schema_updated = True
    for cart in db.get("carts", []):
        if cart.get("capacity") != CART_PASSENGER_CAPACITY or cart.get("guestCapacity") != CART_GUEST_CAPACITY:
            cart["capacity"] = CART_PASSENGER_CAPACITY
            cart["guestCapacity"] = CART_GUEST_CAPACITY
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
    if user["role"] not in {ROLE_ADMIN, ROLE_DRIVER, ROLE_CONCIERGE}:
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


def attendance_for(db: dict[str, Any], user_id: str) -> dict[str, Any] | None:
    return next((item for item in db.setdefault("attendance", []) if item.get("userId") == user_id and item.get("operationDate") == operation_date()), None)


def driver_has_checked_in(db: dict[str, Any], driver_id: str) -> bool:
    linked_accounts = [item for item in db["users"] if item.get("driverId") == driver_id and item.get("active", True) and item["role"] == ROLE_DRIVER]
    return not linked_accounts or any(attendance_for(db, account["id"]) for account in linked_accounts)


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
    require_operational(user)
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


def confirm_quantity_tour_start(tour: dict[str, Any]) -> None:
    """A quantity-only tour needs only driver assignments to start."""
    tour.update({"requiresDetails": False, "updatedAt": timestamp()})


def create_tour_slots(db: dict[str, Any], user: dict[str, Any], quantity: Any, wave: Any, self_guide_quantity: Any = 0) -> list[dict[str, Any]]:
    """Register tour quantities; drivers complete guest data at dispatch time."""
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 0
    if not 1 <= quantity <= 30:
        raise APIError("Informe uma quantidade de tours entre 1 e 30.")
    try:
        self_guide_quantity = int(self_guide_quantity)
    except (TypeError, ValueError):
        self_guide_quantity = -1
    if not 0 <= self_guide_quantity <= quantity:
        raise APIError("A quantidade de tours Self Guide deve estar entre zero e a quantidade total de tours.")
    if wave not in TRANSFER_SCHEDULES:
        raise APIError("Selecione a 1ª ou a 2ª onda do tour.")
    created_at = timestamp()
    existing = sum(1 for item in db["tours"] if item.get("requiresDetails"))
    tours = []
    for offset in range(quantity):
        number = existing + offset + 1
        tour = {"id": new_id("tour"), "groupName": f"Tour {number} aguardando motorista", "people": 0, "selfGuide": offset < self_guide_quantity, "consultantId": None, "wave": wave, "scheduledTime": TRANSFER_SCHEDULES[wave]["tourTime"], "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "requiresDetails": True, "registeredBy": user["role"], "createdAt": created_at, "updatedAt": created_at, "allocations": []}
        db["tours"].insert(0, tour)
        tours.append(tour)
    log_activity(db, user, None, None, STATE_AVAILABLE, f"{quantity} tour{'s' if quantity > 1 else ''} registrado{'s' if quantity > 1 else ''} para a {TRANSFER_SCHEDULES[wave]['label']}, incluindo {self_guide_quantity} Self Guide.")
    return tours


def apply_action(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any], action: str, payload: dict[str, Any]) -> None:
    require_operational(user)
    allocations = lambda: tour.get("allocations", [])

    if action == "start":
        if tour["status"] != STATE_AVAILABLE:
            raise APIError("Apenas grupos disponíveis podem iniciar tour.")
        if tour.get("requiresDetails"):
            confirm_quantity_tour_start(tour)
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"))
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR, tours=True)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["phase"] = "Prestige Waves Bahia"
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} iniciou tour no Prestige.")
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
            log_activity(db, user, tour, STATE_IN_TOUR, STATE_IN_TOUR, f"{find(db['drivers'], driver_id, 'Motorista')['name']} registrou: {'deixou o grupo na Casa' if decision == 'DEIXOU_NA_CASA' else 'aguardou na Casa'} ({recorded}/{len(allocations())} motoristas).")
            return
        if any(item.get("homeDecision") == "AGUARDOU_NA_CASA" for item in allocations()):
            change_tour_state(db, user, tour, STATE_HOME, f"{tour['groupName']} está na Casa; os motoristas registraram suas situações.")
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
        change_tour_state(db, user, tour, STATE_WAITING_HOME, f"{tour['groupName']} ficou aguardando transporte na Casa.")
        return

    if action == "pickup-home":
        if tour["status"] != STATE_WAITING_HOME:
            raise APIError("O grupo não está aguardando na Casa.")
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"))
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR, home_pickup=True)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["phase"] = "Casa → Galeria"
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} foi buscado na Casa para seguir à Galeria.")
        return

    if action == "deliver-gallery":
        if tour["status"] not in {STATE_IN_TOUR, STATE_HOME}:
            raise APIError("O grupo precisa estar em deslocamento para ser entregue na Galeria.")
        for allocation in allocations():
            # The group remains in the Gallery, but its driver and cart immediately return to the available pool.
            update_driver(db, allocation["driverId"], DRIVER_AVAILABLE)
            update_cart(db, allocation["cartId"], "DISPONIVEL")
        tour["allocations"] = []
        tour["phase"] = "Galeria"
        change_tour_state(db, user, tour, STATE_GALLERY, f"{tour['groupName']} foi entregue na Galeria; motorista liberado para retornar ao Prestige.")
        return

    if action == "presentation-started":
        if tour["status"] != STATE_GALLERY:
            raise APIError("O grupo precisa estar na Galeria.")
        change_tour_state(db, user, tour, STATE_PRESENTATION, f"Apresentação iniciada para {tour['groupName']}.")
        return

    if action == "presentation-finished":
        if tour["status"] not in {STATE_GALLERY, STATE_PRESENTATION}:
            raise APIError("A apresentação ainda não está em andamento.")
        destination_id = payload.get("destinationId")
        if not destination_id:
            raise APIError("Informe o destino final.")
        find(db["destinations"], destination_id, "Destino")
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_AVAILABLE)
            update_cart(db, allocation["cartId"], "DISPONIVEL")
        tour["allocations"] = []
        tour["destinationId"] = destination_id
        tour["phase"] = "Galeria"
        change_tour_state(db, user, tour, STATE_WAITING_DESTINATION, f"{tour['groupName']} concluiu a apresentação e aguarda destino.")
        return

    if action == "assign-destination":
        if tour["status"] != STATE_WAITING_DESTINATION:
            raise APIError("O grupo não está aguardando destino.")
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"))
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_DESTINATION)
            update_cart(db, allocation["cartId"], "EM_USO")
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


@app.get("/api/bootstrap")
def bootstrap():
    with DB_LOCK:
        db = operational_database()
        user = get_current_user(db)
        data = safe_database(db)
        if user["role"] == ROLE_CONCIERGE:
            # Concierges receive only their own invitations; they cannot inspect the operation.
            data = {"operationDate": db["operationDate"], "transfers": [item for item in db.get("transfers", []) if item.get("conciergeUserId") == user["id"]]}
        return jsonify(
            user=clean_user(user),
            data=data,
            states={"DISPONIVEL": STATE_AVAILABLE, "EM_TOUR": STATE_IN_TOUR, "NA_CASA": STATE_HOME, "AGUARDANDO_CASA": STATE_WAITING_HOME, "NA_GALERIA": STATE_GALLERY, "EM_APRESENTACAO": STATE_PRESENTATION, "AGUARDANDO_DESTINO": STATE_WAITING_DESTINATION, "EM_DESTINO_FINAL": STATE_FINAL_DESTINATION, "CONCLUIDO": STATE_COMPLETE},
            driverStates={"DISPONIVEL": DRIVER_AVAILABLE, "EM_TOUR": DRIVER_IN_TOUR, "CASA": DRIVER_HOME, "GALERIA": DRIVER_GALLERY, "DESTINO_FINAL": DRIVER_DESTINATION, "FOLGA": DRIVER_LEAVE, "ATESTADO": DRIVER_MEDICAL},
            attendance=attendance_for(db, user["id"]),
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
        target.update({"name": name, "username": username, "role": role, "active": active})
        if driver_id:
            target["driverId"] = driver_id
        else:
            target.pop("driverId", None)
        if role in {ROLE_DRIVER, ROLE_HOSTESS}:
            target["checkInLocation"] = str(payload.get("checkInLocation", target.get("checkInLocation", ""))).strip() or "Prestige Praia do Forte"
        else:
            target.pop("checkInLocation", None)
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
        require_operational(user)
        if "quantity" in payload:
            tours = create_tour_slots(db, user, payload.get("quantity"), payload.get("wave", "WAVE_1"), payload.get("selfGuideQuantity", 0))
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
        tours = create_tour_slots(db, user, payload.get("quantity"), payload.get("wave", "WAVE_1"), payload.get("selfGuideQuantity", 0))
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
        if existing:
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
        driver = {"id": new_id("drv"), "name": name, "active": bool(payload.get("active", True)), "status": status, "toursStarted": 0, "homePickups": 0, "lastActivity": timestamp()}
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


@app.get("/<path:path>")
def spa(path: str):
    # Let the single-page interface own its client-side URLs.
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "4174")), debug=True)
