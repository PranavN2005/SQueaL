# User Stories and Exceptions

**Example:** As a \[persona\], I \[want to\], \[so that\].

## User Stories

1. As a server, I want to be able to split a bill between multiple
    customers, so guests/customers can pay individually if they want
    to.\
2.  As a server, I want to be able to mark/designate a table as
    "reserved", so I can ensure it is held for upcoming guests.\
3.  As a host, I want to be able to divide total tips evenly among my
    wait staff, so that tips are distributed evenly at the end of a
    shift.\
4.  As a restaurant manager, I want to keep track of how long tables
    each take on average so that I can plan for staffing based on
    customer count.\
5.  As a cook, I want to know how long tables have been waiting for
    their orders so that I know what tickets need priority.\
6.  As a waiter, I want to know how many tables have tipped in order to
    count my total tips for the day.\
7.  As a dishwasher, I want to know when tables turn over so I can
    expect when dishes are coming to the sink.\
8.  As a waiter, I want to be able to see how many customers order
    appetizers so that I can plan the table's priorities accordingly.\
9.  As a restaurant owner, I want to be able to see which months
    generate more revenue so that I can plan for the needs of seasonal
    workers.\
10. As a hostess, I want to be able to see all the tables at once as
    well as their statuses so that I know wait times for guests that are
    requesting to dine.\
11. As a hostess, I want to be able to see which waiters are staffed to
    which tables so that I am able to optimize their areas to make their
    work more efficient and space-oriented.\
12. As an owner, I want to be able to track the performance of my wait
    staff to see not only how fast they turn over tables but also their
    tips to see how the customers are reacting to their service.

## Exceptions

1.  If a customer tries to book a reservation at a table already taken,
    it will prompt them to pick a different time and date.\
2.  If identical tickets come in at the same time, they need to be
    differentiated using a unique identifier, or the system will drop
    the duplicate entry.\
3.  If a cook tries to call off within 24 hours of their shift, it will
    prompt them to show up anyway.\
4.  If a host or waitress tries to book or delete a table which isn't in
    the system, it will respond with a table_id not found error.\
5.  If tables are full and the host tries to book another table, the
    system will check the maximum number of tables and prevent invalid
    bookings.\
6.  If a waiter tries to split a bill into invalid amounts (more or less
    than the total), the system will reject the entered split and prompt
    them to correct it.\
7.  If the restaurant starts accepting DoorDash orders, it should not
    automatically assign a table; instead, it should separate delivery
    orders from table-based orders.\
8.  If a host attempts to divide tips but the total amount cannot be
    evenly distributed (e.g., rounding issues or invalid input), the
    system will prompt the user to confirm rounding adjustments or
    manually adjust the distribution.\
9.  If any user tries to close a table that has no orders associated
    with it, the system will prompt a confirmation or require at least
    one order before allowing closure.\
10. If a user tries to enter invalid data, the system will display an
    error message explaining the issue and prevent submission until it
    is corrected.\
11. If a table's status hasn't changed for over an hour, the system will
    alert the user that the table needs to be checked on.\
12. If a hostess tries to seat a party of 6 at a table that only seats
    4, the system will return an error telling them to pick a different
    table.
