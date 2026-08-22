FROM node:20-alpine AS builder

WORKDIR /app
COPY ragflow-docs/website/package.json ./
RUN npm install

COPY ragflow-docs/website ./
COPY docs /docs

RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
