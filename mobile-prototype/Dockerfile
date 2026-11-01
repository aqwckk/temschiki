FROM node:22-alpine AS build
WORKDIR /web
COPY mobile-prototype/package.json mobile-prototype/package-lock.json ./
RUN npm ci
COPY mobile-prototype/ ./
RUN npm run build

FROM nginx:1.28-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
