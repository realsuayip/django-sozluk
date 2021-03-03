# Kurulum

***Güncelleme**: Artık Docker kullanarak çok daha zahmetsiz bir şekilde projeyi ayağa kaldırabilirsiniz.*

Projeyi yerel ağda çalıştırabilmek için gerekli yönergeler ile ilk kurulumdan hemen sonra yapılması gereken ayarlar
burada anlatılacak. Eğer projeyi bir sunucuya yükleyip canlı ortama geçmek istiyorsanız, `django deployment` anahtar
kelimesiyle internette arama yapmanızı öneriyoruz; zira işletim sistemi ve bazı diğer faktörlerin farklılığı sebebiyle
binlerce kurulum senaryosu ortaya çıkabiliyor. Aynı zamanda Django ile canlı ortama geçmek (özellikle konteynerleştirme
yapılmamış ise) epey zahmetli. Projeyi canlı ortama almak niyetindeyseniz [sunucuya kurulum yapacaklar için notlar](deployment.md)
kısmını da okumalısınız.
#### Python
İşletim sistemimizde Python’un kurulu olması gerekiyor. Linux tabanlı sistemlerin çoğunluğunda Python
halihazırda kurulu olarak geliyor. Windows kullanıyor iseniz `python.org` adresinden uygun sürümü indirip kurmanız
gerekiyor, kurulumu yaparken `Add Python to PATH` seçeneğini işaretlediğinizden emin olun, bu komut satırında
Python’u çalıştırmamızı sağlayacak. Kurmanız gereken sürümü projenin ana dizinindeki beni oku dosyasında bulabilirsiniz.
#### Sanal ortam oluşturma
Proje ana dizininde (`manage.py` dosyası bulunan dizin) komut satırını açıyoruz. Şu aşamada projemizi bir “sanal ortam”
içine almamız gerekiyor, bu sayede sistemdeki Python’a dokunmadan işlerimizi halledebileceğiz. Bunun için Python’un
paket yöneticisiyle (pip) `virtualenv` kütüphanesini yüklüyoruz:

    pip install virtualenv
   
Not: Linux tabanlı sistemlerde Python sürümüne göre “pip” komutu değişebilir (pip3, pip3.8 vs.). Bu adımdan sonra proje ana
dizinine sanal ortamı kurabiliriz. Bunu yapmak için:

    virtualenv venv

Bu komut proje ana dizininde “venv” isimli bir klasör oluşturacak. Bu adımda sanal ortama geçiş yapmamız gerekiyor,
sanal ortama geçiş yapmak için aynı dizinde şu komutu çalıştırıyoruz:

Windows için:

    venv\Scripts\activate
    
Linux tabanlı sistemler için (çoğunda):
    
    source venv/bin/activate

Bu adımdan sonra eğer komut satırının başında `(venv)` ibaresi yer alıyor ise sanal ortama geçiş yapmışız demektir.
Komut satırında projeyle etkileşime girerken her zaman sanal ortamda olduğunuzdan emin olun.
#### Gereksinimlerin yüklenmesi
Sıradaki aşamada proje gereksinimlerini yüklememiz gerekiyor. Bunu yapmak için sanal ortamda ana dizindeyken:

    pip install -r requirements.txt

Bu adımdan sonra projemizi çalıştırmamıza neredeyse ramak kalıyor. Projede kullanılan fakat `requirements.txt` dosyasında
listelenmeyen bir gereksinim daha var: `psycopg2`. Bu kütüphane PostgreSQL veri tabanı ile bağlantı kurmaya yarıyor,
fakat yerel ortamda SQLite veri tabanı ile çalışacağımız için bunu kurmamız gerekmiyor. Bu kütüphaneyi kurmadan devam
etmek için `INSTALLED_APPS`’dan `django.contrib.postgres` app’ini çıkartmanız gerekiyor. Eğer bir önceki cümlede ne
anlatıldığına dair bir fikriniz yok ise kolayca bu kütüphaneyi kurarak devam etmenizde herhangi bir sakınca yok:

    pip install psycopg2

#### Tabloların oluşturulması
Sırada veri tabanında tabloları oluşturmak var. Bunu yapmak için yine ana dizinde peş peşe şu komutları çalıştırıyoruz:

    python manage.py makemigrations
    python manage.py migrate


#### Sitenin çalıştırılması
Artık projeyi çalıştırıp siteye girebiliriz:
       
       python manage.py runserver

Bu komut siteyi `127.0.0.1:8000` adresinde erişilebilir hale getirecek. Bu adrese girdiğinizde siteyi gördüğünüzden emin
olun.

#### Yetkili hesabının oluşturulması
Bu adımdan sonra giriş yapıp yönetim paneline girmemiz gerekiyor, zira sitemize hiçbir şekilde müdahale edemiyoruz.
Bunu yapmak için komut satırında <kbd>Ctrl</kbd>+<kbd>C</kbd> kombinasyonunu kullanarak yerel sunucuyu sonlandırıyoruz.
Sanal ortamda iken şu komutu çalıştırıyoruz:

    python manage.py createsuperuser

Bu aşamada e-posta adresi, aktiflik statüsü (basitçe “1” yazabilirsiniz), parola ve nick vermeniz istenecek.
Bu bilgileri doldurduktan sonra e-posta adresiniz ve belirlediğiniz parola ile siteye giriş yapabilirsiniz
(siteyi açmak için bir önceki `runserver` komutunu tekrar çalıştırın). Site içindeyken yönetim paneline erişmeniz için
herhangi bir yol yok, yönetici paneline girmek için `127.0.0.1:8000/admin/` adresine gidebilirsiniz. Burada yazar detay
sayfanıza gidip kendinizi çaylaklıktan çıkarabilirsiniz.

#### Ayarların yapılması
Kurulumun tamamlanması için birtakım ayarların değiştirilip uygun hale getirilmesi gerekiyor. Dokümantasyonda her ayar
için detaylı bilgi bulunuyor. Bu ayarlardan iki tanesini derhal yapmanız gerekiyor, aksi takdirde site düzgün çalışmayacaktır:

[GENERIC_SUPERUSER_USERNAME](settings.md#generic_superuser_username)\
[GENERIC_PRIVATEUSER_USERNAME](settings.md#generic_privateuser_username)

#### Geçici e-posta sunucusu

**Güncelleme:** E-postalar artık Celery ile asenkron olarak gönderildiği için arka planda bir de celery worker
çalıştırmanız gerekiyor.

Son olarak, e-posta gönderen sayfalar ve fonksiyonlar (örneğin yeni kullanıcı kaydı) halihazırda bir e-posta sunucusu
belirlenmediği için çalışmayacaktır. Fakat yerel ağda iken gönderilen e-postaları komut satırına yazdırabiliriz, bunu
yapmak için ayrı bir komut satırında şunu çalıştırın:
    
    python -m smtpd -n -c DebuggingServer localhost:1025

Bu komut satırı, açık olduğu sürece sözde e-posta sunucusu görevi görecek.
