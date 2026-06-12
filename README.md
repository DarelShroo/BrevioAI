# BrevioAI

This project uses **Docker** to simplify the development environment setup. To get the project up and running, you'll need to have **Docker** and **Docker Compose** installed on your machine.

## Prerequisites

Make sure you have **Docker** and **Docker Compose** installed. If you don't have them yet, you can follow the official installation guides:

- [Docker Installation](https://docs.docker.com/get-docker/)
- [Docker Compose Installation](https://docs.docker.com/compose/install/)

## Running the Project

1. Clone this repository to your local machine:

   ```bash
   git clone <repository-url>
   ```

2. Navigate to the project root directory:

   ```bash
   cd BrevioAI
   ```

3. Create the `.env` file from the example:

   ```bash
   cp .env.example .env
   ```
   *Note:* The default configuration sets `OPENAI_API_URL` to `http://host.docker.internal:8080/v1` so the containers can connect to a local LLM API running on your host machine at port 8080. If your local API is running on a different port, update the `.env` accordingly.

### 🚀 Running in Development Mode (Hot-Reload)

This mode runs the Frontend using Vite's development server on port **3000** with Hot-Module Replacement (HMR). Changes to your Vue code will reflect instantly in the browser without rebuilding Docker.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/docs

### 🏭 Running in Production Mode

This mode builds the frontend for production and serves it using an ultra-fast Nginx web server on port **80**. Use this for final testing or deployment.

```bash
docker compose up -d --build
```
- **Frontend**: http://localhost:80
- **Backend API**: http://localhost:8000/api/docs

## Stopping the Project

To stop the running containers, execute the following command in the project root directory:

```bash
docker compose down
```

This will stop and remove the containers, networks, and volumes associated with the project.

## Additional Information

For more details on how the project is set up with Docker, please refer to the `docker-compose.yml` file.

---

Feel free to reach out if you encounter any issues or have questions about the project!
