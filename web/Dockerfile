FROM node:22-bookworm-slim

WORKDIR /app

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web ./

ENV NODE_ENV=production
ENV PORT=3000
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
