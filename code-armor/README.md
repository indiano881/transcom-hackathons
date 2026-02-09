# Code Armor Backend Service
`code-armor` is the backend service module of the `hackathon_transcom` project.
It provides:
- RESTful APIs
- Authentication and authorization
- Database access
- Core business logic

# Project Setup
## MySQL Setup
On my Intel-based macOS, installing MySQL 9.5 directly via Homebrew is not convenient.  
Therefore, I chose to use Docker to run MySQL. The commands I used are:

```bash
docker volume create mysql95-data
docker run -d \
  --name mysql95 \
  -v mysql95-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=xxx \
  -e MYSQL_DATABASE=codearmor \
  -e MYSQL_USER=codearmor \
  -e MYSQL_PASSWORD=xxx \
  -p 3306:3306 \
  mysql:9.5
````

> Note: Passwords in the command are replaced with `xxx` for security reasons.

To access the database, I use the following command:

```bash
docker exec -it mysql95 mysql -ucodearmor -p
```

## Development Environment
The project is developed and run using the following environment:
- JDK 25.0.1
- Spring Boot 4.0.2
- Spring Data JPA 4.0.2
- Spring Security 7.0.2
