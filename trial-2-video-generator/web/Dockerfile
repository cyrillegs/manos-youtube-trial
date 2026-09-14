FROM node:22-bookworm-slim

WORKDIR /app

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web ./

ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL
ENV NODE_ENV=production
ENV PORT=3000
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
