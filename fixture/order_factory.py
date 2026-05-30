"""
Driver Factory Pattern - Playwright + Faker
Estructura:
  1. Interfaz base (orders_factory.py)
  2. Concrete Factories  (Chromium, Firefox, WebKit)
  3. BrowserManager     (selector por env)
  4. FakerFactory       (datos de test por locale)
  5. conftest.py        (fixtures de pytest)
  6. Ejemplo de testcat /data/MyProject/OrderManagmentSystem/backend/routers/app_postgres.py | head -30
"""
import os
from faker import Faker
from backend.routers.app_postgres import app

fake = Faker("en_US")  # Faker con locale en español para datos más realistas

def create_order_data(customer_id: int | None = None, product_id: int | None = None) -> dict:
    """Genera datos de orden aleatorios usando Faker."""
    return {
        "customer_id": customer_id if customer_id is not None else fake.random_int(min=1, max=1000),
        "product_id": product_id if product_id is not None else fake.random_int(min=1, max=1000),
        "quantity": fake.random_int(min=1, max=1000),
        "unit_price": round(fake.pyfloat(min_value=1.00, max_value=999.99, right_digits=2), 2),  # Precio entre 0.00 y 999.99
        "status": fake.random_element(elements=["pending", "processing", "completed"]),
        "notes": fake.sentence(nb_words=6)
    }