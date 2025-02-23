# Torn Exchange Website

This is a code repository for domain [https://tornexchange.com](https://tornexchange.com/). It runs on Django framework, written in Python.

## Compatibility

This project is only compatible with Python 3.8.10.

## Setup Instructions

1. **Install Requirements**: Install all the required packages using the following command:
    ```sh
    pip install -r requirements.txt
    ```

2. **PostgreSQL Setup**: Ensure you have PostgreSQL installed and running. Create a database and configure the connection details in a `.env` file.

3. **Generate a Secret Key**: Use the following command to generate a Django secret key:  
    ```sh  
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"  
    ```  
    Copy the output and save it for the next step.


4. **Create .env File**: Create a `.env` file with the following information:
    ```env
    SYSTEM_API_KEY=""
    SECRET_KEY=""

    # Database
    POSTGRES_DB="postgres"
    POSTGRES_USER="postgres"
    POSTGRES_PASSWORD=""
    POSTGRES_HOST="localhost"
    POSTGRES_PORT="5432" #default port

    # Logging
    SENTRY_DSN_URL=""

    # Local stuff
    DJANGO_DEBUG="False"

    #Other
    CACHE_DIR=""
    500_ERRORS_FILE=""

    ```

5. **Set up caching folder**
    ```
    mkdir /path/to/cache
    chmod 755 /path/to/cache
    ```

    Currently the setup is done for file-based caching. Caching folder should sit outsite the repository/app root folder.


6. **Run Migrations**: Apply the database migrations using the following command:
    ```sh
    python manage.py migrate
    ```

7. **Run the Server**: Start the development server using the following command:
    ```sh
    python manage.py runserver
    ```