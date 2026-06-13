# =============================================================
# ClientFinder Frontend — Multi-stage build
# =============================================================
# Stage 1: Build with Node + Vite
# Stage 2: Serve static files with nginx
# =============================================================

# ----- Stage 1: Build -----
FROM node:20-alpine AS builder
WORKDIR /app

# Install deps with cache layer
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# Build args for Vite env
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

# Copy source and build
COPY . .
RUN npm run build

# ----- Stage 2: Serve -----
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:5173/health >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
