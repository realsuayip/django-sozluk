# Çeviri


### Çeviri dosyalarının derlenmesi

İlk kurulumda Türkçe dilinin düzgün çalışmadığını göreceksiniz. Bunun sebebi
çeviri dosyalarının henüz derlenmemiş olması. Çeviri dosyaları uygulama bazında
bulunuyor, bu her uygulamanın (dictionary, dictionary_graph) çeviri dosyalarının ayrı derlenmesi demek.

Derlemek istediğimiz uygulamanın dizinindeyken şu komutu çalıştırıyoruz:

    django-admin compilemessages

Not: Derleme yaptıktan sonra sunucuyu yeniden başlatmanız gerekiyor.

### Yeni çeviri oluşturulması

Bir başka dil için çeviri dosyalarını oluşturmak için (ya da mevcut dil dosyalarını güncellemek için):

    django-admin makemessages -l <dil_kodu>
    django-admin makemessages -l <dil_kodu> -d djangojs

`<dil_kodu>` `es`, `fr` gibi geçerli bir dil kodu olmalı.

Çeviri oluştururken de derlemede olduğu gibi uygulama bazında ilerlemelisiniz.
Dosyalar derledikten sonra `djdict/settings.py` dosyasına dilin eklenmesi gerekiyor.
Eğer yeni bir çeviri yaptıysanız GitHub'da issue açarak dilin projeye eklenmesini isteyebilirsiniz.
