# Group Project Proposal - Restaurant Table relations

## Contributors -

- Danny Kullman : <dkullman@calpoly.edu>
- Dylan Martin: <dmart328@calpoly.edu>
- Pranav Nallaperumal: <pnallape@calpoly.edu>
- Andy Cai: <acai10@calpoly.edu>
  
A backend API designed to manage restaurant table operations in real time. The system will track tables, the number of customers seated at each table, and the total bill associated with each party. It will allow staff to create, update, and close tables while maintaining an accurate record of orders and occupancy. The API should support both read and write operations to facilitate the earlier features, enabling restaurant staff to monitor table usage and billing easily.

It will of course use a relational database for persistence and to capture relationships between entities like tables, groups, waiters, bills, etc. It will be our source of truth for activity, financial, and table status data. Essentially (trying to) mimic modern restaurant POS(Point of Sale) systems.
