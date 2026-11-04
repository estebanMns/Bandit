/* Service Worker de Bandit: shell PWA, directorio sin conexión y Web Push. */

const VERSION = "v1";
const STATIC_CACHE = `bandit-static-${VERSION}`;
const DIRECTORY_CACHE = `bandit-directorio-${VERSION}`;
const OFFLINE_URL = "/sin-conexion";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll([OFFLINE_URL, "/manifest.webmanifest", "/icon.svg"]))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name.startsWith("bandit-") && !name.endsWith(VERSION))
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function isDirectory(url) {
  return url.pathname.startsWith("/directorio") || url.pathname.startsWith("/api/directory/media");
}

/** Muestra la copia guardada al instante y la actualiza en segundo plano. */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DIRECTORY_CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached ?? caches.match(OFFLINE_URL));
  return cached ?? network;
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) (await caches.open(STATIC_CACHE)).put(request, response.clone());
  return response;
}

async function networkWithOfflinePage(request) {
  try {
    return await fetch(request);
  } catch {
    return caches.match(OFFLINE_URL);
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  if (isDirectory(url)) {
    event.respondWith(staleWhileRevalidate(request));
  } else if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(request));
  } else if (request.mode === "navigate") {
    // Monitor e incidentes nunca se sirven de caché: siempre datos actuales.
    event.respondWith(networkWithOfflinePage(request));
  }
});

self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  event.waitUntil(
    self.registration.showNotification(data.title ?? "Bandit", {
      body: data.body,
      icon: "/icon.svg",
      tag: data.url,
      requireInteraction: true,
      data: { url: data.url ?? "/monitor" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(event.notification.data.url));
});
