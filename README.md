# Torn Exchange Website

This is a code repository for domain [https://www.tornexchange.com](https://www.tornexchange.com/). It runs on Django framework, written in Python.

## Compatibility

This project is only compatible with Python 3.8.10.

## Setup Instructions

1. **Install Requirements**: Install all the required packages using the following command:
    ```sh
    pip install -r requirements.txt
    ```

2. **PostgreSQL Setup**: Ensure you have PostgreSQL installed and running. Create a database and configure the connection details in a `.env` file.

3. **Create .env File**: Create a `.env` file with the following information:
    ```env
    SYSTEM_API_KEY=""
    SECRET_KEY=""

    # Database
    POSTGRES_DB="postgres"
    POSTGRES_USER="postgres"
    POSTGRES_PASSWORD=""
    POSTGRES_HOST="localhost"
    POSTGRES_PORT="5432" #default port

    #Django
    DJANGO_DEBUG="True"
    ```

4. **Run Migrations**: Apply the database migrations using the following command:
    ```sh
    python manage.py migrate
    ```

5. **Run the Server**: Start the development server using the following command:
    ```sh
    python manage.py runserver
    ```