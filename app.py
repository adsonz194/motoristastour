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
ROLES = {ROLE_ADMIN, ROLE_DRIVER, ROLE_HOSTESS}

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


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def initial_database() -> dict[str, Any]:
    created = timestamp()
    return {
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
            {"id": "cart_01", "name": "Carrinho 01", "capacity": 6, "status": "EM_USO"},
            {"id": "cart_02", "name": "Carrinho 02", "capacity": 6, "status": "EM_USO"},
            {"id": "cart_03", "name": "Carrinho 03", "capacity": 6, "status": "DISPONIVEL"},
            {"id": "cart_04", "name": "Carrinho 04", "capacity": 6, "status": "EM_USO"},
            {"id": "cart_05", "name": "Carrinho 05", "capacity": 6, "status": "EM_USO"},
        ],
        "destinations": [
            {"id": "dest_prestige", "name": "Prestige Praia do Forte", "active": True},
            {"id": "dest_waves", "name": "Prestige Waves Bahia", "active": True},
            {"id": "dest_lobby", "name": "Lobby principal", "active": True},
            {"id": "dest_villas", "name": "Villas", "active": True},
        ],
        "tours": [
            {
                "id": "tour_yasmin", "groupName": "Família de Yasmin", "people": 8, "selfGuide": False, "consultantId": "con_yasmin",
                "status": STATE_IN_TOUR, "phase": "Golf", "createdAt": created, "updatedAt": created,
                "allocations": [
                    {"driverId": "drv_carlos", "cartId": "cart_01", "seats": 6, "arrived": True},
                    {"driverId": "drv_joao", "cartId": "cart_02", "seats": 2, "arrived": True},
                ],
            },
            {"id": "tour_rafael", "groupName": "Casal de Rafael", "people": 2, "selfGuide": True, "consultantId": "con_rafael", "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_lucas", "groupName": "Família de Lucas", "people": 5, "selfGuide": False, "consultantId": "con_lucas", "status": STATE_WAITING_HOME, "phase": "Casa", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_fernanda", "groupName": "Casal de Fernanda", "people": 2, "selfGuide": False, "consultantId": "con_fernanda", "status": STATE_GALLERY, "phase": "Galeria", "createdAt": created, "updatedAt": created, "allocations": [{"driverId": "drv_ricardo", "cartId": "cart_05", "seats": 2, "arrived": True}]},
            {"id": "tour_juliana", "groupName": "Família de Juliana", "people": 4, "selfGuide": True, "consultantId": "con_juliana", "status": STATE_PRESENTATION, "phase": "Galeria", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_marcela", "groupName": "Família de Marcela", "people": 6, "selfGuide": False, "consultantId": "con_yasmin", "status": STATE_WAITING_DESTINATION, "phase": "Galeria", "destinationId": "dest_prestige", "createdAt": created, "updatedAt": created, "allocations": []},
            {"id": "tour_bruno", "groupName": "Casal de Bruno", "people": 2, "selfGuide": False, "consultantId": "con_rafael", "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "createdAt": created, "updatedAt": created, "allocations": []},
        ],
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


def log_activity(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any] | None, previous: str | None, next_state: str | None, message: str) -> None:
    activity = {"id": new_id("act"), "at": timestamp(), "userName": user["name"], "tourId": tour["id"] if tour else None, "message": message, "previous": previous, "next": next_state}
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


def update_cart(db: dict[str, Any], cart_id: str, status: str) -> None:
    find(db["carts"], cart_id, "Carrinho")["status"] = status


def change_tour_state(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any], next_state: str, message: str) -> None:
    previous = tour["status"]
    tour["status"] = next_state
    tour["updatedAt"] = timestamp()
    log_activity(db, user, tour, previous, next_state, message)


def normalized_allocations(db: dict[str, Any], raw_allocations: Any, people: int) -> list[dict[str, Any]]:
    if not isinstance(raw_allocations, list) or not raw_allocations:
        raise APIError("Selecione pelo menos um carrinho e um motorista.")
    drivers: set[str] = set()
    carts: set[str] = set()
    allocations: list[dict[str, Any]] = []
    for allocation in raw_allocations:
        driver_id = allocation.get("driverId")
        cart_id = allocation.get("cartId")
        if not driver_id or not cart_id:
            raise APIError("Cada alocação exige motorista e carrinho.")
        if driver_id in drivers or cart_id in carts:
            raise APIError("Não repita motorista ou carrinho na mesma saída.")
        drivers.add(driver_id)
        carts.add(cart_id)
        driver = find(db["drivers"], driver_id, "Motorista")
        cart = find(db["carts"], cart_id, "Carrinho")
        if driver["status"] != DRIVER_AVAILABLE:
            raise APIError(f"{driver['name']} não está disponível.")
        if cart["status"] != "DISPONIVEL":
            raise APIError(f"{cart['name']} não está disponível.")
        allocations.append({"driverId": driver_id, "cartId": cart_id, "seats": int(allocation.get("seats") or cart["capacity"]), "arrived": False})
    if sum(item["seats"] for item in allocations) < people:
        raise APIError("A capacidade dos carrinhos não atende todas as pessoas do grupo.")
    return allocations


def apply_action(db: dict[str, Any], user: dict[str, Any], tour: dict[str, Any], action: str, payload: dict[str, Any]) -> None:
    require_operational(user)
    allocations = lambda: tour.get("allocations", [])

    if action == "start":
        if tour["status"] != STATE_AVAILABLE:
            raise APIError("Apenas grupos disponíveis podem iniciar tour.")
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"), tour["people"])
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_IN_TOUR, tours=True)
            update_cart(db, allocation["cartId"], "EM_USO")
        tour["phase"] = "Prestige Waves Bahia"
        change_tour_state(db, user, tour, STATE_IN_TOUR, f"{tour['groupName']} iniciou tour no Prestige.")
        return

    if action == "arrived-home":
        if tour["status"] != STATE_IN_TOUR:
            raise APIError("O grupo precisa estar em tour para chegar à Casa.")
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_HOME)
        tour["phase"] = "Casa"
        change_tour_state(db, user, tour, STATE_HOME, f"{tour['groupName']} chegou à Casa.")
        return

    if action == "return-prestige":
        if tour["status"] != STATE_HOME:
            raise APIError("A ação é válida somente para grupos na Casa.")
        for allocation in allocations():
            update_driver(db, allocation["driverId"], DRIVER_AVAILABLE)
            update_cart(db, allocation["cartId"], "DISPONIVEL")
        tour["allocations"] = []
        tour["phase"] = "Casa"
        change_tour_state(db, user, tour, STATE_WAITING_HOME, f"{tour['groupName']} ficou aguardando transporte na Casa.")
        return

    if action == "pickup-home":
        if tour["status"] != STATE_WAITING_HOME:
            raise APIError("O grupo não está aguardando na Casa.")
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"), tour["people"])
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
            update_driver(db, allocation["driverId"], DRIVER_GALLERY)
        tour["phase"] = "Galeria"
        change_tour_state(db, user, tour, STATE_GALLERY, f"{tour['groupName']} foi entregue na Galeria.")
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
        tour["allocations"] = normalized_allocations(db, payload.get("allocations"), tour["people"])
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
        db = load_database()
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
        return jsonify(user=clean_user(get_current_user(load_database())))


@app.get("/api/bootstrap")
def bootstrap():
    with DB_LOCK:
        db = load_database()
        user = get_current_user(db)
        return jsonify(
            user=clean_user(user),
            data=safe_database(db),
            states={"DISPONIVEL": STATE_AVAILABLE, "EM_TOUR": STATE_IN_TOUR, "NA_CASA": STATE_HOME, "AGUARDANDO_CASA": STATE_WAITING_HOME, "NA_GALERIA": STATE_GALLERY, "EM_APRESENTACAO": STATE_PRESENTATION, "AGUARDANDO_DESTINO": STATE_WAITING_DESTINATION, "EM_DESTINO_FINAL": STATE_FINAL_DESTINATION, "CONCLUIDO": STATE_COMPLETE},
            driverStates={"DISPONIVEL": DRIVER_AVAILABLE, "EM_TOUR": DRIVER_IN_TOUR, "CASA": DRIVER_HOME, "GALERIA": DRIVER_GALLERY, "DESTINO_FINAL": DRIVER_DESTINATION},
        )


@app.post("/api/users")
def create_user():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = load_database()
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
        new_user = {"id": new_id("user"), "username": username, "name": name, "role": role, "active": True, "passwordHash": generate_password_hash(password), "createdAt": timestamp()}
        db["users"].append(new_user)
        log_activity(db, user, None, None, None, f"Usuário {name} criado com perfil {role}.")
        save_database(db)
        return jsonify(user=clean_user(new_user)), 201


@app.post("/api/tours")
def create_tour():
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = load_database()
        user = get_current_user(db)
        require_operational(user)
        group_name = str(payload.get("groupName", "")).strip()
        try:
            people = int(payload.get("people", 0))
        except (ValueError, TypeError):
            people = 0
        if not group_name or not 1 <= people <= 48:
            raise APIError("Informe o grupo e uma quantidade de pessoas entre 1 e 48.")
        find(db["consultants"], payload.get("consultantId"), "Consultor")
        tour = {"id": new_id("tour"), "groupName": group_name, "people": people, "selfGuide": bool(payload.get("selfGuide")), "consultantId": payload["consultantId"], "status": STATE_AVAILABLE, "phase": "Prestige Praia do Forte", "createdAt": timestamp(), "updatedAt": timestamp(), "allocations": []}
        db["tours"].insert(0, tour)
        log_activity(db, user, tour, None, STATE_AVAILABLE, f"{group_name} cadastrado como disponível no Prestige.")
        save_database(db)
        return jsonify(tour=tour), 201


@app.post("/api/tours/<tour_id>/action")
def tour_action(tour_id: str):
    payload = request.get_json(silent=True) or {}
    with DB_LOCK:
        db = load_database()
        user = get_current_user(db)
        tour = find(db["tours"], tour_id, "Tour")
        apply_action(db, user, tour, payload.get("action", ""), payload)
        save_database(db)
        return jsonify(tour=tour)


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
