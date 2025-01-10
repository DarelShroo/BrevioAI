FROM alpine:latest

WORKDIR /app

COPY package*.json ./

COPY . /app

RUN apk update && \
    apk upgrade && \
    apk add --no-cache nodejs npm

RUN npm install && \
    npm run build && \
    npm install -g http-server \
    npm run build


EXPOSE 8080

CMD [ "http-server", "dist" ]
#CMD ["tail", "-f", "/dev/null"]
