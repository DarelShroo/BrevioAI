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
   cd <project-directory>
   ```

3. Build and start the containers with Docker Compose:

   ```bash
   docker-compose up --build
   ```

   This will build the necessary Docker images and start the containers for the project.

4. Once the containers are up and running, you can access the application through your browser or API, depending on the configuration.

## Stopping the Project

To stop the running containers, execute the following command in the project root directory:

```bash
docker-compose down
```

This will stop and remove the containers, networks, and volumes associated with the project.

## Additional Information

For more details on how the project is set up with Docker, please refer to the `docker-compose.yml` file.

---

Feel free to reach out if you encounter any issues or have questions about the project!
