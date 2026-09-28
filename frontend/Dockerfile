FROM node:20-slim AS build
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./

# Vite bakes VITE_* variables into the bundle at build time -- passed through
# from docker-compose's `args:` block, which reads them from .env.
ARG VITE_API_BASE_URL=/api
ARG VITE_RISK_TIER_HIGH=70
ARG VITE_RISK_TIER_MEDIUM=40
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_RISK_TIER_HIGH=${VITE_RISK_TIER_HIGH} \
    VITE_RISK_TIER_MEDIUM=${VITE_RISK_TIER_MEDIUM}

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
