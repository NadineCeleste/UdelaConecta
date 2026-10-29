// Producción (VPS detrás de Caddy): la API y el storage se sirven en el mismo dominio
export const environment = {
  production: true,
  apiUrl: '/api/',
  bucketUrl: '/storage'
};
