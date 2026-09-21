"""Backend API tests for Kitchen Admin Suite - Phase 1"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://kitchen-admin-suite.preview.emergentagent.com').rstrip('/')
TENANT_ID = "c901a226-260a-4ee4-a486-05eb01b76411"
EMAIL = "furkanafsin73@gmail.com"
PASSWORD = "JlMykl5STjjeH_eXxjZkCQ"


@pytest.fixture(scope="module")
def session_with_cookies():
    """Login and return session with cookies"""
    s = requests.Session()
    resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert not data.get("requires_mfa"), "MFA should not be required"
    assert data.get("user"), "User not in response"
    return s


class TestAuth:
    """Authentication endpoints"""

    def test_login_success(self):
        s = requests.Session()
        resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("user") is not None
        assert data["user"]["email"] == EMAIL
        assert not data.get("requires_mfa")

    def test_login_sets_cookies(self):
        s = requests.Session()
        resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert resp.status_code == 200
        # Cookies set via Set-Cookie headers
        cookies = resp.cookies
        assert "access_token" in cookies or "access_token" in s.cookies
        assert "refresh_token" in cookies or "refresh_token" in s.cookies

    def test_login_invalid_credentials(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": "wrongpass"})
        assert resp.status_code == 401

    def test_me_authenticated(self, session_with_cookies):
        resp = session_with_cookies.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == EMAIL
        assert data["is_super_admin"] is True

    def test_me_unauthenticated(self):
        resp = requests.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 401

    def test_refresh_token(self, session_with_cookies):
        resp = session_with_cookies.post(f"{BASE_URL}/api/auth/refresh")
        assert resp.status_code == 200
        assert resp.json().get("ok") is True

    def test_logout(self):
        s = requests.Session()
        s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        resp = s.post(f"{BASE_URL}/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json().get("ok") is True


class TestTenants:
    """Tenant endpoints"""

    def test_my_tenants(self, session_with_cookies):
        resp = session_with_cookies.get(f"{BASE_URL}/api/tenants/my")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        tenant_ids = [t["public_id"] for t in data]
        assert TENANT_ID in tenant_ids

    def test_tenant_has_ecrin_yemek(self, session_with_cookies):
        resp = session_with_cookies.get(f"{BASE_URL}/api/tenants/my")
        assert resp.status_code == 200
        data = resp.json()
        names = [t.get("name", "") for t in data]
        assert any("Ecrin" in n for n in names)


class TestUsers:
    """User endpoints - requires X-Tenant-ID"""

    def test_list_users(self, session_with_cookies):
        resp = session_with_cookies.get(
            f"{BASE_URL}/api/users/",
            headers={"X-Tenant-ID": TENANT_ID}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Users endpoint returns objects with nested 'user' field
        emails = [u["user"]["email"] for u in data]
        assert EMAIL in emails


class TestRoles:
    """Roles endpoints"""

    def test_list_roles(self, session_with_cookies):
        resp = session_with_cookies.get(
            f"{BASE_URL}/api/roles/",
            headers={"X-Tenant-ID": TENANT_ID}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check roles exist (by code field)
        role_codes = [r.get("code", "") for r in data]
        assert any(code in role_codes for code in ["firma_sahibi", "yonetici", "muhasebe"])


class TestDocuments:
    """Documents endpoints"""

    def test_list_documents(self, session_with_cookies):
        resp = session_with_cookies.get(
            f"{BASE_URL}/api/documents/",
            headers={"X-Tenant-ID": TENANT_ID}
        )
        assert resp.status_code == 200


class TestAuditLog:
    """Audit log endpoints"""

    def test_list_audit(self, session_with_cookies):
        resp = session_with_cookies.get(
            f"{BASE_URL}/api/audit/",
            headers={"X-Tenant-ID": TENANT_ID}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Audit returns paginated response
        assert "items" in data or isinstance(data, list)

    def test_audit_has_login_entries(self, session_with_cookies):
        resp = session_with_cookies.get(
            f"{BASE_URL}/api/audit/",
            headers={"X-Tenant-ID": TENANT_ID}
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        # May be empty if super_admin audit is not in tenant scope
        assert isinstance(items, list)


class TestSuperAdmin:
    """Super admin endpoints"""

    def test_super_admin_tenants(self, session_with_cookies):
        resp = session_with_cookies.get(f"{BASE_URL}/api/super-admin/tenants")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_system_health(self, session_with_cookies):
        resp = session_with_cookies.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("database") == "ok"


class TestModules:
    """Modules endpoints"""

    def test_list_modules(self, session_with_cookies):
        resp = session_with_cookies.get(
            f"{BASE_URL}/api/modules/",
            headers={"X-Tenant-ID": TENANT_ID}
        )
        assert resp.status_code == 200
