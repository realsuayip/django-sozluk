# nginx:1.29-alpine3.22
FROM nginx@sha256:42a516af16b852e33b7682d5ef8acbd5d13fe08fecadc7ed98605ba5e3b26ab8

COPY docker/prod/nginx /etc/nginx/

RUN  chown -R nginx:nginx /var/cache/nginx && \
     chown -R nginx:nginx /var/log/nginx && \
     chown -R nginx:nginx /etc/nginx/conf.d && \
     chown -R nginx:nginx /etc/nginx/certs
RUN touch /var/run/nginx.pid && \
        chown -R nginx:nginx /var/run/nginx.pid

RUN addgroup -g 1015 fileserv \
    && addgroup nginx fileserv

RUN mkdir -p /app/media && chown -R :fileserv /app/media && chmod -R 770 /app/media
RUN mkdir -p /app/static && chown -R :fileserv /app/static && chmod -R 770 /app/static

USER nginx
