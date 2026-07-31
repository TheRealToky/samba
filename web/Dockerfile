# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
# The lockfile must be part of the install, and the install must be `ci`, not
# `install`. Resolving dependencies afresh per build means two builds of the
# same commit can pull different transitive versions, emit different bundles,
# and therefore different content hashes in dist/assets. Behind a round-robin
# load balancer that is fatal: the index.html one replica serves names chunks
# the other replica does not have. `npm ci` installs the locked tree exactly.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
