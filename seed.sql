INSERT INTO employees (employee_id, first_name, last_name) VALUES
    (10, 'Dylan',   'Martin'),
    (11, 'Pranav',    'Nallaperumal'),
    (12, 'Danny', 'Kullman'),
    (13, 'Andy', 'Cai')
ON CONFLICT (employee_id) DO NOTHING;

INSERT INTO tables (table_id, capacity, status, assigned_waiter_id, current_party_size) VALUES
    (1, 2, 'available', NULL, NULL),
    (2, 4, 'occupied',  10,   3),
    (3, 4, 'available', NULL, NULL),
    (4, 6, 'occupied',  11,   5),
    (5, 2, 'available', NULL, NULL),
    (6, 8, 'available', NULL, NULL),
    (7, 6, 'available', NULL, NULL),
    (8, 4, 'available', NULL, NULL)
ON CONFLICT (table_id) DO NOTHING;

-- Keep auto-increment sequences ahead of the seeded ids so future inserts
-- don't collide with these fixed values.
SELECT setval('employees_employee_id_seq', (SELECT MAX(employee_id) FROM employees));
SELECT setval('tables_table_id_seq',       (SELECT MAX(table_id)    FROM tables));
