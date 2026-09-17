FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

# VITE_* se resuelven en build time (import.meta.env). Preferir build-args
# de Compose; frontend/.env del contexto actúa de fallback local.
ARG VITE_API_URL=http://localhost:8000
ARG VITE_API_KEY=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_KEY=$VITE_API_KEY

RUN npm run build-only
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
