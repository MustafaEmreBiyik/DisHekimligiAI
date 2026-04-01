"""Authentication endpoint tests running fully in-process with local SQLite DB."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.api import deps
from app.api.routers import auth
from db.database import Base, User, UserRole


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    db_file = tmp_path / "auth_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Keep tests deterministic: no JSON seed import.
    monkeypatch.setattr(auth, "SEED_USER_FILES", [])

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth")
    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[auth.get_db] = override_get_db

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_user(db_factory, user_id: str, name: str, role: UserRole, password: str = "test123") -> None:
    db = db_factory()
    try:
        db.add(
            User(
                user_id=user_id,
                display_name=name,
                email=f"{user_id}@example.com",
                hashed_password=auth.get_password_hash(password),
                role=role,
                is_archived=False,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_then_login(auth_client):
    client, _ = auth_client
    register_payload = {
        "student_id": "test999",
        "name": "Test User",
        "password": "test123",
        "email": "test@example.com",
    }

    register_response = client.post("/api/auth/register", json=register_payload)
    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["student_id"] == "test999"
    assert register_body["name"] == "Test User"
    assert register_body["user_id"] == "test999"
    assert register_body["display_name"] == "Test User"
    assert register_body["role"] == "student"
    assert register_body["token_type"] == "bearer"
    assert register_body["access_token"]

    login_response = client.post(
        "/api/auth/login",
        json={"student_id": "test999", "password": "test123"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["student_id"] == "test999"
    assert login_body["role"] == "student"
    assert login_body["access_token"]


def test_jwt_payload_standardized_fields(auth_client):
    client, _ = auth_client
    register_response = client.post(
        "/api/auth/register",
        json={
            "student_id": "jwt001",
            "name": "JWT User",
            "password": "test123",
        },
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    payload = jwt.decode(token, deps.get_secret_key(), algorithms=[deps.ALGORITHM])
    assert set(payload.keys()) == {"user_id", "role", "display_name", "exp"}
    assert payload["user_id"] == "jwt001"
    assert payload["role"] == "student"
    assert payload["display_name"] == "JWT User"


def test_register_duplicate_student_id_returns_400(auth_client):
    client, _ = auth_client
    payload = {
        "student_id": "dup001",
        "name": "Duplicate User",
        "password": "test123",
        "email": "dup@example.com",
    }

    first = client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"]


def test_me_endpoint_returns_authenticated_user(auth_client):
    client, _ = auth_client
    register_response = client.post(
        "/api/auth/register",
        json={
            "student_id": "me001",
            "name": "Me User",
            "password": "test123",
            "email": "me@example.com",
        },
    )
    token = register_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers=_auth_header(token))

    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["student_id"] == "me001"
    assert me_body["user_id"] == "me001"
    assert me_body["name"] == "Me User"
    assert me_body["display_name"] == "Me User"
    assert me_body["role"] == "student"


def test_student_forbidden_from_user_listing(auth_client):
    client, _ = auth_client
    register_response = client.post(
        "/api/auth/register",
        json={
            "student_id": "std403",
            "name": "Student User",
            "password": "test123",
        },
    )
    token = register_response.json()["access_token"]

    response = client.get("/api/auth/users", headers=_auth_header(token))
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_instructor_can_list_users(auth_client):
    client, db_factory = auth_client
    _create_user(db_factory, user_id="inst001", name="Instructor One", role=UserRole.INSTRUCTOR)

    token = deps.create_access_token(
        user_id="inst001",
        role=UserRole.INSTRUCTOR,
        display_name="Instructor One",
    )

    response = client.get("/api/auth/users", headers=_auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(user["user_id"] == "inst001" for user in body)


def test_instructor_cannot_archive_user_returns_403(auth_client):
    client, db_factory = auth_client
    _create_user(db_factory, user_id="inst002", name="Instructor Two", role=UserRole.INSTRUCTOR)
    _create_user(db_factory, user_id="target001", name="Target User", role=UserRole.STUDENT)

    instructor_token = deps.create_access_token(
        user_id="inst002",
        role=UserRole.INSTRUCTOR,
        display_name="Instructor Two",
    )

    response = client.patch(
        "/api/auth/users/target001/archive",
        json={"archived": True},
        headers=_auth_header(instructor_token),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_admin_can_archive_user_and_archived_user_cannot_login(auth_client):
    client, db_factory = auth_client
    _create_user(db_factory, user_id="admin001", name="Admin One", role=UserRole.ADMIN)
    _create_user(db_factory, user_id="student001", name="Student One", role=UserRole.STUDENT)

    admin_token = deps.create_access_token(
        user_id="admin001",
        role=UserRole.ADMIN,
        display_name="Admin One",
    )

    archive_response = client.patch(
        "/api/auth/users/student001/archive",
        json={"archived": True},
        headers=_auth_header(admin_token),
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True

    login_response = client.post(
        "/api/auth/login",
        json={"student_id": "student001", "password": "test123"},
    )
    assert login_response.status_code == 401
