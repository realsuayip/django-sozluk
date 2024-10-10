FROM nginx:1.25-alpine

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
