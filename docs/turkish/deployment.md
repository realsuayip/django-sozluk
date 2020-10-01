# Sunucuya kurulum yapacaklar için notlar

Aksini yapmak için spesifik bir sebebiniz yok ise sunucuya kurulum yaparken şu adımları takip etmenizi öneriyoruz:

* Web server için `Nginx` kullanın.
* Medya dizinini `internal` olarak işaretleyin, medya dosyalarının direkt olarak görüntülenmemesi gerekiyor. Bu dosyalar
`XSendfile` yoluyla servis ediliyor. 
* Veritabanı için `PostgreSQL` kullanın.
* Sunucunuza bir önbellekleme sistemi kurmanız veya önbellekleme için ayrı bir sunucu açmanız gerekiyor. Önbellekleme
sistemi için `memcached` test edildi, fakat Django'da önbellek sistemi ortak bir arayüz kullandığı için herhangi bir
sistemi kullanabilirsiniz.
* E-postaların gönderilmesi ve periyodik işlemlerin gerçekleştirebilmesi için Celery kullanılıyor. Celery için broker
seçerken `RabbitMQ` kullanın. Celery'i nasıl ayarlayıp daemonize edebileceğiniz bilgisini  Celery dökümantasyonunda bulabilirsiniz.
* Bu adreste belirtilen yönergelerin hepsini titiz bir şekilde kontrol ettiğinizden emin olun:
https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/