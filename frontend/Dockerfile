FROM alpine:latest

WORKDIR /app

COPY brevio_service/ /app

RUN apk update && \
    apk upgrade && \
    apk add --no-cache nodejs npm

RUN npm install && \
    npm run build

CMD ["npm", "run","dev"]