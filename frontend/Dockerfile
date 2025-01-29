FROM node:18-alpine

WORKDIR /app

COPY . /app

RUN apk update && \
    apk upgrade 

RUN npm install
RUN npm run build

RUN npm install -g http-server 

EXPOSE 8080

CMD [ "http-server", "dist", "-p", "8080"]
