FROM nginx:1.19.6-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d

ENV APP_HOME=/home/app/web
WORKDIR $APP_HOME

RUN mkdir -p static media

RUN  chown -R nginx:nginx /var/cache/nginx && \
     chown -R nginx:nginx /var/log/nginx && \
     chown -R nginx:nginx /etc/nginx/conf.d
RUN touch /var/run/nginx.pid && \
        chown -R nginx:nginx /var/run/nginx.pid

USER nginx
