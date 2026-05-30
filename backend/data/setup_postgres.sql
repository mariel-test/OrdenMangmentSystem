 SELECT 
 o.order_id,
 c.name as customer_name,
 p.product_name,
o.quantity,
 o.unit_price,
  o.total_price,
 o.status,
   o.created_at
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
ORDER BY o.created_at DESC;