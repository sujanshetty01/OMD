CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    registration_date DATE
);

INSERT INTO customers (first_name, last_name, email, phone, registration_date) VALUES
('John', 'Doe', 'john.doe@example.com', '555-0100', '2023-01-15'),
('Jane', 'Smith', 'jane.smith@testmail.com', '555-0101', '2023-02-20'),
('Alice', 'Johnson', 'alice.j@domain.net', '555-0102', '2023-03-10'),
('Bob', 'Williams', 'bob.w@example.org', '555-0103', '2023-04-05'),
('Charlie', 'Brown', 'charlie.b@testmail.com', '555-0104', '2023-05-12');

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    amount DECIMAL(10, 2),
    status VARCHAR(20)
);

INSERT INTO orders (customer_id, order_date, amount, status) VALUES
(1, '2023-06-01', 150.00, 'Shipped'),
(2, '2023-06-02', 200.50, 'Processing'),
(1, '2023-06-05', 50.00, 'Delivered'),
(3, '2023-06-10', 300.75, 'Shipped'),
(4, '2023-06-15', 120.25, 'Cancelled');
