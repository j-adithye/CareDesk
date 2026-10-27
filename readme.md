# CareDeskProject – Database Setup

## Step 1: Create and Activate a Virtual Environment

Create a virtual environment and activate it before installing the project dependencies.
```
python -m venv .venv
```
```
.\.venv\Scripts\Activate
```

Install the required dependencies by running the following command in the terminal:

```bash
pip install -r requirements.txt
```

## Step 2: Project Structure

- **Project folder:** `CareDeskProject`
- **Application structure:** Each role has its own Django app.

## Step 3: Create the MySQL Database

Open MySQL and execute the following command to create the database:

```sql
CREATE DATABASE cmsdb;
```

Either create this exact db or Ensure that your Django project's database configuration in `settings.py` matches your MySQL database credentials and database name.

## Step 4: Create and Apply Migrations

Run the following commands in the terminal from the directory containing `manage.py`.

**1. Create migration files:**

```bash
python manage.py makemigrations
```

**2. Apply migrations to the database:**

```bash
python manage.py migrate

These commands create the necessary database tables based on your Django models and apply them to the MySQL database.

## Step 5: Entity-Relationship (ER) Diagram

The following ER diagram represents the database structure of the CareDeskProject.

[View and edit the ER diagram on Mermaid Live Editor](https://mermaid.live/edit#pako:eNq9V1tv2jAU_iuRn6Hi0paWt5QEFJVCBtmmTUiVG7vUq2Mj29nKgP8-JyQhDqFlD9sT8rl-5_g7x2EDQo4w6AMsHAKXAkYLsWCWNZuO3bm13TabfGPNA3s4nFt96wXKvTqTpPqt5UwHwXT26LiB7Y0TuwUg0oILcGy8se688dibjBKzUGCocBayEiSzzqRfXffesb8lTr-4eM1cCulJY87eC277_tSbBA_uJEiMoVKYoSy2bwdeKq-3feI8R2FoEuvt1vJn7nww8_zAm06MxpmKrH-lljwRSjF6JOyk-cYQPgbuPAXEBcIiS7KXvWeNOMN_keTBdbyBN3ETV8JCGqP81g6aj_yW5CdmWc4yxzb7g6UDK2vGKfaQ5d_nQqkEYUsrIIrivWxnkMrwniv4_Gy4l2IOqzGHMaUTGOFcjDQXLYc_Vcz8F92rimykeYJFRWgjJLCUlXA_ijMOSQSpNYcUinXF97PEgpWw5LmhlJrvKBdr1lEMmeVJO1S6n0ZHqoNmDwLvixd8exxPR7r_lC_lofeG0mjimC-NFiZ1KBJhfQcHfEz3rmj3UWcfdBvgsoyudgqNtA4PFRdp5kYpYppZJxKqnD6VugyVZXl_B5zJmCqoCGdDjGUF23yl7SAlv1MDo4HF3jCAfcX4FcF1HSsP7NkZBdYHKioc3tfHz-W7ygYyovgaN2aqDs6ZhK4l7x3lHI0Ej1dn0L-G6emNDNJ9jqbsLL4ae9Oo0V6tuP6NqnW-08VDW4YGc8uxHH02GFTSlZmUVTnDUHL2UZG7uh1q3pjuVSjIKuHbEb9zVq6jleJRlazJk8y4JPJMFPv1bmQPsKwlSyIvk2W_P3n4OsbPqjpTnxlRviAhPutiD1vfQPKAEQkJw-9PUpmmWKes0Qx4tIJs_Y_Qn3jAjFKOWFm5Y5ObpcJNxacYMkXU2qaU68v8EHeuCLiCtMogvfFiebqSGmr8XRUZkf5rBcWHkYH7Tn8jaYejWUp02Vzcrct74IOXoXiZ4ycDVwEWvh0bO0SGPGZHZBsJqN8lI8zJ9VhofEiqozx0y6SrZpU1GDN30ABLQRDoKxHjBoiwiGByBJtEvQDqBeu5AclHusAofmsiKF6bIadc6A92lvjr6frOeZSH0K_C8gX0nyGV-hSvEtjZn4XCJH1TBgk00G-32zdpENDfgDd9vm5fdK5urzqt28vudeum0wBr0G92272Lm851q9PpXva6t71dA_xOs7Yvuq3W9W2nddnr9S7bV1e93R9_ix3q)

```
**Note:** Run `makemigrations` and `migrate` after configuring the database connection and defining your Django models.
