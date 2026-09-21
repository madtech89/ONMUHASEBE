"""
Seeds the database with initial data.
IDEMPOTENT: Safe to run multiple times.
"""
import asyncio
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MODULES = [
    ("core", "Çekirdek", "Core", True, 0),
    ("catering", "Catering / Yemek", "Catering", False, 10),
    ("customers", "Cariler", "Customers & Suppliers", False, 20),
    ("cash_bank", "Kasa & Banka", "Cash & Bank", False, 30),
    ("cheques", "Çekler & Senetler", "Cheques", False, 40),
    ("loans", "Krediler", "Loans", False, 50),
    ("inventory", "Stok", "Inventory", False, 60),
    ("purchasing", "Satın Alma", "Purchasing", False, 70),
    ("cost_accounting", "Maliyet Muhasebesi", "Cost Accounting", False, 80),
    ("employees", "Personel", "Employees", False, 90),
    ("attendance", "Puantaj", "Attendance", False, 100),
    ("payroll", "Bordro", "Payroll", False, 110),
    ("vehicles", "Araçlar & Filo", "Vehicles & Fleet", False, 120),
    ("documents", "Belgeler", "Documents", False, 130),
    ("advisor", "Mali Müşavir Merkezi", "Accounting Advisor", False, 140),
    ("reports", "Raporlar", "Reports", False, 150),
]

PERMISSIONS = [
    # Core
    ("settings.manage", "Firma Ayarlarını Yönet", "core"),
    ("users.view", "Kullanıcıları Görüntüle", "core"),
    ("users.manage", "Kullanıcıları Yönet", "core"),
    ("roles.manage", "Rolleri Yönet", "core"),
    ("audit.view", "Audit Log Görüntüle", "core"),
    ("modules.manage", "Modülleri Yönet", "core"),
    # Documents
    ("documents.upload", "Belge Yükle", "documents"),
    ("documents.view", "Belgeleri Görüntüle", "documents"),
    ("documents.delete", "Belge Sil/Arşivle", "documents"),
    # Catering/Orders
    ("orders.create", "Sipariş Oluştur", "catering"),
    ("orders.view", "Siparişleri Görüntüle", "catering"),
    ("orders.edit", "Sipariş Düzenle", "catering"),
    ("orders.delete", "Sipariş Sil", "catering"),
    # Customers
    ("customers.create", "Müşteri Oluştur", "customers"),
    ("customers.view", "Müşterileri Görüntüle", "customers"),
    ("customers.edit", "Müşteri Düzenle", "customers"),
    ("customers.deactivate", "Müşteriyi Pasifleştir", "customers"),
    # Meal Entries
    ("meal_entries.create", "Yemek Girişi Yap", "catering"),
    ("meal_entries.view", "Yemek Girişlerini Görüntüle", "catering"),
    ("meal_entries.correct", "Yemek Girişi Düzelt", "catering"),
    ("meal_entries.view_financial", "Yemek Finansallarını Gör", "catering"),
    # Meal Prices
    ("meal_prices.view", "Yemek Fiyatlarını Görüntüle", "catering"),
    ("meal_prices.manage", "Yemek Fiyatlarını Yönet", "catering"),
    # Finance
    ("customer_financials.view", "Müşteri Finansallarını Gör", "finance"),
    ("ledger.view", "Defterleri Görüntüle", "finance"),
    ("payments.create", "Ödeme Oluştur", "finance"),
    ("payments.view", "Ödemeleri Görüntüle", "finance"),
    ("payments.approve", "Ödeme Onayla", "finance"),
    ("expenses.create", "Gider Oluştur", "finance"),
    ("expenses.view", "Giderleri Görüntüle", "finance"),
    # Reports
    ("reports.financial.view", "Mali Rapor Görüntüle", "reports"),
    ("reports.view", "Raporları Görüntüle", "reports"),
    ("reports.export", "Rapor İndir (PDF/Excel)", "reports"),
    # HR
    ("payroll.view", "Maaş Bilgilerini Görüntüle", "hr"),
    ("attendance.create", "Puantaj Girişi Yap", "hr"),
    ("attendance.view", "Puantaj Görüntüle", "hr"),
]

ROLES = {
    "firma_sahibi": ("Firma Sahibi", "all"),
    "yonetici": ("Yönetici", [
        "settings.manage", "users.view", "users.manage", "roles.manage",
        "audit.view", "modules.manage",
        "documents.upload", "documents.view", "documents.delete",
        "orders.create", "orders.view", "orders.edit",
        "customers.create", "customers.view", "customers.edit", "customers.deactivate",
        "meal_entries.create", "meal_entries.view", "meal_entries.correct", "meal_entries.view_financial",
        "meal_prices.view", "meal_prices.manage",
        "customer_financials.view", "ledger.view",
        "payments.create", "payments.view", "payments.approve",
        "expenses.create", "expenses.view",
        "reports.financial.view", "reports.view", "reports.export",
    ]),
    "muhasebe": ("Muhasebe", [
        "documents.upload", "documents.view",
        "customers.view", "customer_financials.view",
        "meal_entries.view", "meal_entries.view_financial",
        "meal_prices.view",
        "ledger.view", "payments.create", "payments.view",
        "expenses.create", "expenses.view",
        "reports.financial.view", "reports.view", "reports.export",
    ]),
    "siparis_personeli": ("Sipariş Personeli", [
        "orders.create", "orders.view", "orders.edit",
        "customers.view", "documents.view",
        "meal_entries.create", "meal_entries.view",
        "meal_prices.view",
    ]),
    "depo": ("Depo", ["orders.view", "documents.view", "meal_entries.view"]),
    "personel_yetkilisi": ("Personel/Puantaj Yetkilisi", [
        "attendance.create", "attendance.view",
        "payroll.view", "documents.view",
    ]),
    "mali_musavir": ("Mali Müşavir", [
        "documents.view", "ledger.view",
        "reports.financial.view", "reports.view", "reports.export",
        "customer_financials.view",
        "meal_entries.view", "meal_entries.view_financial",
    ]),
}


async def seed_database(db):
    from sqlalchemy import select
    from app.core.config import settings
    from app.core.security import hash_password
    from app.models.tenant import Module, TenantModule, Tenant, TenantSettings
    from app.models.user import User, TenantUser
    from app.models.role import Permission, Role, RolePermission, UserRole

    logger.info("Running database seed...")

    # 1. Seed Modules
    for code, name_tr, name_en, is_core, sort_order in MODULES:
        result = await db.execute(select(Module).where(Module.code == code))
        if not result.scalar_one_or_none():
            db.add(Module(code=code, name_tr=name_tr, name_en=name_en, is_core=is_core, sort_order=sort_order))
    await db.flush()

    # 2. Seed Permissions
    perm_map = {}
    for code, name, module in PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.code == code))
        p = result.scalar_one_or_none()
        if not p:
            p = Permission(code=code, name=name, module=module)
            db.add(p)
            await db.flush()
        perm_map[code] = p
    await db.flush()

    # 3. Seed Super Admin User
    admin_email = settings.SUPER_ADMIN_EMAIL
    admin_password = settings.SUPER_ADMIN_PASSWORD

    admin_result = await db.execute(select(User).where(User.email == admin_email.lower()))
    admin = admin_result.scalar_one_or_none()
    if not admin:
        admin = User(
            email=admin_email.lower(),
            password_hash=hash_password(admin_password),
            first_name="Super",
            last_name="Admin",
            is_super_admin=True,
            status="active",
        )
        db.add(admin)
        await db.flush()
        logger.info(f"Created super admin: {admin_email}")
    else:
        # Update password if it was changed in env
        from app.core.security import verify_password, needs_rehash
        if not verify_password(admin_password, admin.password_hash):
            admin.password_hash = hash_password(admin_password)
            logger.info("Updated super admin password")

    # 4. Seed Ecrin Yemek Tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.name == "Ecrin Yemek"))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(name="Ecrin Yemek", short_name="EY")
        db.add(tenant)
        await db.flush()
        settings_obj = TenantSettings(
            tenant_id=tenant.id,
            ticari_unvan="Ecrin Yemek Catering",
            kisa_ad="Ecrin Yemek",
            para_birimi="TRY",
            kdv_orani="20",
            timezone="Europe/Istanbul",
        )
        db.add(settings_obj)
        logger.info("Created Ecrin Yemek tenant")

    # 5. Enable modules for Ecrin Yemek
    modules_result = await db.execute(select(Module))
    all_modules = modules_result.scalars().all()
    enabled_codes = {"core", "documents", "catering", "customers", "reports"}
    for module in all_modules:
        existing = await db.execute(
            select(TenantModule).where(
                TenantModule.tenant_id == tenant.id,
                TenantModule.module_id == module.id
            )
        )
        if not existing.scalar_one_or_none():
            db.add(TenantModule(
                tenant_id=tenant.id,
                module_id=module.id,
                is_enabled=(module.code in enabled_codes or module.is_core),
                enabled_at=datetime.now(timezone.utc) if (module.code in enabled_codes or module.is_core) else None,
            ))

    # 6. Seed Roles for Ecrin Yemek
    role_map = {}
    all_perm_codes = list(perm_map.keys())
    for code, (name, perms) in ROLES.items():
        r_result = await db.execute(
            select(Role).where(Role.code == code, Role.tenant_id == tenant.id)
        )
        role = r_result.scalar_one_or_none()
        if not role:
            role = Role(tenant_id=tenant.id, code=code, name=name, is_system_role=True)
            db.add(role)
            await db.flush()
            perm_codes = all_perm_codes if perms == "all" else perms
            for perm_code in perm_codes:
                if perm_code in perm_map:
                    db.add(RolePermission(role_id=role.id, permission_id=perm_map[perm_code].id))
        role_map[code] = role
    await db.flush()

    # 7. Add super admin to Ecrin Yemek as owner
    tu_result = await db.execute(
        select(TenantUser).where(TenantUser.user_id == admin.id, TenantUser.tenant_id == tenant.id)
    )
    if not tu_result.scalar_one_or_none():
        db.add(TenantUser(tenant_id=tenant.id, user_id=admin.id, status="active", is_owner=True))

    # 8. Assign firma_sahibi role to super admin in Ecrin Yemek
    if "firma_sahibi" in role_map:
        ur_result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == admin.id,
                UserRole.role_id == role_map["firma_sahibi"].id,
                UserRole.tenant_id == tenant.id,
            )
        )
        if not ur_result.scalar_one_or_none():
            db.add(UserRole(user_id=admin.id, role_id=role_map["firma_sahibi"].id, tenant_id=tenant.id))

    await db.commit()

    # 9. Seed default MealTypes (system-wide, tenant_id=NULL)
    from app.models.meal import MealType
    DEFAULT_MEAL_TYPES = [
        ("kahvalti", "Kahvaltı", "Breakfast", 1),
        ("ogle", "Öğle Yemeği", "Lunch", 2),
        ("aksam", "Akşam Yemeği", "Dinner", 3),
        ("ara_ogun", "Ara Öğün", "Snack", 4),
        ("ikindi", "İkindi", "Afternoon Break", 5),
    ]
    for code, name_tr, name_en, sort_order in DEFAULT_MEAL_TYPES:
        mt_result = await db.execute(
            select(MealType).where(MealType.code == code, MealType.tenant_id.is_(None))
        )
        if not mt_result.scalar_one_or_none():
            db.add(MealType(
                code=code, name_tr=name_tr, name_en=name_en,
                sort_order=sort_order, is_active=True, tenant_id=None,
            ))
    await db.commit()

    # 10. Write test credentials
    _write_credentials(admin_email, admin_password, tenant)
    logger.info("Seed complete")


def _write_credentials(email: str, password: str, tenant):
    creds_path = Path("/app/memory/test_credentials.md")
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# Test Credentials

## Super Admin
- **Email**: {email}
- **Password**: {password}
- **Role**: Super Admin (is_super_admin=true)
- **Tenant**: Ecrin Yemek (owner)

## First Tenant
- **Name**: {tenant.name}
- **Public ID**: {tenant.public_id}

## API Endpoints
- Login: POST /api/auth/login
- Me: GET /api/auth/me
- Refresh: POST /api/auth/refresh
- Logout: POST /api/auth/logout
- MFA Setup: POST /api/auth/mfa/setup
- MFA Enable: POST /api/auth/mfa/enable
- Tenants: GET /api/tenants/my
- Users: GET /api/users/
- Roles: GET /api/roles/
- Documents: GET /api/documents/
- Audit: GET /api/audit/
- Super Admin Tenants: GET /api/super-admin/tenants
- Health: GET /api/health
"""
    creds_path.write_text(content)


if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')

    async def main():
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await seed_database(db)

    asyncio.run(main())
