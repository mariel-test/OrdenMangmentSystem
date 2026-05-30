import pytest
import psycopg2
from backend.routers.app_postgres import app, DB_CONFIG
from fixture.order_factory import create_order_data
from playwright.sync_api import Page

LIST_ENDPOINT = "orders"



def get_test_db():
    """Obtiene conexión a BD"""
    return psycopg2.connect(**DB_CONFIG)

class TestAPICustomer:
    @pytest.mark.smoke
    @pytest.mark.happy_path
    @pytest.mark.order(1)
    def test_01_get_orders(self, client):
        """GET /orders devuelve órdenes (puede haber datos previos)"""
        response = client.get(f"/api/{LIST_ENDPOINT}")

        response_json = response.get_json()
        assert response.status_code == 200
        assert 'data' in response.json
        assert isinstance(response.json['data'], list)      
        print(f"\n✓ GET /orders OK: {response_json.get('count', 0)} órdenes")
        print('--- Fin del test de orden 1 ---\n')


    @pytest.mark.smoke
    @pytest.mark.happy_path
    @pytest.mark.order(2)
    def test_02_post_order_persists_in_db(self, client):
        """POST /orders inserta orden y persiste en BD"""
        conn = get_test_db()
        cursor = conn.cursor()

        # Obtener customer y product
        cursor.execute('SELECT customer_id FROM customers LIMIT 1')
        customer_id = cursor.fetchone()[0]
        cursor.execute('SELECT product_id FROM products LIMIT 1')
        product_id = cursor.fetchone()[0]

        # Contar órdenes ANTES
        cursor.execute('SELECT COUNT(*) FROM orders')
        count_before = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Crear orden
        payload = create_order_data(customer_id=customer_id, product_id=product_id)
        response = client.post(
            f"/api/{LIST_ENDPOINT}",
            json=payload,
            content_type='application/json'
        )

        assert response.status_code == 201, f"Error: {response.json}"
        assert response.json['success'] is True
        order_id = response.json['data']['order_id']
        print(f"\n✓ Orden creada con ID: {order_id}")

        # Verificar en BD que persiste
        conn = get_test_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders')
        count_after = cursor.fetchone()[0]

        assert count_after == count_before + 1, \
            f"BD no fue actualizada: antes={count_before}, después={count_after}"

        # Verificar datos
        cursor.execute(
            'SELECT customer_id, product_id FROM orders WHERE order_id = %s',
            (order_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        assert row is not None
        assert row[0] == customer_id
        print(f"✓ Orden persiste en BD (count: {count_before}→{count_after})")


    @pytest.mark.smoke
    @pytest.mark.happy_path
    @pytest.mark.order(3)
    def test_03_get_orders_shows_inserted_data(self, client):
        """GET /orders retorna órdenes insertadas"""
        conn = get_test_db()
        cursor = conn.cursor()

        # Obtener datos
        cursor.execute('SELECT customer_id FROM customers LIMIT 1')
        customer_id = cursor.fetchone()[0]
        cursor.execute('SELECT product_id FROM products LIMIT 1')
        product_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Crear orden
        payload = create_order_data(customer_id=customer_id, product_id=product_id)
        client.post(f"/api/{LIST_ENDPOINT}", json=payload, content_type='application/json')

        # GET debe retornar órdenes
        response = client.get(f"/api/{LIST_ENDPOINT}")

        assert response.status_code == 200
        assert response.json['count'] > 0
        assert len(response.json['data']) > 0

        # Validar estructura
        for order in response.json['data']:
            assert 'order_id' in order
            assert 'customer_id' in order
            assert 'product_id' in order

        print(f"✓ GET retorna {response.json['count']} orden(es)")
