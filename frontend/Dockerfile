# =============================================================
# Frontend — T1 placeholder (will be replaced in T3)
# =============================================================
# For T1, we just serve a static landing page via nginx.
# In T3, this will be a multi-stage Node + Vite build with
# proper React app, Tailwind, shadcn/ui.
# =============================================================

FROM nginx:1.27-alpine

# Replace default config with one that listens on 5173
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf

# Copy static landing page
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 5173

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:5173/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
