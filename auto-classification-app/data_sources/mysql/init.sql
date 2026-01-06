CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2),
    supplier VARCHAR(50)
);

INSERT INTO products (product_name, category, price, supplier) VALUES
('Laptop Pro X', 'Electronics', 1200.00, 'TechCorp'),
('Wireless Mouse', 'Electronics', 25.50, 'GadgetWorld'),
('Ergonomic Chair', 'Furniture', 350.00, 'OfficeDepot'),
('Desk Lamp', 'Furniture', 45.00, 'BrightLights'),
('Noise Cancelling Headphones', 'Electronics', 299.99, 'AudioBest');

CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    stock_quantity INT,
    warehouse_location VARCHAR(50),
    last_restock_date DATE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

INSERT INTO inventory (product_id, stock_quantity, warehouse_location, last_restock_date) VALUES
(1, 50, 'Warehouse A', '2023-05-01'),
(2, 200, 'Warehouse B', '2023-05-15'),
(3, 30, 'Warehouse A', '2023-04-20'),
(4, 100, 'Warehouse C', '2023-06-01'),
(5, 75, 'Warehouse B', '2023-05-25');
