FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Ningún paquete necesita scripts de instalación (solo fsevents, que es de macOS).
RUN npm ci --ignore-scripts
COPY . .
ARG NEXT_PUBLIC_VAPID_PUBLIC_KEY=""
ENV NEXT_PUBLIC_VAPID_PUBLIC_KEY=$NEXT_PUBLIC_VAPID_PUBLIC_KEY
RUN npm run build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production
# El usuario node debe poder escribir .next: ahí guarda las páginas ISR regeneradas.
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
