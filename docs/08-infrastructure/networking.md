# Redes y Seguridad (Networking)

La topología de red en el archivo `docker-compose.yml` está diseñada bajo el principio del "Menor Privilegio" (Principle of Least Privilege).

## 1. Aislamiento de Bases de Datos

Los servicios `database` (MongoDB) y `redis` **no exponen puertos al Host (host_os)**.
En el YAML de producción, en lugar de usar `ports: ["27017:27017"]`, se utiliza `expose: ["27017"]`.
Esto significa que MongoDB es accesible única y exclusivamente por los contenedores que pertenezcan a la red `app_network`. Ni siquiera un administrador conectado a la máquina Host por SSH puede hacer una consulta directa a la base de datos sin entrar a un contenedor. Esto previene fugas de datos si el firewall perimetral (UFW/Iptables) falla.

## 2. Redis ACL (Listas de Control de Acceso)

Para mayor seguridad, Redis no arranca con el usuario `default` omnipotente sin contraseña.
El volumen monta un script de inicialización (`deploy/redis/entrypoint.sh`) que:
1.  Deshabilita el usuario por defecto.
2.  Crea un usuario específico (ej. `brevio`) con la contraseña pasada en `$REDIS_PASSWORD`.
3.  Le otorga permisos limitados (ej. deniega el uso de comandos administrativos peligrosos como `FLUSHALL` o `CONFIG`).

## 3. Subred Fija y `TRUSTED_PROXY`

BrevioAI implementa protección estricta contra falsificación de IPs (IP Spoofing) vital para que los baneos por Rate Limit funcionen.
El `docker-compose.yml` fuerza a Docker a usar una subred estática:
```yaml
networks:
  app_network:
    ipam:
      config:
        - subnet: 172.28.0.0/16
```
Esto permite al administrador configurar la variable de entorno `TRUSTED_PROXY` exactamente en la IP/rango del Frontend Nginx que hace de proxy inverso, de forma predecible en cada reinicio. El Backend (FastAPI) solo aceptará la cabecera `X-Forwarded-For` (que indica la IP real del usuario) si proviene directamente de un proxy confiable dentro de esa subred (`172.28.0.0/16`). Si alguien falsifica la cabecera atacando directamente al backend, el sistema ignora la cabecera y toma la IP del atacante.
